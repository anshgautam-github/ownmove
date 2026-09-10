"""Shared response envelopes and primitives."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ErrorResponse(BaseModel):
    code: str
    detail: str
    details: dict | None = None
    request_id: str | None = None


class PageMeta(BaseModel):
    total: int = 0
    limit: int = 20
    offset: int = 0
    has_more: bool = False


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)
