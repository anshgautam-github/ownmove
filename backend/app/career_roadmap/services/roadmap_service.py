"""Orchestration only — no FastAPI imports, mirrors
`app.profile_analysis.services.analysis_service` in shape: load -> generate
-> persist -> return. Read this file first to understand the whole feature.
"""

from pydantic import ValidationError

from app.career_roadmap.schemas.roadmap import CareerRoadmapResponse, RoadmapGenerateRequest
from app.career_roadmap.services.generators.factory import get_roadmap_generator
from app.career_roadmap.services.repository import CareerRoadmapRepository
from app.career_roadmap.utils.context import RoadmapContext
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.supabase import get_supabase

logger = get_logger(__name__)


def _to_response(row: dict) -> CareerRoadmapResponse:
    """A `career_roadmaps` row has the setup answers and persistence
    metadata as top-level columns and the generated content in one
    `roadmap_json` blob — merge both into the one wire shape the frontend
    renders. The DB row's own columns (id/user_id/timeline_months/
    weekly_commitment/primary_goal/llm_model/generated_at/updated_at) are
    authoritative and always win on overlap — `dict.update` rather than
    passing both as separate kwargs, so this can never raise a
    duplicate-keyword TypeError no matter what keys a generator's
    `roadmap_json` happens to contain."""
    content = dict(row.get("roadmap_json") or {})
    content.update(
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "timeline_months": row["timeline_months"],
            "weekly_commitment": row["weekly_commitment"],
            "primary_goal": row["primary_goal"],
            "llm_model": row.get("llm_model"),
            "generated_at": row["generated_at"],
            "updated_at": row["updated_at"],
        }
    )
    return CareerRoadmapResponse(**content)


async def generate_roadmap(
    *, user_id: str, access_token: str, request: RoadmapGenerateRequest
) -> CareerRoadmapResponse:
    """Generate a roadmap (first time) or regenerate it (overwriting the
    existing one) for the authenticated user. `career_roadmaps` has
    `unique(user_id)` — this always upserts the user's single row rather
    than inserting new history, unlike profile_analysis.
    """
    client = get_supabase(access_token=access_token)
    repository = CareerRoadmapRepository(client)

    profile = repository.get_profile(user_id)
    experiences = repository.get_experiences(user_id)
    latest_analysis = repository.get_latest_profile_analysis(user_id)
    existing = repository.get_roadmap(user_id)

    context = RoadmapContext(
        profile=profile,
        experiences=experiences,
        latest_analysis=latest_analysis,
        target_role=request.target_role,
        timeline_months=request.timeline_months,
        weekly_commitment=request.weekly_commitment,
        primary_goal=request.primary_goal,
    )

    generator = get_roadmap_generator()
    content = await generator.generate(context)

    row = {
        "user_id": user_id,
        "target_role": request.target_role,
        "timeline_months": request.timeline_months,
        "weekly_commitment": request.weekly_commitment,
        "primary_goal": request.primary_goal,
        "roadmap_json": content.model_dump(mode="json"),
        "llm_model": generator.name,
    }
    saved = repository.save_roadmap(row)

    repository.log_activity(
        roadmap_id=saved["id"],
        user_id=user_id,
        activity_type="regenerated" if existing else "generated",
        description=(
            f"{'Regenerated' if existing else 'Generated'} roadmap for {request.target_role} "
            f"({request.timeline_months} months, {request.weekly_commitment} hrs/week, "
            f"goal: {request.primary_goal})"
        ),
    )

    return _to_response(saved)


async def get_current_roadmap(*, user_id: str, access_token: str) -> CareerRoadmapResponse:
    """Fetch the user's single active roadmap without generating anything.
    404s (NotFoundError -> `not_found`) if none exists yet — the frontend
    renders that as the setup screen, not an error state.
    """
    client = get_supabase(access_token=access_token)
    repository = CareerRoadmapRepository(client)

    row = repository.get_roadmap(user_id)
    if row is None:
        raise NotFoundError("No career roadmap has been generated yet.")

    try:
        return _to_response(row)
    except ValidationError:
        # A row generated before the roadmap schema was deepened (no
        # `starting_point`, per-phase `objectives`, etc.) won't validate
        # against the current `RoadmapContent` shape. Treat that the same
        # way as "no roadmap yet" — the frontend falls back to the setup
        # screen and a fresh Generate Roadmap produces a row in the current
        # shape — rather than 500ing on an old row the user can't act on.
        logger.warning("career_roadmap.stale_shape", extra={"user_id": user_id, "roadmap_id": row.get("id")})
        raise NotFoundError("Your roadmap needs to be regenerated to view it with the latest format.") from None
