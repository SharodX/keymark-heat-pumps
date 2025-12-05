"""API routes for listing available heat pumps."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.db.deps import get_duckdb
from backend.models.heat_pump import HeatPumpSummary
from backend.models.pagination import Page, PaginationMeta

router = APIRouter()


@router.get("/", response_model=Page[HeatPumpSummary])
def list_heat_pumps(
    search: str | None = Query(None, description="Filter manufacturer or subtype using ILIKE"),
    has_cold_climate: bool = Query(False, description="Only include heat pumps with colder climate data"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum heat pumps to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    connection = Depends(get_duckdb),
) -> Page[HeatPumpSummary]:
    """Return paginated heat pump summaries.
    
    Hierarchy: Manufacturer -> Subtype (product line) -> Model (specific configuration)
    """

    base_conditions: list[str] = []
    base_params: list[Any] = []

    if search:
        like = f"%{search}%"
        base_conditions.append("(manufacturer_name ILIKE ? OR subtype_name ILIKE ?)")
        base_params.extend([like, like])

    where_clause = f"WHERE {' AND '.join(base_conditions)}" if base_conditions else ""

    filtered_cte = f"""
        WITH grouped AS (
            SELECT manufacturer_name,
                   subtype_name,
                   model_name,
                   COUNT(*) AS measurement_count,
                   MAX(CASE WHEN split_part(dimension, '_', 2) = '2' THEN 1 ELSE 0 END) AS has_cold_climate
            FROM measurements
            {where_clause}
            GROUP BY manufacturer_name, subtype_name, model_name
        )
    """

    having_clause = "WHERE has_cold_climate = 1" if has_cold_climate else ""

    select_sql = (
        filtered_cte
        + "SELECT manufacturer_name, subtype_name, model_name, measurement_count, "
        "has_cold_climate FROM grouped "
        f"{having_clause} "
        "ORDER BY manufacturer_name, subtype_name, model_name "
        "LIMIT ? OFFSET ?"
    )

    select_params = [*base_params, limit, offset]
    cursor = connection.execute(select_sql, select_params)
    rows = cursor.fetchall()

    data = [
        HeatPumpSummary(
            manufacturer_name=row[0],
            subtype_name=row[1],
            model_name=row[2],
            measurement_count=row[3],
            has_cold_climate=bool(row[4]),
        )
        for row in rows
    ]

    count_sql = filtered_cte + f"SELECT COUNT(*) FROM grouped {having_clause}"
    total = connection.execute(count_sql, base_params).fetchone()[0]

    meta = PaginationMeta(
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(data)) < total,
    )

    return Page[HeatPumpSummary](data=data, meta=meta)
