"""Full-behavior tests for `app.profile_analysis.services.analysis_service`
-- the orchestration layer behind `POST/GET /career-ai/profile-analysis`.

Follows the established convention from tests/test_recommendation_service.py:
`get_supabase` is monkeypatched to a no-op sentinel (the real client raises
`AppError` when SUPABASE_URL is unset, the default test-environment state --
see app/db/supabase.py), so this file never touches Supabase or the network.

Unlike RecommendationService (constructor-injected repository), every
service function here constructs `ProfileAnalysisRepository(client)` INLINE,
so the test seam has to be at the module level: both `get_supabase` and the
imported `ProfileAnalysisRepository` name are monkeypatched inside
`app.profile_analysis.services.analysis_service`'s own namespace. Because a
fresh fake instance is constructed on every service call (matching real
production wiring exactly), the fake's actual state lives in a plain dict
("store") shared by every instance a given test creates, not on the
instance itself.

The real `MockAnalysisGenerator` (app/profile_analysis/services/generators/
mock_generator.py) runs unmocked in every test here -- it's deterministic,
dependency-free, and is exactly what runs in this same test environment in
production (get_analysis_generator() only switches to the LLM generator
when OPENAI_API_KEY is set, which it never is here). Faking it too would
mean testing against content this suite invented rather than the real
generator's real output.
"""

from datetime import UTC, datetime

import pytest

from app.core.exceptions import NotFoundError
from app.profile_analysis.services import analysis_service as service_module
from app.profile_analysis.services.generators.mock_generator import MockAnalysisGenerator

_MODULE = "app.profile_analysis.services.analysis_service"


def _profile(**overrides) -> dict:
    profile = {
        "id": "user-1",
        "full_name": "Riya Sharma",
        "headline": "CS student",
        "bio": "Building things and learning as I go.",
        "city": "Pune",
        "country": "India",
        "education_level": "Undergraduate",
        "degree": "B.Tech",
        "major": "Computer Science",
        "branch": None,
        "college_name": "Example Institute of Technology",
        "graduation_year": 2027,
        "graduation_status": "in_progress",
        "target_role": "Software Engineer",
        "target_company": None,
        "career_interests": ["Backend", "Machine Learning"],
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


def _make_fake_repository_class(store: dict):
    """Returns a fresh FakeProfileAnalysisRepository class bound to `store`.

    Duck-types the real repository's public method signatures (see
    app/profile_analysis/services/repository.py) exactly, including its
    NotFoundError-on-missing-profile behavior.
    """

    class FakeProfileAnalysisRepository:
        def __init__(self, client):
            self._client = client

        def get_profile(self, profile_id: str) -> dict:
            profile = store["profiles"].get(profile_id)
            if profile is None:
                raise NotFoundError("Complete your profile before running Profile Analysis.")
            return profile

        def get_experiences(self, profile_id: str) -> list[dict]:
            return list(store["experiences"].get(profile_id, []))

        def get_latest_analysis(self, profile_id: str) -> dict | None:
            rows = store["analyses"].get(profile_id, [])
            return rows[-1] if rows else None

        def list_score_history(self, profile_id: str, limit: int = 24) -> list[dict]:
            rows = store["analyses"].get(profile_id, [])
            return list(rows[:limit])

        def next_version(self, profile_id: str) -> int:
            latest = self.get_latest_analysis(profile_id)
            if latest is None:
                return 1
            return (latest.get("analysis_version") or 1) + 1

        def save_analysis(self, row: dict) -> dict:
            saved_rows = store["analyses"].setdefault(row["profile_id"], [])
            saved = {
                **row,
                "id": f"analysis-{len(saved_rows) + 1}",
                "created_at": datetime.now(UTC).isoformat(),
            }
            saved_rows.append(saved)
            return saved

    return FakeProfileAnalysisRepository


def _wire(monkeypatch, store: dict):
    monkeypatch.setattr(f"{_MODULE}.get_supabase", lambda access_token=None: object())
    monkeypatch.setattr(f"{_MODULE}.ProfileAnalysisRepository", _make_fake_repository_class(store))
    # Force the deterministic mock generator regardless of the real
    # OPENAI_API_KEY a developer's own .env may have set (get_analysis_
    # generator() is @lru_cache'd on settings.OPENAI_API_KEY, and a real key
    # would otherwise make this suite make genuine network calls to OpenAI --
    # slow, non-deterministic, and a real cost/leak risk in CI). Patching the
    # factory function itself (not settings) sidesteps the cache entirely.
    monkeypatch.setattr(f"{_MODULE}.get_analysis_generator", lambda: MockAnalysisGenerator())


def _new_store() -> dict:
    return {"profiles": {}, "experiences": {}, "analyses": {}}


# ---------------------------------------------------------------------------
# run_profile_analysis
# ---------------------------------------------------------------------------


async def test_run_profile_analysis_happy_path_produces_a_full_response(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]

    response = await service_module.run_profile_analysis(user_id="user-1", access_token="token")

    assert response.profile_id == "user-1"
    assert response.ai_model == "mock-v1"
    assert response.analysis_version == 1
    assert 0 <= response.overall_score <= 100
    assert response.profile_diagnosis.summary
    assert len(response.career_signals) == 6  # fixed vocabulary, always all 6
    assert response.score_breakdown.final_score == response.overall_score
    # Persisted as a new row, not merely returned.
    assert len(store["analyses"]["user-1"]) == 1


async def test_run_profile_analysis_raises_not_found_for_a_missing_profile(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    # No profile registered for "user-1" at all.

    with pytest.raises(NotFoundError):
        await service_module.run_profile_analysis(user_id="user-1", access_token="token")


async def test_run_profile_analysis_never_reads_another_users_data(monkeypatch):
    # There are no id-parameterized routes in this feature at all (see
    # app/profile_analysis/routers/analysis_router.py) -- the only
    # "ownership" surface is that `user_id` always comes from the verified
    # JWT, never client input, so a cross-user read is not even expressible.
    # This test pins that invariant at the service layer: passing a
    # different user_id must never surface user-1's data.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1", full_name="User One")
    store["profiles"]["user-2"] = _profile(id="user-2", full_name="User Two")

    response = await service_module.run_profile_analysis(user_id="user-2", access_token="token")

    assert response.profile_id == "user-2"
    assert "User One" not in response.profile_diagnosis.summary


async def test_run_profile_analysis_each_run_is_a_new_append_only_row(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]

    first = await service_module.run_profile_analysis(user_id="user-1", access_token="token")
    second = await service_module.run_profile_analysis(user_id="user-1", access_token="token")

    assert first.analysis_version == 1
    assert second.analysis_version == 2
    assert first.id != second.id
    # Both rows still exist -- second run never overwrote/deleted the first.
    assert len(store["analyses"]["user-1"]) == 2


# ---------------------------------------------------------------------------
# get_latest_profile_analysis
# ---------------------------------------------------------------------------


async def test_get_latest_profile_analysis_returns_the_most_recent_run(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]
    await service_module.run_profile_analysis(user_id="user-1", access_token="token")
    second = await service_module.run_profile_analysis(user_id="user-1", access_token="token")

    latest = await service_module.get_latest_profile_analysis(
        user_id="user-1", access_token="token"
    )

    assert latest.id == second.id
    assert latest.analysis_version == 2


async def test_get_latest_profile_analysis_raises_not_found_when_never_run(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    with pytest.raises(NotFoundError, match="No profile analysis"):
        await service_module.get_latest_profile_analysis(user_id="user-1", access_token="token")


async def test_get_latest_profile_analysis_treats_a_stale_row_shape_as_not_found(monkeypatch):
    # A row saved under an older section shape (missing fields the current
    # ProfileAnalysisResponse requires, e.g. profile_diagnosis/score_breakdown)
    # must fail pydantic validation and be reported the same as "never run",
    # per analysis_service.py's explicit ValidationError->NotFoundError catch
    # -- never surfaced as a raw 500.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["analyses"]["user-1"] = [
        {
            "id": "old-1",
            "profile_id": "user-1",
            "ai_model": "career-dna-v0",
            "analysis_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "overall_score": 40,
            # Deliberately missing profile_diagnosis, score_breakdown,
            # growth_simulation, highest_roi_recommendation -- the old shape.
        }
    ]

    with pytest.raises(NotFoundError, match="older version"):
        await service_module.get_latest_profile_analysis(user_id="user-1", access_token="token")


async def test_get_latest_profile_analysis_does_not_swallow_unrelated_errors(monkeypatch):
    # The ValidationError->NotFoundError catch must stay narrow: anything
    # that isn't a pydantic ValidationError (e.g. a genuine bug in the
    # repository) has to propagate, not get silently reported as "not found".
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    class BoomRepository:
        def __init__(self, client):
            pass

        def get_latest_analysis(self, profile_id):
            raise RuntimeError("simulated unrelated backend failure")

    monkeypatch.setattr(f"{_MODULE}.ProfileAnalysisRepository", BoomRepository)

    with pytest.raises(RuntimeError, match="simulated unrelated backend failure"):
        await service_module.get_latest_profile_analysis(user_id="user-1", access_token="token")


# ---------------------------------------------------------------------------
# get_profile_analysis_history
# ---------------------------------------------------------------------------


async def test_get_profile_analysis_history_returns_populated_points(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    store["experiences"]["user-1"] = [_experience()]
    await service_module.run_profile_analysis(user_id="user-1", access_token="token")
    await service_module.run_profile_analysis(user_id="user-1", access_token="token")

    history = await service_module.get_profile_analysis_history(
        user_id="user-1", access_token="token"
    )

    assert len(history) == 2
    assert all(hasattr(point, "overall_score") for point in history)


async def test_get_profile_analysis_history_returns_empty_list_not_an_error(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    # No analyses run at all.

    history = await service_module.get_profile_analysis_history(
        user_id="user-1", access_token="token"
    )

    assert history == []
