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
        CREATE OR REPLACE VIEW variant_signatures AS
        SELECT
            manufacturer_name,
            model_name,
            variant_name,
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
            SELECT DISTINCT signature FROM variant_signatures
        )
        """
    )


def create_unique_tables(connection: DuckDBPyConnection) -> None:
    connection.execute("DROP TABLE IF EXISTS unique_variants")
    connection.execute("DROP TABLE IF EXISTS unique_measurements")
    connection.execute("DROP TABLE IF EXISTS variant_lookup")
    connection.execute("DROP VIEW IF EXISTS measurements")

    connection.execute(
        """
        CREATE TABLE unique_variants AS
        WITH signature_counts AS (
            SELECT
                signature,
                COUNT(*) AS variant_count,
                COUNT(DISTINCT manufacturer_name) AS manufacturer_count
            FROM variant_signatures
            GROUP BY signature
        ),
        manufacturer_lists AS (
            SELECT
                signature,
                to_json(list(manufacturer_name ORDER BY manufacturer_name)) AS manufacturers_json
            FROM (
                SELECT DISTINCT signature, manufacturer_name
                FROM variant_signatures
            )
            GROUP BY signature
        ),
        representatives AS (
            SELECT
                signature,
                manufacturer_name AS representative_manufacturer,
                model_name AS representative_model,
                variant_name AS representative_variant
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY signature
                           ORDER BY manufacturer_name, model_name, variant_name
                       ) AS rn
                FROM variant_signatures
            )
            WHERE rn = 1
        )
        SELECT
            sid.signature_id,
            sid.signature,
            rep.representative_manufacturer,
            rep.representative_model,
            rep.representative_variant,
            sc.variant_count,
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
        CREATE TABLE variant_lookup AS
        SELECT
            vs.manufacturer_name,
            vs.model_name,
            vs.variant_name,
            sid.signature_id
        FROM variant_signatures vs
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
        JOIN variant_signatures vs
          ON m.manufacturer_name = vs.manufacturer_name
         AND m.model_name = vs.model_name
         AND m.variant_name = vs.variant_name
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
            uv.representative_manufacturer AS manufacturer_name,
            uv.representative_model AS model_name,
            uv.representative_variant AS variant_name,
            um.en_code,
            um.dimension,
            um.value,
            um.unit
        FROM unique_measurements AS um
        JOIN unique_variants AS uv USING (signature_id)
        """
    )


def create_metadata_tables(connection: DuckDBPyConnection) -> None:
    """Materialize compatibility tables for manufacturers/models/variants."""
    connection.execute("DROP TABLE IF EXISTS manufacturers")
    connection.execute("DROP TABLE IF EXISTS models")
    connection.execute("DROP TABLE IF EXISTS variants")

    # Copy metadata for each representative model so API queries remain unchanged.
    connection.execute(
        """
        CREATE TABLE models AS
        WITH reps AS (
            SELECT DISTINCT
                representative_manufacturer AS manufacturer_name,
                representative_model AS model_name
            FROM unique_variants
        )
        SELECT
            reps.manufacturer_name,
            reps.model_name,
            src.models.metadata
        FROM reps
        LEFT JOIN src.models
          ON reps.manufacturer_name = src.models.manufacturer_name
         AND reps.model_name = src.models.model_name
        """
    )

    # Recreate the variants table using the representative variant for every signature.
    connection.execute(
        """
        CREATE TABLE variants AS
        SELECT
            uv.representative_manufacturer AS manufacturer_name,
            uv.representative_model AS model_name,
            uv.representative_variant AS variant_name,
            src.variants.properties
        FROM unique_variants AS uv
        LEFT JOIN src.variants
          ON uv.representative_manufacturer = src.variants.manufacturer_name
         AND uv.representative_model = src.variants.model_name
         AND uv.representative_variant = src.variants.variant_name
        """
    )

    # Manufacturers can be derived directly from the (now reduced) models table.
    connection.execute(
        """
        CREATE TABLE manufacturers AS
        SELECT DISTINCT manufacturer_name AS name
        FROM models
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
        count = connection.execute("SELECT COUNT(*) FROM unique_variants").fetchone()[0]
    finally:
        connection.close()
    return count


def main() -> None:
    args = parse_args()
    count = build_unique_database(args.source, args.target, args.force)
    print(f"Created unique database at {args.target} with {count} distinct signatures")


if __name__ == "__main__":
    main()
