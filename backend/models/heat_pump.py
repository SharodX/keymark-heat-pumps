"""Heat pump summary models used by the API."""

from pydantic import BaseModel


class HeatPumpSummary(BaseModel):
    """Summary of a heat pump model.
    
    Hierarchy: Manufacturer -> Subtype (product line) -> Model (specific configuration)
    """
    manufacturer_name: str
    subtype_name: str
    model_name: str
    measurement_count: int
    has_cold_climate: bool
