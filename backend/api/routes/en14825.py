"""EN14825 analytics API routes."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.db.deps import get_duckdb

router = APIRouter()


@router.get("/metadata")
def get_en14825_metadata(connection = Depends(get_duckdb)) -> dict:
    """Get metadata for EN14825 filters (available options for dropdowns)."""
    # Get available refrigerants
    refrigerants = connection.execute("""
            SELECT DISTINCT json_extract_string(metadata, '$.Refrigerant') as refrigerant
            FROM subtypes
            WHERE json_extract_string(metadata, '$.Refrigerant') IS NOT NULL
            ORDER BY refrigerant
        """).fetchall()
        
    # Get refrigerant mass range
    mass_range = connection.execute("""
            SELECT 
                MIN(CAST(json_extract_string(metadata, '$.refrigerant_mass_kg') AS DOUBLE)) as min_mass,
                MAX(CAST(json_extract_string(metadata, '$.refrigerant_mass_kg') AS DOUBLE)) as max_mass
            FROM subtypes
            WHERE json_extract_string(metadata, '$.refrigerant_mass_kg') IS NOT NULL
        """).fetchone()
        
    # Get certification date range
    date_range = connection.execute("""
            SELECT 
                MIN(json_extract_string(metadata, '$.certification_date')) as min_date,
                MAX(json_extract_string(metadata, '$.certification_date')) as max_date
            FROM subtypes
            WHERE json_extract_string(metadata, '$.certification_date') IS NOT NULL
        """).fetchone()
        
    # Get heat pump types
    types = connection.execute("""
            SELECT DISTINCT json_extract_string(metadata, '$.Type') as type
            FROM subtypes
            WHERE json_extract_string(metadata, '$.Type') IS NOT NULL
            ORDER BY type
        """).fetchall()
        
    # Get manufacturers
    manufacturers = connection.execute("""
            SELECT DISTINCT manufacturer_name
            FROM subtypes
            ORDER BY manufacturer_name
        """).fetchall()
        
    # Get available temperature levels (from dimension codes)
    # Position 0: 4=35°C (low temp, high SCOP), 5=55°C (medium temp, low SCOP)
    temp_levels = [
        {"code": "4", "label": "35°C"},
        {"code": "5", "label": "55°C"}
    ]

    # Get available climate zones (from dimension codes)
    # Position 1: 1=Average, 2=Colder, 3=Warmer
    climate_zones = [
        {"code": "1", "label": "Average"},
        {"code": "2", "label": "Colder"},
        {"code": "3", "label": "Warmer"}
    ]
        
    # Get EN14825 measurement ranges for key metrics
    # EN14825_001 = ηs (efficiency %), EN14825_002 = Prated (kW), EN14825_003 = SCOP
    en14825_ranges = connection.execute("""
            SELECT 
                MIN(CASE WHEN en_code = 'EN14825_002' THEN value END) as min_prated,
                MAX(CASE WHEN en_code = 'EN14825_002' THEN value END) as max_prated,
                MIN(CASE WHEN en_code = 'EN14825_003' THEN value END) as min_scop,
                MAX(CASE WHEN en_code = 'EN14825_003' THEN value END) as max_scop,
                MIN(CASE WHEN en_code = 'EN14825_004' THEN value END) as min_tbiv,
                MAX(CASE WHEN en_code = 'EN14825_004' THEN value END) as max_tbiv,
                MIN(CASE WHEN en_code = 'EN14825_005' THEN value END) as min_tol,
                MAX(CASE WHEN en_code = 'EN14825_005' THEN value END) as max_tol,
                MIN(CASE WHEN en_code = 'EN14825_028' THEN value END) as min_psup,
                MAX(CASE WHEN en_code = 'EN14825_028' THEN value END) as max_psup
            FROM measurements
            WHERE en_code IN ('EN14825_002', 'EN14825_003', 'EN14825_004', 'EN14825_005', 'EN14825_028')
        """).fetchone()
    
    return {
        "refrigerants": [r[0] for r in refrigerants],
        "refrigerant_mass_range": {
            "min": mass_range[0] if mass_range[0] else 0,
            "max": mass_range[1] if mass_range[1] else 10
        },
        "certification_date_range": {
            "min": date_range[0] if date_range[0] else "2020-01-01",
            "max": date_range[1] if date_range[1] else "2025-12-31"
        },
        "types": [t[0] for t in types],
        "manufacturers": [m[0] for m in manufacturers],
        "temperature_levels": temp_levels,
        "climate_zones": climate_zones,
        "en14825_ranges": {
            "prated": {"min": en14825_ranges[0] or 0, "max": en14825_ranges[1] or 1000},
            "scop": {"min": en14825_ranges[2] or 0, "max": en14825_ranges[3] or 10},
            "tbiv": {"min": en14825_ranges[4] or -30, "max": en14825_ranges[5] or 10},
            "tol": {"min": en14825_ranges[6] or -30, "max": en14825_ranges[7] or 10},
            "psup": {"min": en14825_ranges[8] or 0, "max": en14825_ranges[9] or 50}
        }
    }


@router.get("/data")
def get_en14825_data(
    # Temperature and climate filters
    temperature_level: Optional[str] = Query(None, description="Temperature level: 4 (55°C) or 5 (35°C)"),
    climate_zone: Optional[str] = Query(None, description="Climate zone: 1 (Average), 2 (Colder), 3 (Warmer)"),
    
    # EN14825 metric filters
    prated_min: Optional[float] = Query(None, description="Minimum Prated (kW)"),
    prated_max: Optional[float] = Query(None, description="Maximum Prated (kW)"),
    scop_min: Optional[float] = Query(None, description="Minimum SCOP"),
    scop_max: Optional[float] = Query(None, description="Maximum SCOP"),
    tbiv_min: Optional[float] = Query(None, description="Minimum Tbiv (°C)"),
    tbiv_max: Optional[float] = Query(None, description="Maximum Tbiv (°C)"),
    tol_min: Optional[float] = Query(None, description="Minimum TOL (°C)"),
    tol_max: Optional[float] = Query(None, description="Maximum TOL (°C)"),
    psup_min: Optional[float] = Query(None, description="Minimum PSUP (kW)"),
    psup_max: Optional[float] = Query(None, description="Maximum PSUP (kW)"),
    
    # Model metadata filters
    refrigerant: Optional[list[str]] = Query(None, description="Refrigerant types"),
    refrigerant_mass_min: Optional[float] = Query(None, description="Minimum refrigerant mass (kg)"),
    refrigerant_mass_max: Optional[float] = Query(None, description="Maximum refrigerant mass (kg)"),
    certification_date_from: Optional[str] = Query(None, description="Certification date from (YYYY-MM-DD)"),
    certification_date_to: Optional[str] = Query(None, description="Certification date to (YYYY-MM-DD)"),
    hp_type: Optional[list[str]] = Query(None, description="Heat pump types"),
    manufacturer: Optional[list[str]] = Query(None, description="Manufacturers"),
    
    # Variant property filters
    reversibility: Optional[int] = Query(None, description="Reversibility: 0 or 1"),
    power_supply: Optional[int] = Query(None, description="Power supply type: 1, 2, or 3"),
    
    # Pagination
    limit: int = Query(1000, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    connection = Depends(get_duckdb),
) -> dict:
    """Get EN14825 data with comprehensive filtering."""
    # Build WHERE clauses
    where_clauses = []
    params = []

    # Build dimension filter for temperature/climate
    dimension_pattern = None
    if temperature_level and climate_zone:
        dimension_pattern = f"{temperature_level}_{climate_zone}_%"
    elif temperature_level:
        dimension_pattern = f"{temperature_level}_%"
    elif climate_zone:
        dimension_pattern = f"%_{climate_zone}_%"

    if dimension_pattern:
        where_clauses.append("m.dimension LIKE ?")
        params.append(dimension_pattern)

    # Refrigerant filter
    if refrigerant:
        placeholders = ','.join(['?' for _ in refrigerant])
        where_clauses.append(
            f"json_extract_string(sub.metadata, '$.Refrigerant') IN ({placeholders})"
        )
        params.extend(refrigerant)

    # Refrigerant mass filter
    if refrigerant_mass_min is not None:
        where_clauses.append(
            "CAST(json_extract_string(sub.metadata, '$.refrigerant_mass_kg') AS DOUBLE) >= ?"
        )
        params.append(refrigerant_mass_min)
    if refrigerant_mass_max is not None:
        where_clauses.append(
            "CAST(json_extract_string(sub.metadata, '$.refrigerant_mass_kg') AS DOUBLE) <= ?"
        )
        params.append(refrigerant_mass_max)

    # Certification date filter
    if certification_date_from:
        where_clauses.append("json_extract_string(sub.metadata, '$.certification_date') >= ?")
        params.append(certification_date_from)
    if certification_date_to:
        where_clauses.append("json_extract_string(sub.metadata, '$.certification_date') <= ?")
        params.append(certification_date_to)

    # Type filter
    if hp_type:
        placeholders = ','.join(['?' for _ in hp_type])
        where_clauses.append(f"json_extract_string(sub.metadata, '$.Type') IN ({placeholders})")
        params.extend(hp_type)

    # Manufacturer filter
    if manufacturer:
        placeholders = ','.join(['?' for _ in manufacturer])
        where_clauses.append(f"sub.manufacturer_name IN ({placeholders})")
        params.extend(manufacturer)

    # Model property filters
    if reversibility is not None:
        where_clauses.append("CAST(json_extract_string(mdl.properties, '$.reversibility') AS INTEGER) = ?")
        params.append(reversibility)
    if power_supply is not None:
        where_clauses.append("CAST(json_extract_string(mdl.properties, '$.powerSupply') AS INTEGER) = ?")
        params.append(power_supply)

    where_clause = " AND " + " AND ".join(where_clauses) if where_clauses else ""

    # Main query to get EN14825 data
    # EN14825_002 = Prated (kW), EN14825_003 = SCOP, EN14825_004 = Tbiv, EN14825_005 = TOL, EN14825_028 = PSUP
    # EN14825_001 = ηs (efficiency %), EN14825_022 = WTOL (°C), EN14825_029 = Qhe (kWh/year)
    query = f"""
        WITH en14825_metrics AS (
            SELECT 
                m.manufacturer_name,
                m.subtype_name,
                m.model_name,
                m.dimension,
                MAX(CASE WHEN m.en_code = 'EN14825_002' THEN m.value END) as prated,
                MAX(CASE WHEN m.en_code = 'EN14825_003' THEN m.value END) as scop,
                MAX(CASE WHEN m.en_code = 'EN14825_004' THEN m.value END) as tbiv,
                MAX(CASE WHEN m.en_code = 'EN14825_005' THEN m.value END) as tol,
                MAX(CASE WHEN m.en_code = 'EN14825_028' THEN m.value END) as psup,
                MAX(CASE WHEN m.en_code = 'EN14825_001' THEN m.value END) as efficiency_pct,
                MAX(CASE WHEN m.en_code = 'EN14825_022' THEN m.value END) as wtol,
                MAX(CASE WHEN m.en_code = 'EN14825_029' THEN m.value END) as annual_energy_kwh,
                sub.metadata,
                mdl.properties
            FROM measurements m
            JOIN subtypes sub ON m.manufacturer_name = sub.manufacturer_name AND m.subtype_name = sub.subtype_name
            JOIN models mdl ON m.manufacturer_name = mdl.manufacturer_name 
                AND m.subtype_name = mdl.subtype_name 
                AND m.model_name = mdl.model_name
            WHERE m.en_code IN ('EN14825_001', 'EN14825_002', 'EN14825_003', 'EN14825_004', 'EN14825_005', 'EN14825_022', 'EN14825_028', 'EN14825_029')
                {where_clause}
            GROUP BY m.manufacturer_name, m.subtype_name, m.model_name, m.dimension, sub.metadata, mdl.properties
        )
        SELECT *
        FROM en14825_metrics
        WHERE 1=1
            {f"AND prated >= {prated_min}" if prated_min is not None else ""}
            {f"AND prated <= {prated_max}" if prated_max is not None else ""}
            {f"AND scop >= {scop_min}" if scop_min is not None else ""}
            {f"AND scop <= {scop_max}" if scop_max is not None else ""}
            {f"AND tbiv >= {tbiv_min}" if tbiv_min is not None else ""}
            {f"AND tbiv <= {tbiv_max}" if tbiv_max is not None else ""}
            {f"AND tol >= {tol_min}" if tol_min is not None else ""}
            {f"AND tol <= {tol_max}" if tol_max is not None else ""}
            {f"AND psup >= {psup_min}" if psup_min is not None else ""}
            {f"AND psup <= {psup_max}" if psup_max is not None else ""}
        ORDER BY manufacturer_name, subtype_name, model_name, dimension
        LIMIT ? OFFSET ?
        """
        
    params.extend([limit, offset])
    
    results = connection.execute(query, params).fetchall()
    
    # Get total count
    count_query = f"""
        WITH en14825_metrics AS (
            SELECT 
                m.manufacturer_name,
                m.subtype_name,
                m.model_name,
                m.dimension,
                MAX(CASE WHEN m.en_code = 'EN14825_002' THEN m.value END) as prated,
                MAX(CASE WHEN m.en_code = 'EN14825_003' THEN m.value END) as scop,
                MAX(CASE WHEN m.en_code = 'EN14825_004' THEN m.value END) as tbiv,
                MAX(CASE WHEN m.en_code = 'EN14825_005' THEN m.value END) as tol,
                MAX(CASE WHEN m.en_code = 'EN14825_028' THEN m.value END) as psup
            FROM measurements m
            JOIN subtypes sub ON m.manufacturer_name = sub.manufacturer_name AND m.subtype_name = sub.subtype_name
            JOIN models mdl ON m.manufacturer_name = mdl.manufacturer_name 
                AND m.subtype_name = mdl.subtype_name 
                AND m.model_name = mdl.model_name
            WHERE m.en_code IN ('EN14825_002', 'EN14825_003', 'EN14825_004', 'EN14825_005', 'EN14825_028')
                {where_clause}
            GROUP BY m.manufacturer_name, m.subtype_name, m.model_name, m.dimension
        )
        SELECT COUNT(*)
        FROM en14825_metrics
        WHERE 1=1
            {f"AND prated >= {prated_min}" if prated_min is not None else ""}
            {f"AND prated <= {prated_max}" if prated_max is not None else ""}
            {f"AND scop >= {scop_min}" if scop_min is not None else ""}
            {f"AND scop <= {scop_max}" if scop_max is not None else ""}
            {f"AND tbiv >= {tbiv_min}" if tbiv_min is not None else ""}
            {f"AND tbiv <= {tbiv_max}" if tbiv_max is not None else ""}
            {f"AND tol >= {tol_min}" if tol_min is not None else ""}
            {f"AND tol <= {tol_max}" if tol_max is not None else ""}
            {f"AND psup >= {psup_min}" if psup_min is not None else ""}
            {f"AND psup <= {psup_max}" if psup_max is not None else ""}
        """
        
    total_count = connection.execute(count_query, params[:-2]).fetchone()[0]  # Exclude limit/offset params
    
    # Format results
    data = []
    for row in results:
        # Parse JSON strings from DuckDB
        # Row order: manufacturer, subtype, model, dimension, prated, scop, tbiv, tol, psup, efficiency_pct, wtol, annual_energy_kwh, metadata, properties
        metadata = {}
        properties = {}
        
        if row[12]:
            try:
                metadata = json.loads(row[12]) if isinstance(row[12], str) else row[12]
            except Exception:  # noqa: BLE001 - defensive parsing guard
                pass
        
        if len(row) > 13 and row[13]:
            try:
                properties = json.loads(row[13]) if isinstance(row[13], str) else row[13]
            except Exception:  # noqa: BLE001 - defensive parsing guard
                pass
        
        data.append({
            "manufacturer": row[0],
            "subtype": row[1],
            "model": row[2],
            "dimension": row[3],
            "temperature_level": row[3][0] if row[3] else None,
            "climate_zone": row[3][2] if len(row[3]) > 2 else None,
            "prated": row[4],
            "scop": row[5],
            "tbiv": row[6],
            "tol": row[7],
            "psup": row[8],
            "efficiency_pct": row[9],
            "wtol": row[10],
            "annual_energy_kwh": row[11],
            "refrigerant": metadata.get("Refrigerant"),
            "refrigerant_mass_kg": metadata.get("refrigerant_mass_kg"),
            "certification_date": metadata.get("certification_date"),
            "type": metadata.get("Type"),
            "reversibility": properties.get("reversibility"),
            "power_supply": properties.get("powerSupply")
        })
    
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "data": data
    }
