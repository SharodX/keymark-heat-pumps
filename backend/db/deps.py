"""Database dependencies for FastAPI routes."""

from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
import os

import duckdb
from fastapi import HTTPException, status

DB_ENV_VAR = "KEYMARK_DB_PATH"
DB_CANDIDATES = (
    Path("data/keymark_unique.duckdb"),
    Path("data/keymark.duckdb"),
)


@lru_cache(maxsize=1)
def get_db_path() -> Path:
    """Resolve the DuckDB path using env override and sane fallbacks."""
    env_override = os.environ.get(DB_ENV_VAR)
    if env_override:
        return Path(env_override).expanduser()

    for candidate in DB_CANDIDATES:
        path = candidate.expanduser()
        if path.exists():
            return path

    # Default to the first candidate when nothing exists so the error message stays useful.
    return DB_CANDIDATES[0].expanduser()


def get_duckdb() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a DuckDB connection for the duration of a request."""
    db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"DuckDB file not found at {db_path}. "
                f"Set {DB_ENV_VAR} to override the location."
            ),
        )

    connection = duckdb.connect(str(db_path))
    try:
        yield connection
    finally:
        connection.close()
