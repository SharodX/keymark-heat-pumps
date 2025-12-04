"""Pydantic schemas representing measurement data."""

from pydantic import BaseModel


class Measurement(BaseModel):
    manufacturer_name: str
    model_name: str
    variant_name: str
    en_code: str
    dimension: str
    value: float | None = None
    unit: str | None = None
