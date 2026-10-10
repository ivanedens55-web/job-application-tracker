"""The backend's routes and methods must match docs/openapi.yaml exactly."""
from pathlib import Path

import yaml
from fastapi.routing import APIRoute

from app.main import create_app

from .conftest import make_settings

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def contract_operations() -> set[tuple[str, str]]:
    spec = yaml.safe_load(CONTRACT.read_text())
    return {
        (method.upper(), path)
        for path, item in spec["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }


def app_operations() -> set[tuple[str, str]]:
    app = create_app(make_settings(environment="production"))  # production: no /docs routes
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods - {"HEAD", "OPTIONS"}
    }


def test_backend_matches_contract():
    expected, actual = contract_operations(), app_operations()
    assert actual - expected == set(), f"Routes in the app but not in the contract: {actual - expected}"
    assert expected - actual == set(), f"Routes in the contract but not in the app: {expected - actual}"


def test_contract_declares_status_codes_the_app_uses():
    spec = yaml.safe_load(CONTRACT.read_text())
    app = create_app(make_settings(environment="production"))
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            responses = spec["paths"][route.path][method.lower()]["responses"]
            assert str(route.status_code or 200) in responses, (method, route.path)
