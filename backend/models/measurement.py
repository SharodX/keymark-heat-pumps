"""Pydantic schemas representing measurement data."""

from pydantic import BaseModel


class Measurement(BaseModel):
    """A single EN measurement for a heat pump model.
    
    Hierarchy: Manufacturer -> Subtype (product line) -> Model (specific configuration)
    """
    manufacturer_name: str
    subtype_name: str
    model_name: str
    en_code: str
    dimension: str
    value: float | None = None
    unit: str | None = None
