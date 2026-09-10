"""Full-behavior tests for `app.career_roadmap.services.roadmap_service` --
the orchestration layer behind `POST/GET /career-ai/roadmap`.

Same convention as tests/test_profile_analysis_service.py: `get_supabase`
and the module's imported `CareerRoadmapRepository` are monkeypatched to a
fake bound to a plain dict ("store") shared across every fake instance a
test creates (the real service constructs a fresh repository inline on
every call, same as production). The real `MockRoadmapGenerator` runs
unmocked -- deterministic, no network, exactly what this test environment
uses in production (OPENAI_API_KEY is unset).
"""

from datetime import UTC, datetime

import pytest

from app.career_roadmap.schemas.roadmap import RoadmapGenerateRequest
from app.career_roadmap.services import roadmap_service as service_module
from app.career_roadmap.services.generators.mock_generator import MockRoadmapGenerator
from app.core.exceptions import NotFoundError

_MODULE = "app.career_roadmap.services.roadmap_service"


def _profile(**overrides) -> dict:
    profile = {
        "id": "user-1",
        "full_name": "Riya Sharma",
        "headline": "CS student",
        "bio": "Building things and learning as I go.",
        "education_level": "Undergraduate",
        "degree": "B.Tech",
        "major": "Computer Science",
        "branch": None,
        "college_name": "Example Institute of Technology",
        "graduation_year": 2027,
        "graduation_status": "in_progress",
        "target_role": "Backend Engineer",
        "target_company": None,
        "career_interests": ["Backend"],
        "current_skills": ["Python", "SQL", "Git"],
        "github_url": "https://github.com/example",
        "resume_url": "https://example.com/resume.pdf",
        "linkedin_url": "https://linkedin.com/in/example",
        "ai_profile_summary": None,
    }
    profile.update(overrides)
    return profile


def _experience(**overrides) -> dict:
    experience = {
        "id": "exp-1",
        "profile_id": "user-1",
        "title": "Backend Intern",
        "company": "Acme Corp",
        "experience_type": "internship",
        "description": "Built REST APIs and wrote tests.",
        "skills_used": ["Python", "SQL"],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    experience.update(overrides)
    return experience


def _request(**overrides) -> RoadmapGenerateRequest:
    payload = {
        "target_role": "Backend Engineer",
        "timeline_months": 3,
        "weekly_commitment": 10,
        "primary_goal": "Get an Internship",
    }
    payload.update(overrides)
    return RoadmapGenerateRequest(**payload)


def _make_fake_repository_class(store: dict):
    class FakeCareerRoadmapRepository:
        def __init__(self, client):
            self._client = client

        def get_profile(self, user_id: str) -> dict:
            profile = store["profiles"].get(user_id)
            if profile is None:
                raise NotFoundError("Complete your profile before generating a Career Roadmap.")
            return profile

        def get_experiences(self, user_id: str) -> list[dict]:
            return list(store["experiences"].get(user_id, []))

        def get_latest_profile_analysis(self, user_id: str) -> dict | None:
            return store["latest_analysis"].get(user_id)

        def get_roadmap(self, user_id: str) -> dict | None:
            return store["roadmaps"].get(user_id)

        def save_roadmap(self, row: dict) -> dict:
            existing = store["roadmaps"].get(row["user_id"])
            now = datetime.now(UTC).isoformat()
            saved = {
                **row,
                "id": existing["id"] if existing else f"roadmap-{len(store['roadmaps']) + 1}",
                "generated_at": existing["generated_at"] if existing else now,
                "updated_at": now,
            }
            store["roadmaps"][row["user_id"]] = saved
            return saved

        def log_activity(self, *, roadmap_id, user_id, activity_type, description) -> None:
            store["activity"].append(
                {
                    "roadmap_id": roadmap_id,
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "description": description,
                }
            )

    return FakeCareerRoadmapRepository


def _wire(monkeypatch, store: dict):
    monkeypatch.setattr(f"{_MODULE}.get_supabase", lambda access_token=None: object())
    monkeypatch.setattr(f"{_MODULE}.CareerRoadmapRepository", _make_fake_repository_class(store))
    # Force the deterministic mock generator regardless of a real
    # OPENAI_API_KEY in the developer's own .env -- see the matching comment
    # in tests/test_profile_analysis_service.py._wire for why patching the
    # factory function (not settings) is required here.
    monkeypatch.setattr(f"{_MODULE}.get_roadmap_generator", lambda: MockRoadmapGenerator())


def _new_store() -> dict:
    return {
        "profiles": {},
        "experiences": {},
        "latest_analysis": {},
        "roadmaps": {},
        "activity": [],
    }


# ---------------------------------------------------------------------------
# generate_roadmap
# ---------------------------------------------------------------------------


async def test_generate_roadmap_happy_path_produces_a_full_response(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]

    response = await service_module.generate_roadmap(
        user_id="user-1", access_token="token", request=_request()
    )

    assert response.user_id == "user-1"
    assert response.target_role == "Backend Engineer"
    assert response.timeline_months == 3
    assert response.weekly_commitment == 10
    assert response.primary_goal == "Get an Internship"
    assert response.llm_model == "mock-v1"
    assert response.phases  # a real curriculum was produced
    # First-ever generation logs "generated", not "regenerated".
    assert store["activity"][-1]["activity_type"] == "generated"


async def test_generate_roadmap_raises_not_found_for_a_missing_profile(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)

    with pytest.raises(NotFoundError):
        await service_module.generate_roadmap(
            user_id="user-1", access_token="token", request=_request()
        )


async def test_generate_roadmap_regenerate_upserts_the_same_row(monkeypatch):
    # career_roadmaps has unique(user_id) -- a second Generate call for the
    # same user must overwrite the existing row (same id, same generated_at),
    # never insert a second one, unlike profile_analysis's append-only history.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]

    first = await service_module.generate_roadmap(
        user_id="user-1", access_token="token", request=_request()
    )
    second = await service_module.generate_roadmap(
        user_id="user-1",
        access_token="token",
        request=_request(timeline_months=6, weekly_commitment=20),
    )

    assert second.id == first.id
    assert second.generated_at == first.generated_at  # original generation time preserved
    assert second.timeline_months == 6
    assert len(store["roadmaps"]) == 1  # still exactly one row for this user
    assert store["activity"][-1]["activity_type"] == "regenerated"


async def test_generate_roadmap_dict_update_lets_db_columns_win_over_roadmap_json(monkeypatch):
    # _to_response() merges roadmap_json UNDER the DB row's own columns via
    # dict.update -- the DB's timeline_months/weekly_commitment/primary_goal
    # are authoritative even if a stale generator payload somehow disagreed.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]

    response = await service_module.generate_roadmap(
        user_id="user-1", access_token="token", request=_request(weekly_commitment=15)
    )

    saved_row = store["roadmaps"]["user-1"]
    assert saved_row["roadmap_json"].get("weekly_commitment") is None  # generator never sets this
    assert response.weekly_commitment == 15  # yet the response has the real, requested value


async def test_generate_roadmap_uses_latest_profile_analysis_when_available(monkeypatch):
    # Not required to exist (None is a normal state -- "no analysis has ever
    # been run"), but when present it must actually reach the generator/
    # context rather than being silently ignored.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]
    store["latest_analysis"]["user-1"] = {
        "overall_score": 62,
        "profile_diagnosis": {
            "strongest_signal": "Software Engineering Foundation",
            "limiting_factor": "No Portfolio",
        },
        "missing_signals": [{"title": "No Portfolio"}],
        "career_signals": [],
        "recruiter_signals": [],
    }

    response = await service_module.generate_roadmap(
        user_id="user-1", access_token="token", request=_request()
    )

    assert response.phases  # generation succeeded with the analysis present too


# ---------------------------------------------------------------------------
# get_current_roadmap
# ---------------------------------------------------------------------------


async def test_get_current_roadmap_returns_the_saved_roadmap(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]
    generated = await service_module.generate_roadmap(
        user_id="user-1", access_token="token", request=_request()
    )

    current = await service_module.get_current_roadmap(user_id="user-1", access_token="token")

    assert current.id == generated.id
    assert current.target_role == generated.target_role


async def test_get_current_roadmap_raises_not_found_when_never_generated(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)

    with pytest.raises(NotFoundError, match="No career roadmap"):
        await service_module.get_current_roadmap(user_id="user-1", access_token="token")


async def test_get_current_roadmap_treats_a_stale_row_shape_as_not_found(monkeypatch):
    # A row saved before the roadmap schema deepened (missing
    # industry_landscape/starting_point/phases as currently shaped) fails
    # validation and must be reported the same as "no roadmap yet", per
    # roadmap_service.py's explicit ValidationError->NotFoundError catch.
    store = _new_store()
    _wire(monkeypatch, store)
    now = datetime.now(UTC).isoformat()
    store["roadmaps"]["user-1"] = {
        "id": "old-roadmap-1",
        "user_id": "user-1",
        "timeline_months": 3,
        "weekly_commitment": 10,
        "primary_goal": "Get an Internship",
        "llm_model": "career-roadmap-v0",
        "generated_at": now,
        "updated_at": now,
        "roadmap_json": {"title": "Old shape roadmap"},  # missing required fields
    }

    with pytest.raises(NotFoundError, match="regenerated"):
        await service_module.get_current_roadmap(user_id="user-1", access_token="token")
