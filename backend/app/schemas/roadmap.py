"""Career roadmap contracts.

Superseded by `app.career_roadmap.schemas.roadmap` — the real, implemented
Career Roadmap feature's schema (phases/tasks/milestones, not a flat step
list — see backend/app/career_roadmap/README.md).
"""

from pydantic import BaseModel, Field


class RoadmapStep(BaseModel):
    order: int
    title: str
    description: str | None = None
    duration_weeks: int | None = None
    skills: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)


class Roadmap(BaseModel):
    id: str | None = None
    target_role: str
    horizon_months: int = 12
    steps: list[RoadmapStep] = Field(default_factory=list)
    generated_at: str | None = None


class RoadmapRequest(BaseModel):
    target_role: str
    horizon_months: int = Field(default=12, ge=1, le=60)
    focus_areas: list[str] = Field(default_factory=list)
