from __future__ import annotations

from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings


def _client(tmp_path) -> TestClient:
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context))


def _session(client: TestClient, persona_id: str = "lucia") -> dict:
    response = client.post("/api/demo/sessions", json={"persona_id": persona_id})
    assert response.status_code == 201
    return response.json()


def _turn(client: TestClient, session: dict, message: str) -> dict:
    response = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": message},
    )
    assert response.status_code == 200
    return response.json()


def test_answer_exposes_verified_read_evidence(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client)

    body = _turn(
        client,
        session,
        "¿Cuál es el estado de la transacción DEMO-ES-1001?",
    )

    assert body["route"] == "ANSWER"
    evidence = body["decision_evidence"]
    assert evidence == {
        "language": "es",
        "interpretation_status": "verified",
        "reference_status": "verified",
        "controlling_check": None,
        "controlling_reason": "supported_verified",
        "action": "read_verified_bank_records",
        "execution_status": "completed",
        "verification_codes": [
            "customer_scope_enforced",
            "records_verified",
        ],
    }


def test_clarify_exposes_ambiguity_preservation_evidence(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client)

    body = _turn(
        client,
        session,
        "Quiero consultar una transacción por 54000 COP.",
    )

    assert body["route"] == "CLARIFY"
    evidence = body["decision_evidence"]
    assert evidence["interpretation_status"] == "verified"
    assert evidence["reference_status"] == "ambiguous"
    assert evidence["controlling_check"] == 8
    assert evidence["controlling_reason"] == "ambiguous_transaction_match"
    assert evidence["action"] == "none"
    assert evidence["execution_status"] == "not_invoked"
    assert evidence["verification_codes"] == [
        "no_banking_action",
        "ambiguity_preserved",
    ]


def test_escalate_exposes_persisted_readback_verified_action(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client)

    body = _turn(
        client,
        session,
        (
            "No reconozco la transacción DEMO-ES-1001. "
            "Yo no autoricé ese pago."
        ),
    )

    assert body["route"] == "ESCALATE"
    assert body["escalation_ticket_id"]
    evidence = body["decision_evidence"]
    assert evidence["controlling_check"] == 1
    assert evidence["controlling_reason"] == "unauthorized_activity_reported"
    assert evidence["action"] == "create_escalation_ticket"
    assert evidence["execution_status"] == "completed"
    assert evidence["verification_codes"] == [
        "escalation_persisted",
        "escalation_readback_verified",
    ]


def test_abstain_exposes_no_banking_action_evidence(tmp_path) -> None:
    client = _client(tmp_path)
    session = _session(client)

    body = _turn(client, session, "Transfiere 100 a mi otra cuenta.")

    assert body["route"] == "ABSTAIN"
    evidence = body["decision_evidence"]
    assert evidence["controlling_check"] == 6
    assert evidence["controlling_reason"] == "prohibited_banking_action"
    assert evidence["action"] == "none"
    assert evidence["execution_status"] == "not_invoked"
    assert evidence["verification_codes"] == ["no_banking_action"]


def test_demo_ui_surfaces_compact_operational_decision_evidence(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Decision evidence" in html
    assert "decision_evidence" in html
    assert "controlling_check" in html
    assert "controlling_reason" in html
    assert "verification_codes" in html
    assert "Proof of One does not expose model reasoning" not in html
