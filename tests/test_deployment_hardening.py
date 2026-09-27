from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.http_safety import DEFAULT_MAX_REQUEST_BODY_BYTES
from app.main import create_app
from app.settings import Settings


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context)), context


def _session(client: TestClient) -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": "lucia"})
    assert response.status_code == 201
    return response.json()


def test_ready_reports_live_dependency_state(tmp_path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "proof-of-one",
        "data_mode": "synthetic",
        "synthetic_data": True,
        "bank_ready": True,
        "runtime_ready": True,
        "llm_connected": False,
    }


def test_ready_fails_closed_when_runtime_schema_binding_is_corrupted(tmp_path) -> None:
    client, context = _client(tmp_path)

    with sqlite3.connect(context.store.path) as connection:
        connection.execute(
            "UPDATE runtime_metadata SET value = '999' WHERE key = 'schema_version'"
        )
        connection.commit()

    response = client.get("/ready")
    liveness = client.get("/health")

    assert response.status_code == 503
    assert liveness.status_code == 200
    assert liveness.json()["status"] == "ok"
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["bank_ready"] is True
    assert body["runtime_ready"] is False
    assert body["data_mode"] == "synthetic"


def test_ready_fails_closed_when_bank_dependency_is_not_ready(
    tmp_path,
    monkeypatch,
) -> None:
    client, context = _client(tmp_path)

    def fail_bank_ready() -> None:
        raise RuntimeError("simulated bank readiness failure")

    monkeypatch.setattr(context.bank, "check_ready", fail_bank_ready)

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["bank_ready"] is False
    assert body["runtime_ready"] is True


def test_runtime_store_uses_wal_mode(tmp_path) -> None:
    _, context = _client(tmp_path)

    with sqlite3.connect(context.store.path) as connection:
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert str(mode).casefold() == "wal"
    context.store.check_ready(expected_data_mode="synthetic")


def test_oversized_request_is_rejected_before_model_validation(tmp_path) -> None:
    client, _ = _client(tmp_path)
    oversized = "x" * (DEFAULT_MAX_REQUEST_BODY_BYTES + 1)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": "not-a-session"},
        json={"message": oversized},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}
    assert len(response.content) < 256


def test_validation_error_does_not_echo_customer_input(tmp_path) -> None:
    client, _ = _client(tmp_path)
    long_but_allowed_body = "SENSITIVE-" + ("z" * 5000)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": "not-a-session"},
        json={"message": long_but_allowed_body},
    )

    assert response.status_code == 422
    assert long_but_allowed_body not in response.text
    assert "SENSITIVE-" not in response.text
    assert len(response.content) < 2048
    detail = response.json()["detail"]
    assert detail
    assert all("input" not in item for item in detail)


def test_body_cap_allows_normal_customer_turn(tmp_path) -> None:
    client, _ = _client(tmp_path)
    session = _session(client)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert response.status_code == 200


def test_body_limit_handles_chunked_asgi_input_without_content_length(tmp_path) -> None:
    app = create_app(build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    ))
    chunk = b"x" * (DEFAULT_MAX_REQUEST_BODY_BYTES // 2 + 1)
    messages = [
        {"type": "http.request", "body": chunk, "more_body": True},
        {"type": "http.request", "body": chunk, "more_body": False},
    ]
    sent = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    import asyncio

    asyncio.run(
        app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/customer/turn",
                "raw_path": b"/api/customer/turn",
                "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "client": ("testclient", 123),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
    )

    start = next(message for message in sent if message["type"] == "http.response.start")
    body = next(message for message in sent if message["type"] == "http.response.body")
    assert start["status"] == 413
    assert json.loads(body["body"]) == {"detail": "Request body too large"}
