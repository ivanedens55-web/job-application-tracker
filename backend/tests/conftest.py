"""Test setup: a REAL Postgres database, schema applied from db/schema.sql,
and the app connecting as the restricted jobtracker_app role (like production).

Needs TEST_ADMIN_DATABASE_URL pointing at a throwaway database whose name
contains "test", e.g. postgresql://postgres:postgres@localhost:5432/jobtracker_test
DB tests are skipped if it's not set. Unit tests always run.
"""
import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.config import Settings
from app.main import create_app

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "db" / "schema.sql"
APP_ROLE_TEST_PASSWORD = "test-only-app-role-password"
ADMIN_URL = os.environ.get("TEST_ADMIN_DATABASE_URL", "")
FRONTEND_ORIGIN = "http://localhost:3000"


def make_settings(database_url: str = "postgresql://unused", **overrides) -> Settings:
    values = dict(
        database_url=database_url,
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        access_token_minutes=30,
        cors_origins=[FRONTEND_ORIGIN],
        environment="development",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture(scope="session")
def app_database_url() -> str:
    if not ADMIN_URL:
        pytest.skip("TEST_ADMIN_DATABASE_URL not set; skipping database tests")
    params = conninfo_to_dict(ADMIN_URL)
    # Safety guard: these tests DROP tables. Never run them against a real database.
    if "test" not in (params.get("dbname") or ""):
        pytest.exit("Refusing to run: the test database name must contain 'test'.")

    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS jobtracker_applications, jobtracker_users CASCADE")
        conn.execute(SCHEMA_FILE.read_text())
        conn.execute(f"ALTER ROLE jobtracker_app WITH PASSWORD '{APP_ROLE_TEST_PASSWORD}'")

    return make_conninfo(ADMIN_URL, user="jobtracker_app", password=APP_ROLE_TEST_PASSWORD)


@pytest.fixture
def admin_conn(app_database_url):
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        yield conn


@pytest.fixture
def client(app_database_url, admin_conn):
    admin_conn.execute("TRUNCATE jobtracker_applications, jobtracker_users RESTART IDENTITY CASCADE")
    app = create_app(make_settings(app_database_url))
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def register_and_login(client, email="ivan@example.com", password="correct-horse-1") -> dict:
    """Return Authorization headers for a fresh user."""
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client) -> dict:
    return register_and_login(client)
