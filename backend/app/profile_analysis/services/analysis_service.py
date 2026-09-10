"""Orchestration only — no FastAPI imports (importable from a script or a
future background worker unchanged), no business logic of its own beyond
sequencing. Every branch here is meant to be readable top to bottom:
load -> generate -> persist -> return. Read this file first to understand
the whole feature; everything it calls out to has its own narrower docstring.
"""

from pydantic import ValidationError

from app.core.exceptions import NotFoundError
from app.db.supabase import get_supabase
from app.profile_analysis.schemas.analysis import ProfileAnalysisResponse, ScoreHistoryPoint
from app.profile_analysis.services.generators.factory import get_analysis_generator
from app.profile_analysis.services.repository import ProfileAnalysisRepository
from app.profile_analysis.utils.context import ProfileContext


async def run_profile_analysis(*, user_id: str, access_token: str) -> ProfileAnalysisResponse:
    """Generate a brand-new analysis, persist it, and return it.

    This is what `POST /career-ai/profile-analysis` calls. Every invocation
    inserts a new row rather than overwriting the last one — see
    `supabase/schema/012_profile_analysis.sql` for why this table is
    append-only history, same as `profile_insights`.
    """
    client = get_supabase(access_token=access_token)
    repository = ProfileAnalysisRepository(client)

    profile = repository.get_profile(user_id)
    experiences = repository.get_experiences(user_id)
    context = ProfileContext(profile=profile, experiences=experiences)

    generator = get_analysis_generator()
    content = await generator.generate(context)

    row = {
        "profile_id": user_id,
        # profile_diagnosis/score_breakdown/growth_simulation/
        # highest_roi_recommendation are nested pydantic models;
        # career_signals/missing_signals/profile_contradictions/
        # recruiter_signals are lists of them. mode="json" turns all of it
        # into plain dicts/lists/primitives, which is what the jsonb columns
        # and the Supabase client's JSON encoder expect.
        **content.model_dump(mode="json"),
        "ai_model": generator.name,
        "analysis_version": repository.next_version(user_id),
    }
    saved = repository.save_analysis(row)

    return ProfileAnalysisResponse(**saved)


async def get_latest_profile_analysis(*, user_id: str, access_token: str) -> ProfileAnalysisResponse:
    """Fetch the most recent analysis without generating a new one.

    Lets the dashboard show a previous result immediately on load instead of
    spending an LLM call every time the page opens — the frontend calls this
    first and only calls `run_profile_analysis` when the user explicitly
    asks to (re-)analyze.
    """
    client = get_supabase(access_token=access_token)
    repository = ProfileAnalysisRepository(client)

    latest = repository.get_latest_analysis(user_id)
    if latest is None:
        raise NotFoundError("No profile analysis has been generated yet.")

    try:
        return ProfileAnalysisResponse(**latest)
    except ValidationError as exc:
        # This feature's section shapes have changed a few times during
        # development (most recently: a full redesign from Career DNA/
        # Recruiter View/Evidence Score into Profile Diagnosis/Career
        # Signals/Evidence Credibility/Score Breakdown/Profile
        # Contradictions). A row saved under an older shape can no longer be
        # parsed into the current
        # response model — treating that the same as "nothing generated
        # yet" is the honest option: the old data can't be rendered
        # correctly anyway, and re-running produces a row in the current
        # shape. This should only ever fire against genuinely stale rows,
        # never silently swallow an unrelated bug — hence re-raising
        # anything that isn't a validation error.
        raise NotFoundError(
            "Your last analysis was generated under an older version of this feature. "
            "Run a new one to see the current report."
        ) from exc


async def get_profile_analysis_history(*, user_id: str, access_token: str) -> list[ScoreHistoryPoint]:
    """Every past analysis's headline score, oldest first — powers the
    Profile Timeline section of the dashboard. Returns an empty list (not a
    404) when there's no history yet; "not enough data to plot a trend" is a
    normal state for the frontend to render inline, not an error.
    """
    client = get_supabase(access_token=access_token)
    repository = ProfileAnalysisRepository(client)

    rows = repository.list_score_history(user_id)
    return [ScoreHistoryPoint(**row) for row in rows]
