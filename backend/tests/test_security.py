import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app

from .conftest import FRONTEND_ORIGIN, make_settings


@pytest.fixture
def no_db_client():
    # These checks don't touch the database, so the pool is never used.
    app = create_app(make_settings())
    return TestClient(app, raise_server_exceptions=False)


def test_security_headers(no_db_client):
    headers = no_db_client.get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert "strict-transport-security" not in headers  # only in production


def test_hsts_in_production_and_docs_disabled():
    client = TestClient(create_app(make_settings(environment="production")))
    assert "max-age" in client.get("/health").headers["strict-transport-security"]
    assert client.get("/docs").status_code == 404


def test_cors_allows_only_the_frontend(no_db_client):
    preflight = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}
    ok = no_db_client.options("/applications", headers={"Origin": FRONTEND_ORIGIN, **preflight})
    assert ok.headers["access-control-allow-origin"] == FRONTEND_ORIGIN

    evil = no_db_client.options("/applications", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in evil.headers


def test_unknown_route_and_method_use_error_format(no_db_client):
    assert no_db_client.get("/nope").json()["error"]["code"] == "not_found"
    assert no_db_client.put("/health").json()["error"]["code"] == "method_not_allowed"


def test_unexpected_errors_are_generic():
    app = create_app(make_settings())

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail at /srv/app.py")

    res = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "internal_error"
    assert "secret" not in res.text
    assert res.headers["x-content-type-options"] == "nosniff"


def test_settings_reject_wildcard_cors_and_weak_secret(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="CORS"):
        load_settings()
    monkeypatch.setenv("CORS_ORIGINS", FRONTEND_ORIGIN)
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()
