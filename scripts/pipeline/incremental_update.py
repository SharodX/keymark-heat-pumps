#!/usr/bin/env python3
"""
Incremental Pipeline Update
===========================
Processes only new CSV files from the sync, validates them, and updates the database.

Steps:
1. Read sync_log.jsonl to find new files
2. Validate each new CSV (check format, required fields)
3. Ingest new CSVs to staging (JSONL)
4. Transform staging to database JSON
5. Incrementally add to DuckDB

Usage:
    python incremental_update.py                # Process new files from sync log
    python incremental_update.py --validate    # Validate only (no processing)
    python incremental_update.py --full        # Full rebuild (all files)
"""

import json
import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.csv_loader import load_csv_records, write_staging_jsonl

# Paths
DATA_SOURCE = PROJECT_ROOT / "data" / "source"
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
DATABASE_DIR = PROJECT_ROOT / "data" / "database"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
SYNC_LOG = LOGS_DIR / "sync_log.jsonl"

# Validation thresholds
MIN_EXPECTED_ROWS = 1
MIN_EXPECTED_COLUMNS = 3


class ValidationResult:
    """Result of validating a single CSV file."""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.valid = True
        self.warnings = []
        self.errors = []
        self.row_count = 0
        self.column_count = 0
        self.has_manufacturer = False
        self.has_title = False
        self.has_measurements = False
        self.measurement_codes = set()
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False
    
    def summary(self) -> str:
        status = "✓ VALID" if self.valid else "✗ INVALID"
        lines = [f"{status}: {self.filepath.name}"]
        lines.append(f"  Rows: {self.row_count}, Cols: {self.column_count}")
        lines.append(f"  Manufacturer: {'✓' if self.has_manufacturer else '✗'}, Title: {'✓' if self.has_title else '✗'}")
        if self.measurement_codes:
            lines.append(f"  EN codes: {', '.join(sorted(self.measurement_codes)[:5])}{'...' if len(self.measurement_codes) > 5 else ''}")
        for w in self.warnings:
            lines.append(f"  ⚠ {w}")
        for e in self.errors:
            lines.append(f"  ✗ {e}")
        return "\n".join(lines)


def validate_csv(csv_path: Path) -> ValidationResult:
    """
    Validate a CSV file for expected structure.
    
    Checks:
    - File is readable
    - Has minimum rows/columns
    - Contains manufacturer and title metadata
    - Contains at least some EN measurement codes
    """
    result = ValidationResult(csv_path)
    
    try:
        csv.field_size_limit(10_000_000)
        
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        result.row_count = len(rows)
        
        if not rows:
            result.add_error("Empty file")
            return result
        
        # Check column count (from first row with data)
        for row in rows:
            if row:
                result.column_count = len(row)
                break
        
        if result.row_count < MIN_EXPECTED_ROWS:
            result.add_error(f"Too few rows: {result.row_count}")
        
        if result.column_count < MIN_EXPECTED_COLUMNS:
            result.add_warning(f"Few columns: {result.column_count}")
        
        # Check for key metadata fields
        for row in rows:
            if len(row) >= 3:
                field_name = row[1] if len(row) > 1 else ""
                
                if field_name == "Manufacturer":
                    result.has_manufacturer = True
                    if not row[2].strip():
                        result.add_warning("Manufacturer field is empty")
                
                elif field_name == "title":
                    result.has_title = True
                    if not row[2].strip():
                        result.add_warning("Title field is empty")
                
                # Check for EN measurement codes
                elif field_name.startswith(('EN14825', 'EN14511', 'EN16147', 'EN12102')):
                    result.has_measurements = True
                    # Extract the base EN code (e.g., "EN14825_2_001" from "EN14825_2_001_5_1_1_0")
                    parts = field_name.split('_')
                    if len(parts) >= 3:
                        base_code = '_'.join(parts[:3])
                        result.measurement_codes.add(base_code)
        
        if not result.has_manufacturer:
            result.add_warning("No Manufacturer field found in metadata")
        
        if not result.has_title:
            result.add_warning("No title field found")
        
        if not result.has_measurements:
            result.add_warning("No EN measurement codes found")
        
    except Exception as e:
        result.add_error(f"Failed to read file: {e}")
    
    return result


def get_new_files_from_sync_log() -> list[tuple[str, dict]]:
    """
    Read sync log and return list of (csv_filename, metadata) for new files.
    """
    new_files = []
    
    if not SYNC_LOG.exists():
        print(f"No sync log found at {SYNC_LOG}")
        return new_files
    
    with open(SYNC_LOG, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    if entry.get("action") == "new" and entry.get("csv_file"):
                        new_files.append((entry["csv_file"], entry))
                except json.JSONDecodeError:
                    continue
    
    print(f"Found {len(new_files)} new files in sync log")
    return new_files


def get_already_processed() -> set[str]:
    """
    Get set of CSV files that have already been processed to staging.
    """
    processed = set()
    
    if STAGING_DIR.exists():
        for jsonl_file in STAGING_DIR.glob("*.jsonl"):
            # Staging files are named like the CSV: _ManufacturerModel.jsonl
            csv_name = jsonl_file.stem + ".csv"
            processed.add(csv_name)
    
    return processed


def ingest_csv_to_staging(csv_path: Path) -> Optional[Path]:
    """
    Ingest a single CSV to staging JSONL format.
    Returns the path to the staging file, or None on failure.
    """
    try:
        records, _ = load_csv_records(csv_path, model_id=csv_path.stem)
        
        if not records:
            print(f"  ⚠ No records extracted from {csv_path.name}")
            return None
        
        staging_path = STAGING_DIR / (csv_path.stem + ".jsonl")
        write_staging_jsonl(records, staging_path)
        
        return staging_path
        
    except Exception as e:
        print(f"  ✗ Failed to ingest {csv_path.name}: {e}")
        return None


def run_validation(csv_files: list[Path], verbose: bool = True) -> tuple[list[Path], list[Path]]:
    """
    Validate a list of CSV files.
    Returns (valid_files, invalid_files).
    """
    valid = []
    invalid = []
    
    print(f"\n{'='*60}")
    print("VALIDATION PHASE")
    print(f"{'='*60}")
    print(f"Validating {len(csv_files)} CSV files...\n")
    
    warnings_count = 0
    errors_count = 0
    
    for csv_path in csv_files:
        result = validate_csv(csv_path)
        
        if result.valid:
            valid.append(csv_path)
        else:
            invalid.append(csv_path)
        
        warnings_count += len(result.warnings)
        errors_count += len(result.errors)
        
        if verbose and (result.errors or result.warnings):
            print(result.summary())
            print()
    
    print(f"\nValidation Summary:")
    print(f"  Valid files:   {len(valid)}")
    print(f"  Invalid files: {len(invalid)}")
    print(f"  Total warnings: {warnings_count}")
    print(f"  Total errors:   {errors_count}")
    
    return valid, invalid


def run_ingestion(csv_files: list[Path]) -> list[Path]:
    """
    Ingest validated CSV files to staging.
    Returns list of successfully created staging files.
    """
    print(f"\n{'='*60}")
    print("INGESTION PHASE")
    print(f"{'='*60}")
    print(f"Ingesting {len(csv_files)} CSV files to staging...\n")
    
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    
    staging_files = []
    failed = 0
    
    for i, csv_path in enumerate(csv_files, 1):
        if i % 100 == 0 or i == len(csv_files):
            print(f"  Progress: {i}/{len(csv_files)}")
        
        staging_path = ingest_csv_to_staging(csv_path)
        if staging_path:
            staging_files.append(staging_path)
        else:
            failed += 1
    
    print(f"\nIngestion Summary:")
    print(f"  Successfully ingested: {len(staging_files)}")
    print(f"  Failed: {failed}")
    
    return staging_files


def run_transform(staging_files: list[Path]) -> list[Path]:
    """
    Transform staging JSONL files to database JSON format.
    Returns list of successfully created database files.
    """
    print(f"\n{'='*60}")
    print("TRANSFORM PHASE")
    print(f"{'='*60}")
    print(f"Transforming {len(staging_files)} staging files to database format...\n")
    
    # Import the transform module
    sys.path.insert(0, str(SCRIPT_DIR))
    from transform_to_database import TransformationLogger, transform_file
    
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create a logger
    logger = TransformationLogger(LOGS_DIR / "transform_logs")
    
    database_files = []
    failed = 0
    skipped = 0
    
    for i, staging_path in enumerate(staging_files, 1):
        if i % 100 == 0 or i == len(staging_files):
            print(f"  Progress: {i}/{len(staging_files)}")
        
        try:
            db_path = DATABASE_DIR / (staging_path.stem + ".json")
            
            # Only transform if not already done
            if db_path.exists():
                database_files.append(db_path)
                skipped += 1
                continue
            
            # Transform the file
            result = transform_file(staging_path, logger)
            
            if result:
                # Write the result to database JSON
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                database_files.append(db_path)
            else:
                failed += 1
                
        except Exception as e:
            print(f"  ✗ Failed to transform {staging_path.name}: {e}")
            failed += 1
    
    print(f"\nTransform Summary:")
    print(f"  Successfully transformed: {len(database_files) - skipped}")
    print(f"  Already existed (skipped): {skipped}")
    print(f"  Failed: {failed}")
    
    return database_files


def update_duckdb_incremental(database_files: list[Path]) -> None:
    """
    Incrementally add new database files to DuckDB.
    """
    import duckdb
    from build_duckdb import (
        load_schema, ingest_json_file, DB_FILE, SCHEMA_FILE
    )
    
    print(f"\n{'='*60}")
    print("DATABASE UPDATE PHASE")
    print(f"{'='*60}")
    print(f"Adding {len(database_files)} files to DuckDB...\n")
    
    if not database_files:
        print("No files to add.")
        return
    
    # Connect to existing DB or create new
    connection = duckdb.connect(str(DB_FILE))
    
    try:
        # Ensure schema exists
        load_schema(connection)
        
        # Get existing data to avoid duplicates
        existing_models = set()
        try:
            rows = connection.execute(
                "SELECT manufacturer_name, model_name FROM models"
            ).fetchall()
            existing_models = {(r[0], r[1]) for r in rows}
            print(f"Existing models in DB: {len(existing_models)}")
        except:
            pass  # Table might be empty
        
        # Track what we've seen in this session
        manufacturer_seen = set()
        model_seen = set(existing_models)
        variant_seen = set()
        
        # Load existing variants
        try:
            rows = connection.execute(
                "SELECT manufacturer_name, model_name, variant_name FROM variants"
            ).fetchall()
            variant_seen = {(r[0], r[1], r[2]) for r in rows}
        except:
            pass
        
        # Load existing manufacturers
        try:
            rows = connection.execute("SELECT name FROM manufacturers").fetchall()
            manufacturer_seen = {r[0] for r in rows}
        except:
            pass
        
        new_variants = 0
        new_measurements = 0
        skipped = 0
        
        for i, db_path in enumerate(database_files, 1):
            if i % 100 == 0 or i == len(database_files):
                print(f"  Progress: {i}/{len(database_files)}")
            
            try:
                # Check if model already exists
                with open(db_path) as f:
                    payload = json.load(f)
                
                metadata = payload.get("file_metadata", {})
                manu = metadata.get("Manufacturer", "Unknown").strip() or "Unknown"
                model = metadata.get("Modelname", "Unknown").strip() or "Unknown"
                
                if (manu, model) in existing_models:
                    skipped += 1
                    continue
                
                connection.execute("BEGIN")
                _, variants, measurements = ingest_json_file(
                    connection,
                    manufacturer_seen,
                    model_seen,
                    variant_seen,
                    db_path
                )
                connection.execute("COMMIT")
                
                new_variants += variants
                new_measurements += measurements
                
            except Exception as e:
                connection.execute("ROLLBACK")
                print(f"  ✗ Failed to add {db_path.name}: {e}")
        
        print(f"\nDuckDB Update Summary:")
        print(f"  Files processed: {len(database_files)}")
        print(f"  Skipped (already exist): {skipped}")
        print(f"  New variants added: {new_variants}")
        print(f"  New measurements added: {new_measurements}")
        
        # Print final counts
        counts = connection.execute("""
            SELECT 
                (SELECT COUNT(*) FROM manufacturers) as manu,
                (SELECT COUNT(*) FROM models) as models,
                (SELECT COUNT(*) FROM variants) as variants,
                (SELECT COUNT(*) FROM measurements) as measurements
        """).fetchone()
        
        print(f"\nFinal Database Counts:")
        print(f"  Manufacturers: {counts[0]:,}")
        print(f"  Models: {counts[1]:,}")
        print(f"  Variants: {counts[2]:,}")
        print(f"  Measurements: {counts[3]:,}")
        
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="Incremental pipeline update for new Keymark data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate new files only (no processing)",
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full rebuild (process all CSV files, not just new ones)",
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation step (faster but less safe)",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed validation output",
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("INCREMENTAL PIPELINE UPDATE")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine which files to process
    if args.full:
        print("\nMode: FULL REBUILD")
        csv_files = list(DATA_SOURCE.glob("*.csv"))
        print(f"Found {len(csv_files)} total CSV files")
    else:
        print("\nMode: INCREMENTAL (new files only)")
        new_files = get_new_files_from_sync_log()
        already_processed = get_already_processed()
        
        # Filter to only truly new files
        csv_files = []
        for csv_name, metadata in new_files:
            if csv_name not in already_processed:
                csv_path = DATA_SOURCE / csv_name
                if csv_path.exists():
                    csv_files.append(csv_path)
        
        print(f"New files to process: {len(csv_files)}")
        print(f"Already in staging: {len(already_processed)}")
    
    if not csv_files:
        print("\nNo new files to process. Database is up to date!")
        return
    
    # Step 1: Validation
    if not args.skip_validation:
        valid_files, invalid_files = run_validation(csv_files, verbose=args.verbose)
        
        if args.validate:
            print("\nValidation complete. Use --skip-validation to process files.")
            return
        
        csv_files = valid_files
        
        if not csv_files:
            print("\nNo valid files to process!")
            return
    
    # Step 2: Ingestion (CSV -> Staging JSONL)
    staging_files = run_ingestion(csv_files)
    
    if not staging_files:
        print("\nNo files were successfully ingested!")
        return
    
    # Step 3: Transform (Staging JSONL -> Database JSON)
    database_files = run_transform(staging_files)
    
    if not database_files:
        print("\nNo files were successfully transformed!")
        return
    
    # Step 4: Update DuckDB
    update_duckdb_incremental(database_files)
    
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
