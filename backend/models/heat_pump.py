"""Heat pump summary models used by the API."""

from pydantic import BaseModel


class HeatPumpSummary(BaseModel):
    manufacturer_name: str
    model_name: str
    variant_name: str
    measurement_count: int
    has_cold_climate: bool
