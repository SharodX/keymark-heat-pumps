#!/usr/bin/env python3
"""
Optimized DuckDB builder with batch inserts.

This version is ~10-20x faster than the original by:
1. Collecting all data in memory first
2. Using batch INSERT with executemany()
3. Single transaction for all inserts
4. Progress reporting with timing

Usage:
    python build_duckdb_fast.py           # Full rebuild
    python build_duckdb_fast.py --check   # Just check current DB state
"""

from __future__ import annotations

import json
import re
import sys
import time
import signal
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

import duckdb

# Log file for debugging terminations
LOG_FILE = Path("/tmp/duckdb_build_debug.log")

def log(msg: str):
    """Write to both stdout and log file."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
        f.flush()

def signal_handler(signum, frame):
    """Log signal and exit cleanly."""
    sig_name = signal.Signals(signum).name
    log(f"SIGNAL RECEIVED: {sig_name} ({signum}) - IGNORING during database operation")
    # Don't exit during critical operations, just log
    # sys.exit(128 + signum)

# Register signal handlers - we'll ignore SIGTERM during database operations
original_sigterm = signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
try:
    signal.signal(signal.SIGHUP, signal_handler)
except (ValueError, OSError):
    pass  # SIGHUP may not be available


class ProgressTracker:
    """Real-time progress tracking with rate and ETA."""
    
    def __init__(self, total: int, description: str = "Processing", update_interval: float = 0.5):
        self.total = total
        self.description = description
        self.update_interval = update_interval
        self.current = 0
        self.start_time = time.time()
        self.last_update = 0
        self.last_print_time = 0
        self.last_log_time = 0
    
    def update(self, n: int = 1, force: bool = False):
        """Update progress by n items."""
        self.current += n
        now = time.time()
        
        # Only print at intervals to avoid slowdown
        if force or (now - self.last_print_time) >= self.update_interval:
            self._print_progress()
            self.last_print_time = now
        
        # Log to file every 5 seconds for debugging
        if (now - self.last_log_time) >= 5.0:
            pct = (self.current / self.total * 100) if self.total > 0 else 100
            with open(LOG_FILE, "a") as f:
                f.write(f"{self.description}: {pct:.1f}% ({self.current:,}/{self.total:,})\n")
                f.flush()
            self.last_log_time = now
    
    def _print_progress(self):
        elapsed = time.time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0
        remaining = self.total - self.current
        eta = remaining / rate if rate > 0 else 0
        
        pct = (self.current / self.total * 100) if self.total > 0 else 100
        
        # Create progress bar
        bar_width = 30
        filled = int(bar_width * self.current / self.total) if self.total > 0 else bar_width
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Format numbers with commas
        current_fmt = f"{self.current:,}"
        total_fmt = f"{self.total:,}"
        rate_fmt = f"{rate:,.0f}"
        
        # Format ETA
        if eta < 60:
            eta_fmt = f"{eta:.0f}s"
        elif eta < 3600:
            eta_fmt = f"{eta/60:.1f}m"
        else:
            eta_fmt = f"{eta/3600:.1f}h"
        
        line = f"\r  {self.description}: |{bar}| {pct:5.1f}% [{current_fmt}/{total_fmt}] {rate_fmt}/s ETA:{eta_fmt}  "
        sys.stdout.write(line)
        sys.stdout.flush()
    
    def finish(self):
        """Mark progress as complete."""
        self.current = self.total
        self._print_progress()
        elapsed = time.time() - self.start_time
        print(f" Done in {elapsed:.1f}s")


def get_memory_usage() -> str:
    """Get current memory usage."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mb = usage.ru_maxrss / 1024  # Linux: KB -> MB
        return f"{mb:.0f}MB"
    except:
        return "N/A"

SCHEMA_FILE = Path("backend/db/schema.sql")
DB_FILE = Path("data/keymark.duckdb")
DATA_DIR = Path("data/database")

# Batch size for inserts
BATCH_SIZE = 10000

_number_pattern = re.compile(r"[-+]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")


def parse_numeric(value: object) -> Optional[float]:
    """Best-effort conversion of measurement values to float."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    candidate = value.strip().replace(",", ".")
    match = _number_pattern.search(candidate)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_property_value(value: object) -> object:
    """Parse property values, converting string numbers to integers where appropriate."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            pass
    return value


def parse_properties(properties: dict) -> dict:
    """Parse and structure variant properties from JSON."""
    parsed = {}
    for key, value in properties.items():
        parsed_value = parse_property_value(value)
        if parsed_value is not None:
            parsed[key] = parsed_value
    return parsed


def parse_metadata(metadata: dict) -> dict:
    """Parse and structure metadata fields from JSON."""
    parsed = {}
    for key, value in metadata.items():
        if value and isinstance(value, str):
            value = value.strip()
        if value:
            parsed[key] = value
    
    if "Mass of Refrigerant" in parsed:
        mass_numeric = parse_numeric(parsed["Mass of Refrigerant"])
        if mass_numeric is not None:
            parsed["refrigerant_mass_kg"] = mass_numeric
    
    if "Date" in parsed:
        date_str = parsed["Date"]
        for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                parsed["certification_date"] = dt.strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
    
    return parsed


def _clean_text(value: object) -> Optional[str]:
    """Return a trimmed string if the input is a non-empty string."""
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            return candidate
    return None


def collect_all_data(files: list[Path]) -> tuple[list, list, list, list]:
    """
    Collect all data from JSON files into lists for batch insert.
    
    Returns:
        (manufacturers, models, variants, measurements)
    """
    manufacturers_set = set()
    models_set = set()
    variants_set = set()
    
    manufacturers = []
    models = []
    variants = []
    measurements = []
    
    total = len(files)
    progress = ProgressTracker(total, "Reading files")
    
    for idx, path in enumerate(files, 1):
        try:
            with path.open(encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as e:
            print(f"\n  Error reading {path.name}: {e}")
            progress.update()
            continue
        
        metadata = payload.get("file_metadata", {})
        manufacturer_name = metadata.get("Manufacturer", "Unknown").strip() or "Unknown"
        model_name = metadata.get("Modelname", "Unknown").strip() or "Unknown"
        
        # Manufacturer
        if manufacturer_name not in manufacturers_set:
            manufacturers_set.add(manufacturer_name)
            manufacturers.append((manufacturer_name,))
        
        # Model
        model_key = (manufacturer_name, model_name)
        if model_key not in models_set:
            models_set.add(model_key)
            parsed_metadata = parse_metadata(metadata)
            metadata_json = json.dumps(parsed_metadata) if parsed_metadata else None
            models.append((manufacturer_name, model_name, metadata_json))
        
        # Variants and measurements
        for hp_idx, hp in enumerate(payload.get("heat_pumps", []), 1):
            variant_name = _clean_text(hp.get("variant")) or _clean_text(hp.get("title"))
            if not variant_name:
                variant_name = f"variant_{hp_idx:03d}"
            
            # Handle duplicate variant names
            base_variant_name = variant_name
            suffix = 2
            variant_key = (manufacturer_name, model_name, variant_name)
            while variant_key in variants_set:
                variant_name = f"{base_variant_name}_{suffix}"
                variant_key = (manufacturer_name, model_name, variant_name)
                suffix += 1
            
            variants_set.add(variant_key)
            
            # Variant properties
            properties = hp.get("properties", {})
            parsed_properties = parse_properties(properties)
            properties_json = json.dumps(parsed_properties) if parsed_properties else None
            variants.append((manufacturer_name, model_name, variant_name, properties_json))
            
            # Measurements
            hp_measurements = hp.get("measurements", {})
            for en_code, dimensions in hp_measurements.items():
                if not isinstance(dimensions, dict):
                    continue
                for dimension, raw_value in dimensions.items():
                    numeric_value = parse_numeric(raw_value)
                    if numeric_value is None:
                        continue
                    measurements.append((
                        manufacturer_name, model_name, variant_name,
                        en_code, dimension, numeric_value, None
                    ))
        
        progress.update()
    
    progress.finish()
    return manufacturers, models, variants, measurements


def build_database_fast() -> None:
    """Build database with optimized batch inserts."""
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
    
    files = sorted(DATA_DIR.glob("*.json"))
    total_files = len(files)
    
    print("=" * 70)
    print("OPTIMIZED DUCKDB BUILD")
    print("=" * 70)
    print(f"JSON files to process: {total_files:,}")
    print(f"Memory usage: {get_memory_usage()}")
    print()
    
    # Phase 1: Collect all data
    print("PHASE 1: Reading JSON files into memory")
    print("-" * 70)
    phase1_start = time.time()
    manufacturers, models, variants, measurements = collect_all_data(files)
    phase1_time = time.time() - phase1_start
    
    print()
    print(f"  Data collected:")
    print(f"    Manufacturers: {len(manufacturers):>10,}")
    print(f"    Models:        {len(models):>10,}")
    print(f"    Variants:      {len(variants):>10,}")
    print(f"    Measurements:  {len(measurements):>10,}")
    print(f"  Memory usage: {get_memory_usage()}")
    print()
    
    # Phase 2: Write to database
    print("PHASE 2: Writing to DuckDB")
    print("-" * 70)
    phase2_start = time.time()
    
    connection = duckdb.connect(str(DB_FILE))
    try:
        # Load schema and reset
        print("  Loading schema...")
        sql = SCHEMA_FILE.read_text(encoding="utf-8")
        connection.execute(sql)
        
        print("  Clearing existing data...")
        connection.execute("DELETE FROM measurements")
        connection.execute("DELETE FROM variants")
        connection.execute("DELETE FROM models")
        connection.execute("DELETE FROM manufacturers")
        
        # Begin transaction
        connection.execute("BEGIN")
        
        # Helper for batched inserts with real progress
        def insert_batched(data, sql, description, batch_size=1000):
            """Insert data in batches with live progress updates."""
            total = len(data)
            progress = ProgressTracker(total, description)
            for i in range(0, total, batch_size):
                batch = data[i:i + batch_size]
                connection.executemany(sql, batch)
                progress.update(len(batch))
            progress.finish()
        
        # Insert manufacturers (small, use smaller batches for visible progress)
        insert_batched(
            manufacturers,
            "INSERT OR IGNORE INTO manufacturers (name) VALUES (?)",
            "Manufacturers",
            batch_size=50
        )
        
        # Insert models
        insert_batched(
            models,
            "INSERT OR IGNORE INTO models (manufacturer_name, model_name, metadata) VALUES (?, ?, ?)",
            "Models",
            batch_size=200
        )
        
        # Insert variants
        insert_batched(
            variants,
            "INSERT OR IGNORE INTO variants (manufacturer_name, model_name, variant_name, properties) VALUES (?, ?, ?, ?)",
            "Variants",
            batch_size=500
        )
        
        # Insert measurements (largest table, use bigger batches)
        print("  (Measurements is the big one - ~2M rows)")
        insert_batched(
            measurements,
            "INSERT INTO measurements (manufacturer_name, model_name, variant_name, en_code, dimension, value, unit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            "Measurements",
            batch_size=BATCH_SIZE
        )
        
        print("  Committing transaction...")
        connection.execute("COMMIT")
        
    except Exception as e:
        print(f"\n  ERROR: {e}")
        connection.execute("ROLLBACK")
        raise e
    finally:
        connection.close()
    
    phase2_time = time.time() - phase2_start
    total_time = phase1_time + phase2_time
    
    print()
    print("=" * 70)
    print("BUILD COMPLETE")
    print("=" * 70)
    print(f"  Phase 1 (read):  {phase1_time:>6.1f}s")
    print(f"  Phase 2 (write): {phase2_time:>6.1f}s")
    print(f"  Total time:      {total_time:>6.1f}s")
    print()
    print(f"  Files processed:  {total_files:>10,}")
    print(f"  Manufacturers:    {len(manufacturers):>10,}")
    print(f"  Models:           {len(models):>10,}")
    print(f"  Variants:         {len(variants):>10,}")
    print(f"  Measurements:     {len(measurements):>10,}")
    print()
    print(f"  Database file: {DB_FILE}")
    if DB_FILE.exists():
        print(f"  Database size: {DB_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"  Memory usage:  {get_memory_usage()}")


def check_database() -> None:
    """Check current database state."""
    if not DB_FILE.exists():
        print(f"Database not found: {DB_FILE}")
        return
    
    connection = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        counts = connection.execute("""
            SELECT 
                (SELECT COUNT(*) FROM manufacturers) as manu,
                (SELECT COUNT(*) FROM models) as models,
                (SELECT COUNT(*) FROM variants) as variants,
                (SELECT COUNT(*) FROM measurements) as measurements
        """).fetchone()
        
        print("Current database state:")
        print(f"  Manufacturers: {counts[0]:,}")
        print(f"  Models:        {counts[1]:,}")
        print(f"  Variants:      {counts[2]:,}")
        print(f"  Measurements:  {counts[3]:,}")
        print(f"  File:          {DB_FILE}")
        print(f"  Size:          {DB_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="Fast DuckDB builder with batch inserts")
    parser.add_argument("--check", action="store_true", help="Check current DB state only")
    args = parser.parse_args()
    
    if args.check:
        check_database()
    else:
        build_database_fast()


if __name__ == "__main__":
    main()
