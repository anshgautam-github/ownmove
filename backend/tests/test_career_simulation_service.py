"""Full-behavior tests for `app.career_simulation.services.simulation_service`
-- the orchestration layer behind `POST /career-ai/simulations`,
`POST /career-ai/simulations/compare`, and the id-parameterized routes.

Same convention as the other Career AI service test files: `get_supabase`
and the module's imported `CareerSimulationRepository` are monkeypatched to
a fake bound to a shared "store" dict. The real `MockSimulationGenerator`
runs unmocked.

This is the first of the four modules with real id-parameterized routes
(GET/DELETE /career-simulation/{id}), and the repository implements
explicit app-layer IDOR defense-in-depth: every id-scoped query filters on
BOTH `id` AND `profile_id`, deliberately never relying on RLS alone (see
repository.py's own docstrings). The IDOR tests below pin exactly that.
"""

import pytest

from app.career_simulation.schemas.simulation import (
    SimulationCompareRequest,
    SimulationCreateRequest,
    SimulationOption,
)
from app.career_simulation.services import simulation_service as service_module
from app.career_simulation.services.generators.mock_generator import MockSimulationGenerator
from app.core.exceptions import NotFoundError

_MODULE = "app.career_simulation.services.simulation_service"


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
        "current_skills": ["Python", "SQL"],
        "github_url": None,
        "resume_url": None,
        "linkedin_url": None,
        "ai_profile_summary": None,
    }
    profile.update(overrides)
    return profile


def _create_request(**overrides) -> SimulationCreateRequest:
    payload = {
        "simulation_type": "learn_skill",
        "target_role": "Backend Engineer",
        "scenario_title": "Learn Kubernetes",
        "scenario_input": {"skill": "Kubernetes", "depth": "intermediate"},
    }
    payload.update(overrides)
    return SimulationCreateRequest(**payload)


def _compare_request(**overrides) -> SimulationCompareRequest:
    payload = {
        "target_role": "Backend Engineer",
        "option_a": SimulationOption(
            simulation_type="learn_skill",
            scenario_title="Learn Kubernetes",
            scenario_input={"skill": "Kubernetes"},
        ),
        "option_b": SimulationOption(
            simulation_type="certification",
            scenario_title="AWS Certification",
            scenario_input={"certification_name": "AWS Solutions Architect"},
        ),
    }
    payload.update(overrides)
    return SimulationCompareRequest(**payload)


def _make_fake_repository_class(store: dict):
    class FakeCareerSimulationRepository:
        def __init__(self, client):
            self._client = client

        def get_profile(self, profile_id: str) -> dict:
            profile = store["profiles"].get(profile_id)
            if profile is None:
                raise NotFoundError("Complete your profile before running a Career Simulation.")
            return profile

        def get_experiences(self, profile_id: str) -> list[dict]:
            return list(store["experiences"].get(profile_id, []))

        def get_latest_profile_analysis(self, profile_id: str) -> dict | None:
            return store["latest_analysis"].get(profile_id)

        def create_pending(self, row: dict) -> dict:
            sim_id = f"sim-{len(store['simulations']) + 1}"
            saved = {
                **row,
                "id": sim_id,
                "status": "pending",
                "result": None,
                "verdict": None,
                "model_used": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "completed_at": None,
            }
            store["simulations"][sim_id] = saved
            return saved

        def complete(self, simulation_id: str, profile_id: str, update: dict) -> dict:
            row = store["simulations"].get(simulation_id)
            if row is None or row["profile_id"] != profile_id:
                raise NotFoundError("simulation not found for this profile")  # pragma: no cover
            row.update(update)
            return row

        def mark_failed(self, simulation_id: str, profile_id: str) -> None:
            row = store["simulations"].get(simulation_id)
            if row is not None and row["profile_id"] == profile_id:
                row["status"] = "failed"

        def get_by_id(self, simulation_id: str, profile_id: str) -> dict | None:
            row = store["simulations"].get(simulation_id)
            if row is None or row["profile_id"] != profile_id:
                # Mirrors the real repository's .eq("id", ...).eq("profile_id", ...)
                # double filter: a row that exists but belongs to someone else
                # comes back as None, indistinguishable from not existing at all.
                return None
            return row

        def list_recent(self, profile_id: str, limit: int = 20) -> list[dict]:
            rows = [r for r in store["simulations"].values() if r["profile_id"] == profile_id]
            rows.sort(key=lambda r: r["id"], reverse=True)
            return [
                {
                    "id": r["id"],
                    "simulation_type": r["simulation_type"],
                    "target_role": r["target_role"],
                    "scenario_title": r["scenario_title"],
                    "verdict": r["verdict"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in rows[:limit]
            ]

        def delete_simulation(self, simulation_id: str, profile_id: str) -> None:
            row = store["simulations"].get(simulation_id)
            if row is not None and row["profile_id"] == profile_id:
                del store["simulations"][simulation_id]
            # Same double-filter defense as the real repository: a delete for
            # a simulation_id that exists but belongs to someone else is a
            # silent no-op, never an error and never a cross-user delete.

    return FakeCareerSimulationRepository


def _wire(monkeypatch, store: dict):
    monkeypatch.setattr(f"{_MODULE}.get_supabase", lambda access_token=None: object())
    monkeypatch.setattr(f"{_MODULE}.CareerSimulationRepository", _make_fake_repository_class(store))
    # Force the deterministic mock generator regardless of a real
    # OPENAI_API_KEY in the developer's own .env -- see the matching comment
    # in tests/test_profile_analysis_service.py._wire for why patching the
    # factory function (not settings) is required here.
    monkeypatch.setattr(f"{_MODULE}.get_simulation_generator", lambda: MockSimulationGenerator())


def _new_store() -> dict:
    return {"profiles": {}, "experiences": {}, "latest_analysis": {}, "simulations": {}}


# ---------------------------------------------------------------------------
# create_simulation
# ---------------------------------------------------------------------------


async def test_create_simulation_happy_path_completes_and_persists(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    response = await service_module.create_simulation(
        user_id="user-1", access_token="token", request=_create_request()
    )

    assert response.profile_id == "user-1"
    assert response.status == "completed"
    assert response.model_used == "mock-v1"
    assert response.result is not None
    assert response.verdict in {"high_value", "useful", "limited_value", "low_value"}
    assert store["simulations"][response.id]["status"] == "completed"


async def test_create_simulation_raises_not_found_for_a_missing_profile(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)

    with pytest.raises(NotFoundError):
        await service_module.create_simulation(
            user_id="user-1", access_token="token", request=_create_request()
        )


async def test_create_simulation_marks_failed_and_reraises_on_generator_failure(monkeypatch):
    # Two-phase write: a pending row must move to 'failed' (not just vanish
    # or stay stuck pending) when the generator itself blows up, and the
    # original exception must still propagate to the caller/global handler.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    class BoomGenerator:
        name = "mock-v1"

        async def generate(self, context):
            raise RuntimeError("simulated generator failure")

    monkeypatch.setattr(f"{_MODULE}.get_simulation_generator", lambda: BoomGenerator())

    with pytest.raises(RuntimeError, match="simulated generator failure"):
        await service_module.create_simulation(
            user_id="user-1", access_token="token", request=_create_request()
        )

    [saved] = store["simulations"].values()
    assert saved["status"] == "failed"


# ---------------------------------------------------------------------------
# compare_simulations
# ---------------------------------------------------------------------------


async def test_compare_simulations_happy_path(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    response = await service_module.compare_simulations(
        user_id="user-1", access_token="token", request=_compare_request()
    )

    assert response.simulation_type == "compare_moves"
    assert response.verdict is None  # never a single headline verdict for a comparison
    assert response.result["comparison"]["better_fit"] in {"option_a", "option_b"}
    assert response.result["option_a"] and response.result["option_b"]


async def test_compare_simulations_scenario_title_combines_both_options(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    response = await service_module.compare_simulations(
        user_id="user-1", access_token="token", request=_compare_request()
    )

    assert response.scenario_title == "Learn Kubernetes vs. AWS Certification"


# ---------------------------------------------------------------------------
# get_simulation -- IDOR
# ---------------------------------------------------------------------------


async def test_get_simulation_returns_the_owners_own_simulation(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    created = await service_module.create_simulation(
        user_id="user-1", access_token="token", request=_create_request()
    )

    fetched = await service_module.get_simulation(
        user_id="user-1", access_token="token", simulation_id=created.id
    )

    assert fetched.id == created.id


async def test_get_simulation_raises_not_found_for_a_nonexistent_id(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)

    with pytest.raises(NotFoundError):
        await service_module.get_simulation(
            user_id="user-1", access_token="token", simulation_id="does-not-exist"
        )


async def test_get_simulation_raises_not_found_not_forbidden_for_anothers(monkeypatch):
    # IDOR defense-in-depth: a simulation that genuinely exists but belongs
    # to a different profile_id must come back as NotFoundError, exactly the
    # same as a nonexistent id -- never confirming to the caller that the id
    # exists at all, and never a 403.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    victim_sim = await service_module.create_simulation(
        user_id="user-1", access_token="token", request=_create_request()
    )

    with pytest.raises(NotFoundError):
        await service_module.get_simulation(
            user_id="user-2", access_token="token", simulation_id=victim_sim.id
        )


# ---------------------------------------------------------------------------
# list_recent_simulations
# ---------------------------------------------------------------------------


async def test_list_recent_simulations_returns_empty_list_not_an_error(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    history = await service_module.list_recent_simulations(user_id="user-1", access_token="token")

    assert history == []


async def test_list_recent_simulations_only_returns_the_callers_own(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    await service_module.create_simulation(
        user_id="user-1", access_token="token", request=_create_request()
    )
    await service_module.create_simulation(
        user_id="user-2", access_token="token", request=_create_request()
    )

    history = await service_module.list_recent_simulations(user_id="user-1", access_token="token")

    assert len(history) == 1


# ---------------------------------------------------------------------------
# delete_simulation -- IDOR
# ---------------------------------------------------------------------------


async def test_delete_simulation_removes_the_owners_own_simulation(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    created = await service_module.create_simulation(
        user_id="user-1", access_token="token", request=_create_request()
    )

    await service_module.delete_simulation(
        user_id="user-1", access_token="token", simulation_id=created.id
    )

    assert created.id not in store["simulations"]


async def test_delete_simulation_does_not_delete_another_users_simulation(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    victim_sim = await service_module.create_simulation(
        user_id="user-1", access_token="token", request=_create_request()
    )

    # Attacker (user-2) attempts to delete user-1's simulation by id.
    await service_module.delete_simulation(
        user_id="user-2", access_token="token", simulation_id=victim_sim.id
    )

    assert victim_sim.id in store["simulations"]  # untouched
