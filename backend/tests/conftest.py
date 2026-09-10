import os

import pytest

# Configure the app for tests before app modules import settings.
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
# Off by default for the general-purpose `client` fixture below: no REDIS_URL
# is configured in the test environment, and RATE_LIMIT_FAIL_OPEN_AI
# defaults to False (fail-closed) by design (see app/core/config.py) — every
# existing test that isn't specifically about rate limiting shouldn't have
# to know that. tests/test_rate_limit_api.py explicitly re-enables it (via
# monkeypatch, scoped to just those tests) with a fake Redis backend.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    # raise_server_exceptions=False: match what a real deployed client sees.
    # TestClient's default (True) re-raises the ORIGINAL exception into the
    # test process even when the app's own @app.exception_handler(Exception)
    # catch-all (middleware/error_handler.py) already turned it into a clean
    # opaque 500 -- a TestClient debugging convenience, not what a real HTTP
    # client (or uvicorn) ever does. A test that deliberately raises an
    # unexpected backend error to verify it comes back as a sanitized 500
    # (see test_recommendations_api.py) needs the fixture to behave like a
    # real server, not re-raise past the handler that already ran.
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
