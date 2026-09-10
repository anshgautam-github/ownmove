"""Opportunity contracts — mirrors the public.opportunities table."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

OpportunityCategory = Literal[
    "internships",
    "programs",
    "hackathons",
    "open-source",
    "certifications",
    "challenges",
    "communities",
    "events",
]


class Opportunity(BaseModel):
    id: str
    category: OpportunityCategory
    title: str
    organization: str | None = None
    logo_url: str | None = None
    description: str | None = None
    location: str | None = None
    is_remote: bool = False
    apply_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    eligible_years: list[int] = Field(default_factory=list)
    duration: str | None = None
    application_deadline: date | None = None
    posted_at: datetime | None = None


class OpportunitySearchQuery(BaseModel):
    query: str | None = None
    category: OpportunityCategory | None = None
    is_remote: bool | None = None
    tags: list[str] = Field(default_factory=list)
    graduation_year: int | None = None
    semantic: bool = True
