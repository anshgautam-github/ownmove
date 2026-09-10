def test_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_protected_route_requires_auth(client):
    """No bearer token -> 401 in our uniform error envelope."""
    response = client.get("/api/v1/profiles/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_request_id_header_is_returned(client):
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")
