"""Profile request/response contracts.

Field names are camelCase-free on the wire by design: the backend speaks
snake_case, the frontend service layer maps to its own shape (it already does
this for the direct-Supabase path in services/supabase/profiles.js).
"""

from datetime import date
from pydantic import BaseModel, Field


class ExperienceBase(BaseModel):
    title: str | None = None
    company: str | None = None
    experience_type: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    currently_working: bool = False
    description: str | None = None
    skills_used: list[str] = Field(default_factory=list)


class Experience(ExperienceBase):
    id: str


class ProfileBase(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    bio: str | None = None
    city: str | None = None
    country: str | None = None
    college_name: str | None = None
    education_level: str | None = None
    degree: str | None = None
    branch: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    graduation_status: str | None = None
    career_interests: list[str] = Field(default_factory=list)
    current_skills: list[str] = Field(default_factory=list)
    target_role: str | None = None
    target_company: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    resume_url: str | None = None


class ProfileUpdate(ProfileBase):
    experiences: list[ExperienceBase] = Field(default_factory=list)


class Profile(ProfileBase):
    id: str
    email: str | None = None
    profile_photo: str | None = None
    auth_provider: str | None = None
    onboarding_completed: bool = False
    # AI-derived, read-only from the client's perspective — never accepted on
    # ProfileUpdate, only ever returned here.
    profile_score: int = 0
    ai_profile_summary: str | None = None
    experiences: list[Experience] = Field(default_factory=list)


class ProfileStrength(BaseModel):
    """Deterministic completeness scoring (no LLM involved)."""

    score: int = Field(ge=0, le=100)
    completed_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)


class ProfileAnalysis(BaseModel):
    """LLM-generated qualitative analysis."""

    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    suggested_skills: list[str] = Field(default_factory=list)
    generated_at: str | None = None
