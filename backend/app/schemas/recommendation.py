"""Recommendation contracts."""

from pydantic import BaseModel, Field

from app.schemas.opportunity import Opportunity


class MatchReason(BaseModel):
    factor: str
    weight: float
    detail: str | None = None


class RecommendedOpportunity(BaseModel):
    opportunity: Opportunity
    score: float = Field(ge=0, le=1)
    reasons: list[MatchReason] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    items: list[RecommendedOpportunity] = Field(default_factory=list)
    generated_at: str | None = None
    model: str | None = None


class MatchRequest(BaseModel):
    opportunity_id: str
