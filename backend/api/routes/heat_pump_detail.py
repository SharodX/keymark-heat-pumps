"""Heat pump detail endpoint for individual unit analysis."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db.deps import get_duckdb

router = APIRouter(prefix="/heat-pump", tags=["heat-pump-detail"])

@router.get("/detail")
def get_heat_pump_detail(
    manufacturer: str = Query(..., description="Manufacturer name"),
    subtype: str = Query(..., description="Subtype name"),
    model: str = Query(..., description="Model name"),
    temperature_level: str = Query(..., description="Temperature level code (4 or 5)"),
    climate_zone: str = Query(..., description="Climate zone code (1, 2, or 3)"),
    connection = Depends(get_duckdb),
) -> dict:
    """Get detailed performance curve data for a specific heat pump model and condition."""
    import json

    # Get all EN14825 measurements for this heat pump at specified condition
    dimension_pattern = f"{temperature_level}_{climate_zone}_%"

    query = """
        SELECT 
            m.en_code,
            m.dimension,
            m.value,
            sub.metadata,
            mod.properties
        FROM measurements m
        JOIN subtypes sub ON m.manufacturer_name = sub.manufacturer_name 
            AND m.subtype_name = sub.subtype_name
        JOIN models mod ON m.manufacturer_name = mod.manufacturer_name 
            AND m.subtype_name = mod.subtype_name 
            AND m.model_name = mod.model_name
        WHERE m.manufacturer_name = ?
            AND m.subtype_name = ?
            AND m.model_name = ?
            AND m.en_code LIKE 'EN14825_%'
            AND m.dimension LIKE ?
        ORDER BY m.en_code, m.dimension
        """

    results = connection.execute(
        query, [manufacturer, subtype, model, dimension_pattern]
    ).fetchall()

    if not results:
        raise HTTPException(status_code=404, detail="Heat pump not found")

    # Parse metadata and properties from first result
    metadata_str = results[0][3]
    properties_str = results[0][4] if len(results[0]) > 4 else None

    metadata = {}
    properties = {}

    if metadata_str:
        try:
            metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
        except Exception:  # noqa: BLE001 - defensive parsing guard
            pass

    if properties_str:
        try:
            properties = json.loads(properties_str) if isinstance(properties_str, str) else properties_str
        except Exception:  # noqa: BLE001 - defensive parsing guard
            pass

    # Organize data by EN code
    measurements = {}
    for row in results:
        en_code = row[0]
        dimension = row[1]
        value = row[2]

        if en_code not in measurements:
            measurements[en_code] = []

        measurements[en_code].append({
            "dimension": dimension,
            "value": value
        })

    return {
        "manufacturer": manufacturer,
        "subtype": subtype,
        "model": model,
        "temperature_level": temperature_level,
        "climate_zone": climate_zone,
        "metadata": metadata,
        "properties": properties,
        "measurements": measurements
    }
