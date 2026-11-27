from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ledgerflow.api.app import ApiError
from ledgerflow.config import Settings


def test_live_health_is_open_and_leaks_nothing(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_ready_checks_the_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_echoed_when_well_formed(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={"X-Request-Id": "req_client_01"})
    assert response.headers["X-Request-Id"] == "req_client_01"


def test_malformed_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={"X-Request-Id": "bad id\n"})
    assert response.headers["X-Request-Id"].startswith("req_")


def test_unknown_route_uses_the_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "NOT_FOUND"
    assert body["retryable"] is False
    assert body["request_id"] == response.headers["X-Request-Id"]
    assert "traceback" not in response.text.lower()


def test_api_error_carries_code_and_details(settings: Settings) -> None:
    from ledgerflow.api.app import create_app

    app = create_app(settings)

    @app.get("/api/v1/_test/stale")
    def stale() -> None:
        raise ApiError(
            409,
            "STALE_BASE",
            "This workbook changed after the preview.",
            details={"current_version_id": "ver_demo_2"},
        )

    with TestClient(app) as client:
        response = client.get("/api/v1/_test/stale")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "STALE_BASE"
    assert error["details"] == {"current_version_id": "ver_demo_2"}


def test_validation_error_names_fields_but_not_values(settings: Settings) -> None:
    from ledgerflow.api.app import create_app

    app: FastAPI = create_app(settings)

    @app.get("/api/v1/_test/limit")
    def limit(n: int) -> dict[str, int]:
        return {"n": n}

    with TestClient(app) as client:
        response = client.get("/api/v1/_test/limit?n=not-a-number-secret")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "BAD_REQUEST"
    assert error["details"]["fields"] == ["query/n"]
    assert "not-a-number-secret" not in response.text


def test_unhandled_exception_returns_generic_500(settings: Settings) -> None:
    from ledgerflow.api.app import create_app

    app = create_app(settings)

    @app.get("/api/v1/_test/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail /var/lib/ledgerflow")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_test/boom")
    assert response.status_code == 500
    assert response.json()["error"]["message"] == "internal error"
    assert "secret internal detail" not in response.text
