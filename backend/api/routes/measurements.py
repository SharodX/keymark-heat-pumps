"""API routes for working with measurement data."""

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.db.deps import get_duckdb
from backend.models.measurement import Measurement
from backend.models.pagination import Page, PaginationMeta

router = APIRouter()


CLIMATE_TOKEN_MAP = {
    "warmer": "1",
    "colder": "2",
    "average": "3",
}


@router.get("/", response_model=Page[Measurement])
def list_measurements(
    manufacturer: str | None = Query(None, description="Filter by manufacturer name"),
    subtype: str | None = Query(None, description="Filter by subtype name (product line)"),
    model: str | None = Query(None, description="Filter by model name (specific configuration)"),
    en_code: str | None = Query(None, description="Filter by EN code"),
    dimension: str | None = Query(None, description="Filter by measurement dimension"),
    climates: list[str] | None = Query(
        None,
        description="One or more climate zones: warmer, average, colder",
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    connection = Depends(get_duckdb),
) -> Page[Measurement]:
    """Return a paginated list of measurements.
    
    Hierarchy: Manufacturer -> Subtype (product line) -> Model (specific configuration)
    """

    conditions: list[str] = []
    parameters: list[Any] = []

    def add_condition(column: str, value: str | None) -> None:
        if value:
            conditions.append(f"{column} = ?")
            parameters.append(value)

    add_condition("manufacturer_name", manufacturer)
    add_condition("subtype_name", subtype)
    add_condition("model_name", model)
    add_condition("en_code", en_code)
    add_condition("dimension", dimension)

    if climates:
        tokens = _parse_climate_tokens(climates)
        placeholders = ", ".join("?" for _ in tokens)
        conditions.append(
            f"split_part(dimension, '_', 2) IN ({placeholders})"
        )
        parameters.extend(tokens)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    select_sql = (
        "SELECT manufacturer_name, subtype_name, model_name, en_code, dimension, value, unit "
        "FROM measurements "
        f"{where_clause} "
        "ORDER BY manufacturer_name, subtype_name, model_name, en_code, dimension "
        "LIMIT ? OFFSET ?"
    )

    select_params = [*parameters, limit, offset]
    cursor = connection.execute(select_sql, select_params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in (cursor.description or [])]

    data = _rows_to_models(rows, columns)

    count_sql = f"SELECT COUNT(*) FROM measurements {where_clause}"
    total = connection.execute(count_sql, parameters).fetchone()[0]

    meta = PaginationMeta(
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(data)) < total,
    )

    return Page[Measurement](data=data, meta=meta)


def _rows_to_models(rows: Sequence[Sequence[Any]], columns: Sequence[str]) -> list[Measurement]:
    """Convert DuckDB tuples into Pydantic models."""
    if not columns:
        return []

    return [
        Measurement.model_validate(dict(zip(columns, row)))
        for row in rows
    ]


def _parse_climate_tokens(climates: list[str]) -> list[str]:
    tokens: list[str] = []
    for climate in climates:
        key = climate.strip().lower()
        if key not in CLIMATE_TOKEN_MAP:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported climate value: {climate}",
            )
        tokens.append(CLIMATE_TOKEN_MAP[key])
    unique_tokens = sorted(set(tokens))
    return unique_tokens
