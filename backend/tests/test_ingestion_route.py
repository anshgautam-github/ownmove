"""Route-level security and behavior for `app/api/v1/routes/ingestion.py` --
the production-readiness review's explicit ask: "verify missing configured
secret -> fail closed, wrong secret -> 401, correct secret -> request
proceeds, secret is never logged, ingestion endpoints aren't accidentally
exposed through another route."

Uses the real app (`client` fixture from `conftest.py`) rather than calling
`require_ingestion_admin_key()` in isolation, so these tests exercise the
actual HTTP-level wiring (`dependencies=[Depends(...)]` on each route) --
the same thing a real request against a deployed server would hit.
"""

import pytest

import app.api.v1.routes.ingestion as ingestion_route
from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.agents.registry import agent_registry
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.validation import ValidationResult
from app.ingestion.services.opportunity_service import OpportunityService
from app.ingestion.utils.validation import basic_field_checks, to_validation_result

_KEY_HEADER = "X-Ingestion-Admin-Key"
_SECRET = "test-ingestion-admin-secret-do-not-reuse"


class _RouteFakeAgent(BaseOpportunityAgent):
    """Registered/unregistered around exactly one test each -- discovers one
    fixed listing, no real network, so a route-level test can exercise
    `/ingestion/run/{source}` end-to-end without depending on Devpost or a
    real database."""

    source = "route-fake-source"

    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        return [DiscoveredListing(url="https://example.com/1", source=self.source)]

    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        return RawExtraction(
            url=listing.url, source=self.source, raw_content="title:Route Test Listing"
        )

    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        return NormalizedOpportunity(
            category="programs",
            title=raw.raw_content.split(":", 1)[1],
            apply_url=raw.url,
            source=self.source,
            source_id=raw.url,
        )

    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        return to_validation_result(basic_field_checks(opportunity))


class _NoWriteRepository:
    """A repository double whose write methods raise -- a dry-run route
    test asserts against a 200 AND against these never firing, so this
    fails loudly (rather than silently no-op-ing) if `preview_batch()` ever
    calls a write method by mistake."""

    def get_by_source_and_source_id(self, source: str, source_id: str) -> dict | None:
        return None

    def get_by_fingerprint(self, fingerprint: str) -> dict | None:
        return None

    def insert(self, row: dict) -> dict:
        raise AssertionError("dry run must never call insert()")

    def update(self, opportunity_id: str, row: dict) -> dict:
        raise AssertionError("dry run must never call update()")

    def set_enrichment_status(self, opportunity_id, *, status, queued_at=None):
        raise AssertionError("dry run must never queue enrichment")


class _RecordingRepository:
    """The real-run counterpart -- records what WAS written, so the
    non-dry-run test can confirm a write actually happened (the contrast
    that makes the dry-run guarantee meaningful)."""

    def __init__(self):
        self.inserted: list[dict] = []

    def get_by_source_and_source_id(self, source: str, source_id: str) -> dict | None:
        return None

    def get_by_fingerprint(self, fingerprint: str) -> dict | None:
        return None

    def insert(self, row: dict) -> dict:
        self.inserted.append(row)
        return {"id": "row-1", **row}

    def update(self, opportunity_id: str, row: dict) -> dict:
        raise ExternalServiceError("not exercised in this test")

    def set_enrichment_status(self, opportunity_id, *, status, queued_at=None):
        return {"id": opportunity_id, "enrichment_status": status}


class _FakeQueue:
    async def enqueue(self, task: str, /, **payload) -> str:
        return "fake-1"


@pytest.fixture(autouse=True)
def _reset_admin_key(monkeypatch):
    """Every test starts from a known state (unconfigured) -- individual
    tests opt into a configured secret via `monkeypatch.setattr(settings,
    "INGESTION_ADMIN_API_KEY", _SECRET)`."""
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", "")


# ---------------------------------------------------------------------------
# fail closed when unconfigured
# ---------------------------------------------------------------------------


def test_due_fails_closed_with_503_when_admin_key_is_unconfigured(client):
    response = client.get("/api/v1/ingestion/due", headers={_KEY_HEADER: "anything"})
    assert response.status_code == 503


def test_due_fails_closed_with_503_even_with_no_header_at_all(client):
    response = client.get("/api/v1/ingestion/due")
    assert response.status_code == 503


def test_run_source_fails_closed_with_503_when_admin_key_is_unconfigured(client):
    response = client.post("/api/v1/ingestion/run/devpost", headers={_KEY_HEADER: "anything"})
    assert response.status_code == 503


def test_run_due_fails_closed_with_503_when_admin_key_is_unconfigured(client):
    response = client.post("/api/v1/ingestion/run-due", headers={_KEY_HEADER: "anything"})
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# wrong secret -> 401
# ---------------------------------------------------------------------------


def test_due_rejects_wrong_secret_with_401(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)

    response = client.get("/api/v1/ingestion/due", headers={_KEY_HEADER: "wrong-secret"})

    assert response.status_code == 401


def test_due_rejects_missing_header_with_401_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)

    response = client.get("/api/v1/ingestion/due")

    assert response.status_code == 401


def test_due_rejects_empty_header_value_with_401(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)

    response = client.get("/api/v1/ingestion/due", headers={_KEY_HEADER: ""})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# correct secret -> request proceeds
# ---------------------------------------------------------------------------


def test_due_succeeds_with_the_correct_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)

    response = client.get("/api/v1/ingestion/due", headers={_KEY_HEADER: _SECRET})

    assert response.status_code == 200
    assert "due" in response.json()


# ---------------------------------------------------------------------------
# the secret itself is never echoed back in a response body
# ---------------------------------------------------------------------------


def test_secret_never_appears_in_any_response_body(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)

    responses = [
        client.get("/api/v1/ingestion/due"),  # 401, no header
        client.get("/api/v1/ingestion/due", headers={_KEY_HEADER: "wrong"}),  # 401
        client.get("/api/v1/ingestion/due", headers={_KEY_HEADER: _SECRET}),  # 200
    ]

    for response in responses:
        assert _SECRET not in response.text


# ---------------------------------------------------------------------------
# not accidentally exposed through another route
# ---------------------------------------------------------------------------


def test_the_separate_unimplemented_opportunities_router_does_not_require_the_admin_key(client):
    # api/v1/routes/opportunities.py is a distinct, still-unimplemented
    # router (see that module) -- confirms the ingestion admin-key
    # dependency was not accidentally applied there (or anywhere else) via
    # some shared dependency default, only on the three /ingestion/* routes.
    response = client.get("/api/v1/opportunities")
    assert response.status_code != 503  # i.e. NOT "admin key not configured"


def test_ingestion_admin_key_dependency_is_only_declared_on_the_ingestion_router(client):
    spec = client.app.openapi()
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            header_names = {
                param["name"].lower()
                for param in operation.get("parameters", [])
                if param.get("in") == "header"
            }
            if "ingestion" in path:
                assert "x-ingestion-admin-key" in header_names, (path, method)
            else:
                assert "x-ingestion-admin-key" not in header_names, (path, method)


# ---------------------------------------------------------------------------
# dry_run end-to-end through the real route, with a fake agent + a
# write-forbidding repository -- proves the ?dry_run=true wiring actually
# reaches OpportunityService.preview_batch() and never reaches insert()/
# update(), without touching real Supabase or the real Devpost source.
# ---------------------------------------------------------------------------


def test_run_source_dry_run_makes_zero_writes_and_reports_would_insert(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)
    monkeypatch.setattr(
        ingestion_route,
        "OpportunityService",
        lambda: OpportunityService(repository=_NoWriteRepository(), queue=_FakeQueue()),
    )
    agent_registry.register(_RouteFakeAgent)
    try:
        response = client.post(
            "/api/v1/ingestion/run/route-fake-source",
            params={"dry_run": "true"},
            headers={_KEY_HEADER: _SECRET},
        )
    finally:
        agent_registry.unregister("route-fake-source")

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["source"] == "route-fake-source"
    assert body["inserted"] == 1  # "would create", reported the same way a real insert is
    assert body["updated"] == 0
    assert body["failed"] == 0


def test_run_source_without_dry_run_actually_writes(client, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_ADMIN_API_KEY", _SECRET)
    repository = _RecordingRepository()
    monkeypatch.setattr(
        ingestion_route,
        "OpportunityService",
        lambda: OpportunityService(repository=repository, queue=_FakeQueue()),
    )
    agent_registry.register(_RouteFakeAgent)
    try:
        response = client.post(
            "/api/v1/ingestion/run/route-fake-source",
            headers={_KEY_HEADER: _SECRET},
        )
    finally:
        agent_registry.unregister("route-fake-source")

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is False
    assert body["inserted"] == 1
    assert len(repository.inserted) == 1  # the real write actually happened
