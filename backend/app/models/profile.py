"""public.profiles and public.experiences."""

from datetime import date, datetime

from app.models.base import DBModel, TimestampedModel


class ExperienceRow(DBModel):
    id: str | None = None
    profile_id: str
    title: str | None = None
    company: str | None = None
    experience_type: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    currently_working: bool = False
    description: str | None = None
    # Skills exercised in this specific role — finer-grained than
    # ProfileRow.current_skills, which is unscoped across the whole history.
    skills_used: list[str] = []


class ProfileRow(TimestampedModel):
    # Primary key is auth.users.id — one profile per Supabase user.
    id: str

    # identity
    full_name: str | None = None
    email: str | None = None
    profile_photo: str | None = None
    headline: str | None = None
    bio: str | None = None
    city: str | None = None
    country: str | None = None

    # education
    college_name: str | None = None
    education_level: str | None = None
    degree: str | None = None
    branch: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    graduation_status: str | None = None

    # career signal
    career_interests: list[str] = []
    current_skills: list[str] = []
    target_role: str | None = None
    target_company: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    resume_url: str | None = None

    # AI-derived — written by the backend's analysis job only
    profile_score: int = 0
    ai_profile_summary: str | None = None
    last_profile_analysis: datetime | None = None

    # bookkeeping
    auth_provider: str | None = None
    onboarding_completed: bool = False
    submitted_at: datetime | None = None
