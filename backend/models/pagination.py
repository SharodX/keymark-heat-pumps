"""Generic pagination helpers for API responses."""

from typing import Generic, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class Page(GenericModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta
