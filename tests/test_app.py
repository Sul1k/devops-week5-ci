"""Unit tests for the Flask app. Run with `pytest` from the homework folder."""

import pytest

from app import APP_VERSION, app, greeting


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_index_returns_json_with_version(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    body = response.get_json()
    assert body["version"] == APP_VERSION
    assert body["message"] == greeting()
    assert body["hostname"]


def test_hello_route_uses_the_name(client):
    response = client.get("/hello/Sultan")
    assert response.status_code == 200
    assert response.get_json()["message"] == "Hello, Sultan, from the DevOps Week 5 container"


def test_unknown_route_is_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (None, "Hello from the DevOps Week 5 container"),
        ("", "Hello from the DevOps Week 5 container"),
        ("   ", "Hello from the DevOps Week 5 container"),
        ("Ada", "Hello, Ada, from the DevOps Week 5 container"),
        ("  Ada  ", "Hello, Ada, from the DevOps Week 5 container"),
    ],
)
def test_greeting(name, expected):
    assert greeting(name) == expected
