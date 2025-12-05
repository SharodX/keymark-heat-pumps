#!/usr/bin/env python3
"""Create a reduced DuckDB containing only unique heat pump signatures."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
from duckdb import DuckDBPyConnection

DEFAULT_SOURCE = Path("data/keymark.duckdb")
DEFAULT_TARGET = Path("data/keymark_unique.duckdb")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the full keymark.duckdb file",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Output path for the reduced DuckDB",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target database if it already exists",
    )
    return parser.parse_args()


def ensure_clean_target(target: Path, force: bool) -> None:
    if target.exists():
        if not force:
            raise FileExistsError(
                f"Target database {target} already exists. Pass --force to overwrite."
            )
        target.unlink()


def attach_source(connection: DuckDBPyConnection, source: Path) -> None:
    escaped = str(source).replace("'", "''")
    connection.execute(f"ATTACH DATABASE '{escaped}' AS src")


def create_variant_signature_view(connection: DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE OR REPLACE VIEW model_signatures AS
        SELECT
            manufacturer_name,
            subtype_name,
            model_name,
            string_agg(
                dimension || ':' || en_code || '=' || coalesce(CAST(value AS VARCHAR), 'NULL'),
                ',' ORDER BY dimension, en_code
            ) AS signature
        FROM src.measurements
        GROUP BY 1, 2, 3
        """
    )


def create_signature_id_table(connection: DuckDBPyConnection) -> None:
    connection.execute("DROP TABLE IF EXISTS signature_ids")
    connection.execute(
        """
        CREATE TEMP TABLE signature_ids AS
        SELECT
            signature,
            ROW_NUMBER() OVER (ORDER BY signature) AS signature_id
        FROM (
            SELECT DISTINCT signature FROM model_signatures
        )
        """
    )


def create_unique_tables(connection: DuckDBPyConnection) -> None:
    connection.execute("DROP TABLE IF EXISTS unique_models")
    connection.execute("DROP TABLE IF EXISTS unique_measurements")
    connection.execute("DROP TABLE IF EXISTS model_lookup")
    connection.execute("DROP VIEW IF EXISTS measurements")

    connection.execute(
        """
        CREATE TABLE unique_models AS
        WITH signature_counts AS (
            SELECT
                signature,
                COUNT(*) AS model_count,
                COUNT(DISTINCT manufacturer_name) AS manufacturer_count
            FROM model_signatures
            GROUP BY signature
        ),
        manufacturer_lists AS (
            SELECT
                signature,
                to_json(list(manufacturer_name ORDER BY manufacturer_name)) AS manufacturers_json
            FROM (
                SELECT DISTINCT signature, manufacturer_name
                FROM model_signatures
            )
            GROUP BY signature
        ),
        representatives AS (
            SELECT
                signature,
                manufacturer_name AS representative_manufacturer,
                subtype_name AS representative_subtype,
                model_name AS representative_model
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY signature
                           ORDER BY manufacturer_name, subtype_name, model_name
                       ) AS rn
                FROM model_signatures
            )
            WHERE rn = 1
        )
        SELECT
            sid.signature_id,
            sid.signature,
            rep.representative_manufacturer,
            rep.representative_subtype,
            rep.representative_model,
            sc.model_count,
            sc.manufacturer_count,
            ml.manufacturers_json::JSON AS manufacturers
        FROM signature_ids sid
        JOIN signature_counts sc USING (signature)
        JOIN representatives rep USING (signature)
        JOIN manufacturer_lists ml USING (signature)
        """
    )

    connection.execute(
        """
        CREATE TABLE model_lookup AS
        SELECT
            ms.manufacturer_name,
            ms.subtype_name,
            ms.model_name,
            sid.signature_id
        FROM model_signatures ms
        JOIN signature_ids sid USING (signature)
        """
    )

    connection.execute(
        """
        CREATE TABLE unique_measurements AS
        SELECT DISTINCT
            sid.signature_id,
            m.en_code,
            m.dimension,
            m.value,
            m.unit
        FROM src.measurements m
        JOIN model_signatures ms
          ON m.manufacturer_name = ms.manufacturer_name
         AND m.subtype_name = ms.subtype_name
         AND m.model_name = ms.model_name
        JOIN signature_ids sid USING (signature)
        """
    )

    create_measurements_view(connection)


def create_measurements_view(connection: DuckDBPyConnection) -> None:
    """Expose a compatibility view that mirrors the original measurements table."""
    connection.execute(
        """
        CREATE OR REPLACE VIEW measurements AS
        SELECT
            um.representative_manufacturer AS manufacturer_name,
            um.representative_subtype AS subtype_name,
            um.representative_model AS model_name,
            umeas.en_code,
            umeas.dimension,
            umeas.value,
            umeas.unit
        FROM unique_measurements AS umeas
        JOIN unique_models AS um USING (signature_id)
        """
    )


def create_metadata_tables(connection: DuckDBPyConnection) -> None:
    """Materialize compatibility tables for manufacturers/subtypes/models."""
    connection.execute("DROP TABLE IF EXISTS manufacturers")
    connection.execute("DROP TABLE IF EXISTS subtypes")
    connection.execute("DROP TABLE IF EXISTS models")

    # Copy metadata for each representative subtype so API queries remain unchanged.
    connection.execute(
        """
        CREATE TABLE subtypes AS
        WITH reps AS (
            SELECT DISTINCT
                representative_manufacturer AS manufacturer_name,
                representative_subtype AS subtype_name
            FROM unique_models
        )
        SELECT
            reps.manufacturer_name,
            reps.subtype_name,
            src.subtypes.metadata
        FROM reps
        LEFT JOIN src.subtypes
          ON reps.manufacturer_name = src.subtypes.manufacturer_name
         AND reps.subtype_name = src.subtypes.subtype_name
        """
    )

    # Recreate the models table using the representative model for every signature.
    connection.execute(
        """
        CREATE TABLE models AS
        SELECT
            um.representative_manufacturer AS manufacturer_name,
            um.representative_subtype AS subtype_name,
            um.representative_model AS model_name,
            src.models.properties
        FROM unique_models AS um
        LEFT JOIN src.models
          ON um.representative_manufacturer = src.models.manufacturer_name
         AND um.representative_subtype = src.models.subtype_name
         AND um.representative_model = src.models.model_name
        """
    )

    # Manufacturers can be derived directly from the (now reduced) subtypes table.
    connection.execute(
        """
        CREATE TABLE manufacturers AS
        SELECT DISTINCT manufacturer_name AS name
        FROM subtypes
        WHERE manufacturer_name IS NOT NULL
        """
    )


def build_unique_database(source: Path, target: Path, force: bool) -> int:
    if not source.exists():
        raise FileNotFoundError(f"Source database not found: {source}")

    ensure_clean_target(target, force)
    target.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(target))
    try:
        attach_source(connection, source)
        create_variant_signature_view(connection)
        create_signature_id_table(connection)
        create_unique_tables(connection)
        create_metadata_tables(connection)
        count = connection.execute("SELECT COUNT(*) FROM unique_models").fetchone()[0]
    finally:
        connection.close()
    return count


def main() -> None:
    args = parse_args()
    count = build_unique_database(args.source, args.target, args.force)
    print(f"Created unique database at {args.target} with {count} distinct signatures")


if __name__ == "__main__":
    main()
