from fastapi.testclient import TestClient

from app.main import app, create_app


def test_app_exposes_health_and_chat_routes():
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/chat" in paths


def test_cors_preflight_allows_configured_origin():
    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_preflight_rejects_unconfigured_origin():
    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "https://not-allowed.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers
