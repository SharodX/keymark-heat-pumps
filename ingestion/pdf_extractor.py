"""PDF extraction utilities for model tables."""

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pdfplumber

from . import IngestionMetrics, logger
from .csv_loader import normalize_header


class PDFExtractionError(Exception):
    """Raised when PDF parsing fails."""


def _flatten_table_rows(table: List[List[str]], headers: List[str]) -> Iterable[Dict[str, str]]:
    for row in table:
        record = {}
        for header, value in zip(headers, row):
            record[normalize_header(header)] = (value or "").strip()
        yield record


def _detect_header_row(table: List[List[str]]) -> Optional[List[str]]:
    if not table:
        return None
    candidate = table[0]
    normalized = [normalize_header(cell) for cell in candidate]
    if len(set(normalized)) == len(candidate):
        return [cell.strip() for cell in candidate]
    return None


def extract_pdf_tables(
    pdf_path: Path, metrics: IngestionMetrics | None = None, model_id: str | None = None
) -> List[Dict[str, str]]:
    """Extract tabular data and labeled values from a PDF.

    Each table row is augmented with ``model_id`` and ``submodel_id`` fields when
    columns for model or variant names exist.
    """

    logger.info("Extracting PDF tables from: %s", pdf_path)
    records: List[Dict[str, str]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables() or []
                for table_index, table in enumerate(tables, start=1):
                    headers = _detect_header_row(table)
                    body = table[1:] if headers else table
                    if not headers:
                        headers = [f"column_{i}" for i in range(len(table[0]))]
                    for row in _flatten_table_rows(body, headers):
                        row["source_page"] = page_index
                        row["source_table"] = table_index
                        if model_id:
                            row.setdefault("model_id", model_id)
                        else:
                            row.setdefault("model_id", row.get("model") or row.get("model_name"))
                        row.setdefault(
                            "submodel_id",
                            row.get("variant")
                            or row.get("submodel")
                            or row.get("sub_model")
                            or row.get("model_variant"),
                        )
                        records.append(row)
                if tables:
                    logger.info(
                        "Extracted %s tables from page %s", len(tables), page_index
                    )
                    if metrics:
                        metrics.add_pdf_tables(len(tables))

                text = page.extract_text() or ""
                labeled_values: List[Dict[str, str]] = []
                for line in text.splitlines():
                    if ":" not in line:
                        continue
                    label, _, value = line.partition(":")
                    labeled_values.append(
                        {
                            "label": normalize_header(label),
                            "value": value.strip(),
                            "source_page": page_index,
                            "source_table": None,
                            "model_id": model_id,
                        }
                    )
                records.extend(labeled_values)
                if labeled_values and metrics:
                    metrics.increment_extra("pdf_labeled_values", len(labeled_values))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to parse PDF %s", pdf_path)
        if metrics:
            metrics.mark_pdf_failure()
        raise PDFExtractionError(f"Failed to parse PDF {pdf_path}: {exc}") from exc

    if metrics:
        metrics.mark_pdf_success()
    logger.info("Extracted %s total rows from %s", len(records), pdf_path)
    return records
