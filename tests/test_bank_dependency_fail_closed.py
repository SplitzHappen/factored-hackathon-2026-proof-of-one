from __future__ import annotations

import duckdb
from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings


def _client(tmp_path) -> tuple[TestClient, object]:
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


def _assert_bank_failure(body: dict) -> None:
    assert body == {
        "detail": (
            "Verified banking data is temporarily unavailable. "
            "No account information was returned."
        ),
        "dependency": "bank",
        "execution_status": "dependency_unavailable",
        "action_completed": False,
        "banking_fact_released": False,
    }
    assert "route" not in body
    assert "intent" not in body
    assert "transactions" not in body
    assert "products" not in body


def test_bank_failure_before_policy_fails_closed_without_route_or_facts(
    tmp_path,
    monkeypatch,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client)

    def fail_get_transaction(*args, **kwargs):
        del args, kwargs
        raise duckdb.IOException("SENSITIVE simulated bank read failure")

    monkeypatch.setattr(context.bank, "get_transaction", fail_get_transaction)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "¿Cuál es el estado de la transacción DEMO-ES-1001?"},
    )

    assert response.status_code == 503
    _assert_bank_failure(response.json())
    assert "SENSITIVE" not in response.text
    assert "DEMO-ES-1001" not in response.text


def test_bank_failure_after_policy_still_releases_no_route_or_banking_fact(
    tmp_path,
    monkeypatch,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client)

    def fail_recent(*args, **kwargs):
        del args, kwargs
        raise duckdb.IOException("SENSITIVE post-policy bank failure")

    monkeypatch.setattr(context.bank, "list_recent_transactions", fail_recent)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert response.status_code == 503
    _assert_bank_failure(response.json())
    assert "SENSITIVE" not in response.text


def test_incompatible_bank_failure_uses_same_sanitized_contract(
    tmp_path,
    monkeypatch,
) -> None:
    client, context = _client(tmp_path)
    session = _session(client)

    from app.bank import IncompatibleBankDatabaseError

    def fail_recent(*args, **kwargs):
        del args, kwargs
        raise IncompatibleBankDatabaseError("SENSITIVE schema detail")

    monkeypatch.setattr(context.bank, "list_recent_transactions", fail_recent)

    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Muéstrame mis últimos movimientos."},
    )

    assert response.status_code == 503
    _assert_bank_failure(response.json())
    assert "SENSITIVE" not in response.text


def test_openapi_documents_bank_dependency_failure_contract(tmp_path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    post = response.json()["paths"]["/api/customer/turn"]["post"]
    schema = post["responses"]["503"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/DependencyUnavailableResponse")
