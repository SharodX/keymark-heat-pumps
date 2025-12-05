#!/usr/bin/env python3
"""
Minimal DuckDB builder - no fancy output, just fast execution.
Run with: python scripts/pipeline/build_duckdb_minimal.py
"""
import json
import re
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
import duckdb

# Ignore SIGINT and SIGTERM during database operations
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)

SCHEMA_FILE = Path("backend/db/schema.sql")
DB_FILE = Path("data/keymark.duckdb")
DATA_DIR = Path("data/database")
BATCH_SIZE = 50000  # Big batches for speed

_num_re = re.compile(r"[-+]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
_time_re = re.compile(r"^(\d{1,2}):(\d{2})$")  # h:mm or hh:mm format

# EN16147_001 Load Profile mapping (normalized to uppercase)
LOAD_PROFILE_MAP = {
    "S": 1, "M": 2, "L": 3, "LARGE": 3,
    "XL": 4, "XXL": 5, "3XL": 6, "4XL": 7
}

# Special value for non-numeric entries that should be flagged
INVALID_ENTRY_VALUE = -999.0


def parse_time_to_hours(v):
    """Parse h:mm or hh:mm format to decimal hours."""
    if not isinstance(v, str):
        return None
    m = _time_re.match(v.strip())
    if m:
        hours = int(m.group(1))
        minutes = int(m.group(2))
        return hours + minutes / 60.0
    return None


def parse_load_profile(v):
    """Parse DHW load profile string to numeric code."""
    if not isinstance(v, str):
        return None
    normalized = v.strip().upper()
    return LOAD_PROFILE_MAP.get(normalized)


def parse_value(v, en_code):
    """
    Parse measurement value with special handling for specific EN codes.
    Returns (numeric_value, original_text) tuple.
    """
    original = str(v) if v is not None else None
    
    # Handle None or empty
    if v is None or (isinstance(v, str) and v.strip() in ("", "-", "N/A")):
        return None, original
    
    # Already numeric
    if isinstance(v, (int, float)):
        return float(v), original
    
    if not isinstance(v, str):
        return None, original
    
    v_clean = v.strip()
    
    # EN16147_001: Load Profile (S, M, L, XL, XXL, 3XL, 4XL)
    if en_code == "EN16147_001":
        profile_val = parse_load_profile(v_clean)
        if profile_val is not None:
            return float(profile_val), original
        # Check if it's already numeric
        m = _num_re.search(v_clean.replace(",", "."))
        if m:
            return float(m.group(0)), original
        return None, original
    
    # EN16147_004: Heating up time in h:mm format
    if en_code == "EN16147_004":
        time_val = parse_time_to_hours(v_clean)
        if time_val is not None:
            return time_val, original
        # Fall through to numeric parsing
    
    # EN14825_027: Supplementary heater type - flag invalid text entries
    if en_code == "EN14825_027":
        # Check for known junk values
        if any(x in v_clean.lower() for x in ["400v", "electricity", "elctricity", "n/a"]):
            return INVALID_ENTRY_VALUE, original
    
    # EN12102_1_001, EN12102_1_002, EN14825_020: Skip "-" values
    if en_code in ("EN12102_1_001", "EN12102_1_002", "EN14825_020"):
        if v_clean == "-":
            return None, original
    
    # Default: try to parse as number
    m = _num_re.search(v_clean.replace(",", "."))
    return (float(m.group(0)), original) if m else (None, original)


def parse_num(v):
    """Legacy function for backwards compatibility."""
    if isinstance(v, (int, float)): return float(v)
    if not isinstance(v, str): return None
    m = _num_re.search(v.replace(",", "."))
    return float(m.group(0)) if m else None

def fmt_time(secs):
    """Format seconds as mm:ss or hh:mm:ss"""
    if secs < 60: return f"{secs:.0f}s"
    if secs < 3600: return f"{int(secs//60)}m {int(secs%60)}s"
    return f"{int(secs//3600)}h {int((secs%3600)//60)}m"

def progress(current, total, start_time, prefix=""):
    """Print progress with ETA"""
    elapsed = time.time() - start_time
    pct = current / total * 100 if total > 0 else 100
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0
    bar_len = 25
    filled = int(bar_len * current / total) if total > 0 else bar_len
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r  {prefix}|{bar}| {pct:5.1f}% ({current:,}/{total:,}) ETA: {fmt_time(eta)}    ")
    sys.stdout.flush()

def main():
    build_start = time.time()
    print(f"[{datetime.now():%H:%M:%S}] Starting build...")
    print()
    
    files = sorted(DATA_DIR.glob("*.json"))
    total_files = len(files)
    print(f"  Phase 1: Reading {total_files:,} JSON files...")
    print()
    print(f"[{datetime.now():%H:%M:%S}] Found {len(files)} JSON files")
    
    # Collect all data
    mfrs_set, subtypes_set, models_set = set(), set(), set()
    mfrs, subtypes, models, measurements = [], [], [], []
    
    read_start = time.time()
    for i, p in enumerate(files, 1):
        if i % 100 == 0 or i == total_files:
            progress(i, total_files, read_start, "Reading: ")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except: continue
        
        meta = data.get("file_metadata", {})
        mfr = (meta.get("Manufacturer") or "Unknown").strip() or "Unknown"
        subtype = (meta.get("Modelname") or "Unknown").strip() or "Unknown"
        
        if mfr not in mfrs_set:
            mfrs_set.add(mfr)
            mfrs.append((mfr,))
        
        if (mfr, subtype) not in subtypes_set:
            subtypes_set.add((mfr, subtype))
            subtypes.append((mfr, subtype, json.dumps({k: v for k, v in meta.items() if v})))
        
        for hi, hp in enumerate(data.get("heat_pumps", []), 1):
            model_name = (hp.get("variant") or hp.get("title") or "").strip() or f"model_{hi:03d}"
            base, sfx = model_name, 2
            while (mfr, subtype, model_name) in models_set:
                model_name = f"{base}_{sfx}"; sfx += 1
            models_set.add((mfr, subtype, model_name))
            
            props = {k: v for k, v in hp.get("properties", {}).items() if v is not None}
            models.append((mfr, subtype, model_name, json.dumps(props) if props else None))
            
            for code, dims in hp.get("measurements", {}).items():
                if not isinstance(dims, dict): continue
                for dim, val in dims.items():
                    num, original = parse_value(val, code)
                    if num is not None:
                        measurements.append((mfr, subtype, model_name, code, dim, num, None, original))
    
    print()  # End progress line
    print()
    print(f"  Data collected in {fmt_time(time.time() - read_start)}:")
    print(f"    Manufacturers: {len(mfrs):,}")
    print(f"    Subtypes:      {len(subtypes):,}")
    print(f"    Models:        {len(models):,}")
    print(f"    Measurements:  {len(measurements):,}")
    print()
    
    # Write to database
    print(f"  Phase 2: Writing to DuckDB...")
    print()
    
    print(f"    Opening database...")
    conn = duckdb.connect(str(DB_FILE))
    
    print(f"    Loading schema...")
    conn.execute(SCHEMA_FILE.read_text())
    
    print(f"    Clearing tables...")
    for t in ["measurements", "models", "subtypes", "manufacturers"]:
        conn.execute(f"DELETE FROM {t}")
    
    # Insert each table with its own transaction for resilience
    print(f"    Inserting manufacturers ({len(mfrs):,})...")
    mfr_start = time.time()
    conn.execute("BEGIN")
    conn.executemany("INSERT OR IGNORE INTO manufacturers (name) VALUES (?)", mfrs)
    conn.execute("COMMIT")
    print(f"    ✓ Manufacturers done in {fmt_time(time.time() - mfr_start)}")
    
    print(f"    Inserting subtypes ({len(subtypes):,})...")
    subtype_start = time.time()
    conn.execute("BEGIN")
    conn.executemany("INSERT OR IGNORE INTO subtypes (manufacturer_name, subtype_name, metadata) VALUES (?, ?, ?)", subtypes)
    conn.execute("COMMIT")
    print(f"    ✓ Subtypes done in {fmt_time(time.time() - subtype_start)}")
    
    print(f"    Inserting models ({len(models):,})...")
    model_start = time.time()
    conn.execute("BEGIN")
    # Do models in smaller batches with commits
    for i in range(0, len(models), 2000):
        batch = models[i:i+2000]
        conn.executemany("INSERT OR IGNORE INTO models (manufacturer_name, subtype_name, model_name, properties) VALUES (?, ?, ?, ?)", batch)
        progress(min(i+2000, len(models)), len(models), model_start, "Models: ")
    conn.execute("COMMIT")
    print()  # End progress line
    print(f"    ✓ Models done in {fmt_time(time.time() - model_start)}")
    
    print(f"    Inserting measurements ({len(measurements):,})...")
    meas_start = time.time()
    conn.execute("BEGIN")
    for i in range(0, len(measurements), BATCH_SIZE):
        conn.executemany(
            "INSERT INTO measurements (manufacturer_name, subtype_name, model_name, en_code, dimension, value, unit, value_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            measurements[i:i+BATCH_SIZE]
        )
        progress(min(i+BATCH_SIZE, len(measurements)), len(measurements), meas_start, "Measurements: ")
    conn.execute("COMMIT")
    print()  # End progress line
    print(f"    ✓ Measurements done in {fmt_time(time.time() - meas_start)}")
    
    conn.close()
    
    total_time = time.time() - build_start
    print()
    print(f"  ═══════════════════════════════════════════════")
    print(f"  BUILD COMPLETE in {fmt_time(total_time)}")
    print(f"  ═══════════════════════════════════════════════")

if __name__ == "__main__":
    main()
