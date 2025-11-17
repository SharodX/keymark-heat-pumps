"""CSV ingestion utilities."""

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from . import IngestionMetrics, logger


def normalize_header(header: str) -> str:
    """Normalize a CSV header by lower-casing and replacing whitespace with underscores."""

    return "_".join(header.strip().lower().split())


def load_csv_records(
    csv_path: Path,
    metrics: IngestionMetrics | None = None,
    model_id: str | None = None,
) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    """Load a CSV file and normalize its headers.

    Args:
        csv_path: Path to the CSV file.
        metrics: Optional metrics collector.
        model_id: Optional model identifier that will be added to each row.

    Returns:
        A tuple containing a list of normalized records and a canonical field map
        relating normalized headers back to their original names.
    """

    normalized_records: List[Dict[str, str]] = []
    field_map: Dict[str, str] = {}

    logger.info("Loading CSV file: %s", csv_path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        field_map = {normalize_header(h): h for h in reader.fieldnames or []}
        for row in reader:
            normalized = {
                normalize_header(key): value.strip() if isinstance(value, str) else value
                for key, value in row.items()
            }
            if model_id:
                normalized.setdefault("model_id", model_id)
            if "variant" in normalized:
                normalized.setdefault("submodel_id", normalized["variant"])
            elif "submodel" in normalized:
                normalized.setdefault("submodel_id", normalized["submodel"])
            elif "sub_model" in normalized:
                normalized.setdefault("submodel_id", normalized["sub_model"])
            normalized_records.append(normalized)

    row_count = len(normalized_records)
    logger.info("Processed %s rows from %s", row_count, csv_path)
    if metrics:
        metrics.add_rows(row_count)
    return normalized_records, field_map


def write_staging_jsonl(records: Iterable[Dict[str, str]], output_path: Path) -> None:
    """Write normalized records to a JSONL file in the staging area."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    logger.info("Wrote %s records to %s", count, output_path)
