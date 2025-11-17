"""Ingestion utilities for heat pump datasets."""

import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger("ingestion")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@dataclass
class IngestionMetrics:
    """Track ingestion statistics for CSV and PDF processing."""

    csv_rows_processed: int = 0
    pdf_tables_extracted: int = 0
    pdf_parse_successes: int = 0
    pdf_parse_failures: int = 0
    extra: Dict[str, int] = field(default_factory=dict)

    def add_rows(self, count: int) -> None:
        self.csv_rows_processed += count
        logger.debug("Added %s CSV rows; total=%s", count, self.csv_rows_processed)

    def add_pdf_tables(self, count: int) -> None:
        self.pdf_tables_extracted += count
        logger.debug(
            "Added %s PDF tables; total=%s", count, self.pdf_tables_extracted
        )

    def mark_pdf_success(self) -> None:
        self.pdf_parse_successes += 1
        logger.debug(
            "Marked PDF parse success; total=%s", self.pdf_parse_successes
        )

    def mark_pdf_failure(self) -> None:
        self.pdf_parse_failures += 1
        logger.debug(
            "Marked PDF parse failure; total=%s", self.pdf_parse_failures
        )

    def increment_extra(self, key: str, count: int = 1) -> None:
        self.extra[key] = self.extra.get(key, 0) + count
        logger.debug("Incremented %s metric by %s; total=%s", key, count, self.extra[key])


__all__ = ["IngestionMetrics", "logger"]
