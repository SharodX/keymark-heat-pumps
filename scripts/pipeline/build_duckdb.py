#!/usr/bin/env python3
"""Build or refresh the DuckDB database from JSON heat pump files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Set, Tuple

import duckdb

SCHEMA_FILE = Path("backend/db/schema.sql")
DB_FILE = Path("data/keymark.duckdb")
DATA_DIR = Path("data/database")


def load_schema(connection: duckdb.DuckDBPyConnection) -> None:
    """Execute the schema SQL file."""
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    connection.execute(sql)


def reset_tables(connection: duckdb.DuckDBPyConnection) -> None:
    """Clear existing data to avoid duplicate rows on rebuild."""
    connection.execute("DELETE FROM measurements")
    connection.execute("DELETE FROM variants")
    connection.execute("DELETE FROM models")
    connection.execute("DELETE FROM manufacturers")


_number_pattern = re.compile(r"[-+]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _clean_text(value: object) -> Optional[str]:
    """Return a trimmed string if the input is a non-empty string."""
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            return candidate
    return None


def parse_numeric(value: object) -> Optional[float]:
    """Best-effort conversion of measurement values to float."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    # Replace comma decimal separators and strip whitespace
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
    
    # If it's already a number, return as-is
    if isinstance(value, (int, float)):
        return value
    
    # If it's a string that looks like an integer, convert it
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            return int(value)
        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass
    
    return value


def parse_properties(properties: dict) -> dict:
    """Parse and structure variant properties from JSON."""
    parsed = {}
    
    for key, value in properties.items():
        # Parse each property value (convert string numbers to int/float)
        parsed_value = parse_property_value(value)
        if parsed_value is not None:  # Only include non-null values
            parsed[key] = parsed_value
    
    return parsed


def parse_metadata(metadata: dict) -> dict:
    """Parse and structure metadata fields from JSON."""
    parsed = {}
    
    # Copy all fields as-is
    for key, value in metadata.items():
        if value and isinstance(value, str):
            value = value.strip()
        if value:  # Only include non-empty values
            parsed[key] = value
    
    # Parse specific fields for better querying
    if "Mass of Refrigerant" in parsed:
        mass_numeric = parse_numeric(parsed["Mass of Refrigerant"])
        if mass_numeric is not None:
            parsed["refrigerant_mass_kg"] = mass_numeric
    
    # Parse date if present
    if "Date" in parsed:
        date_str = parsed["Date"]
        # Try to parse common date formats: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD
        for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                from datetime import datetime
                dt = datetime.strptime(date_str, fmt)
                parsed["certification_date"] = dt.strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
    
    return parsed


def ingest_json_file(connection: duckdb.DuckDBPyConnection,
                     manufacturer_seen: Set[str],
                     model_seen: Set[Tuple[str, str]],
                     variant_seen: Set[Tuple[str, str, str]],
                     path: Path) -> Tuple[int, int, int]:
    """Load a single JSON database file."""
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    metadata = payload.get("file_metadata", {})
    manufacturer_name = metadata.get("Manufacturer", "Unknown").strip() or "Unknown"
    model_name = metadata.get("Modelname", "Unknown").strip() or "Unknown"

    if manufacturer_name not in manufacturer_seen:
        connection.execute(
            "INSERT OR IGNORE INTO manufacturers (name) VALUES (?)",
            [manufacturer_name],
        )
        manufacturer_seen.add(manufacturer_name)

    model_key = (manufacturer_name, model_name)
    if model_key not in model_seen:
        # Parse and store all metadata as JSON
        parsed_metadata = parse_metadata(metadata)
        import json as json_module
        metadata_json = json_module.dumps(parsed_metadata) if parsed_metadata else None
        
        connection.execute(
            "INSERT OR IGNORE INTO models (manufacturer_name, model_name, metadata) VALUES (?, ?, ?)",
            [manufacturer_name, model_name, metadata_json],
        )
        model_seen.add(model_key)

    variants_loaded = 0
    measurements_loaded = 0

    for idx, hp in enumerate(payload.get("heat_pumps", []), 1):
        variant_name = _clean_text(hp.get("variant")) or _clean_text(hp.get("title"))
        if not variant_name:
            variant_name = f"variant_{idx:03d}"

        base_variant_name = variant_name
        suffix = 2
        variant_key = (manufacturer_name, model_name, variant_name)
        while variant_key in variant_seen:
            variant_name = f"{base_variant_name}_{suffix}"
            variant_key = (manufacturer_name, model_name, variant_name)
            suffix += 1

        if variant_key not in variant_seen:
            # Parse and store variant properties
            properties = hp.get("properties", {})
            parsed_properties = parse_properties(properties)
            import json as json_module
            properties_json = json_module.dumps(parsed_properties) if parsed_properties else None
            
            connection.execute(
                "INSERT OR IGNORE INTO variants (manufacturer_name, model_name, variant_name, properties) "
                "VALUES (?, ?, ?, ?)",
                [manufacturer_name, model_name, variant_name, properties_json],
            )
            variant_seen.add(variant_key)
        variants_loaded += 1

        measurements = hp.get("measurements", {})
        for en_code, dimensions in measurements.items():
            if not isinstance(dimensions, dict):
                continue
            for dimension, raw_value in dimensions.items():
                numeric_value = parse_numeric(raw_value)
                if numeric_value is None:
                    continue
                connection.execute(
                    "INSERT INTO measurements (manufacturer_name, model_name, variant_name, en_code, dimension, value, unit) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [manufacturer_name, model_name, variant_name, en_code, dimension, numeric_value, None],
                )
                measurements_loaded += 1

    return 1, variants_loaded, measurements_loaded


def build_database() -> None:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    connection = duckdb.connect(str(DB_FILE))
    try:
        load_schema(connection)
        reset_tables(connection)

        manufacturer_seen: Set[str] = set()
        model_seen: Set[Tuple[str, str]] = set()
        variant_seen: Set[Tuple[str, str, str]] = set()

        files = sorted(DATA_DIR.glob("*.json"))
        total_files = len(files)

        total_variants = 0
        total_measurements = 0

        for idx, path in enumerate(files, 1):
            try:
                connection.execute("BEGIN")
                _, variants_added, measurements_added = ingest_json_file(
                    connection,
                    manufacturer_seen,
                    model_seen,
                    variant_seen,
                    path,
                )
                connection.execute("COMMIT")
            except Exception as exc:  # noqa: BLE001
                connection.execute("ROLLBACK")
                print(f"Failed to ingest {path.name}: {exc}")
                continue

            total_variants += variants_added
            total_measurements += measurements_added

            if idx % 100 == 0 or idx == total_files:
                print(f"Processed {idx}/{total_files} files…")

        print("\nDatabase build complete")
        print(f"  Manufacturers : {len(manufacturer_seen):,}")
        print(f"  Models        : {len(model_seen):,}")
        print(f"  Variants      : {total_variants:,}")
        print(f"  Measurements  : {total_measurements:,}")
        print(f"  DuckDB file   : {DB_FILE}")
    finally:
        connection.close()


if __name__ == "__main__":
    build_database()
