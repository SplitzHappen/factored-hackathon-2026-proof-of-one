from __future__ import annotations

from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

from app.challenge_ui import render_challenge_ui
from app.main import create_app
from app.settings import Settings
from app.bootstrap import build_app_context


def _full_challenge_db(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        con.execute("INSERT INTO build_metadata VALUES (1, 'r3b-full-1')")

        con.execute(
            """
            CREATE TABLE customers (
                customer_id VARCHAR,
                country VARCHAR,
                detected_accent VARCHAR,
                customer_status VARCHAR
            )
            """
        )
        con.execute(
            "INSERT INTO customers VALUES ('C001', 'Brazil', 'brasileiro', 'Active')"
        )

        con.execute(
            """
            CREATE TABLE products (
                product_id VARCHAR,
                customer_id VARCHAR,
                product_type VARCHAR,
                currency VARCHAR,
                current_balance DECIMAL(15,2),
                opening_date DATE,
                expiration_date DATE,
                product_status VARCHAR,
                last_transaction_date TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO products VALUES (
                'P001', 'C001', 'Checking Account', 'BRL', 1000.00,
                DATE '2025-01-01', NULL, 'Active',
                TIMESTAMP '2026-09-25 10:00:00'
            )
            """
        )

        con.execute(
            """
            CREATE TABLE transactions (
                transaction_id VARCHAR,
                transaction_date TIMESTAMP,
                product_id VARCHAR,
                customer_id VARCHAR,
                transaction_type VARCHAR,
                transaction_category VARCHAR,
                amount DECIMAL(15,2),
                currency VARCHAR,
                channel VARCHAR,
                merchant_name VARCHAR,
                merchant_category VARCHAR,
                transaction_country VARCHAR,
                transaction_city VARCHAR,
                transaction_status VARCHAR,
                is_fraud BOOLEAN,
                fraud_score DECIMAL(5,2)
            )
            """
        )
        con.execute(
            """
            INSERT INTO transactions VALUES (
                'T001', TIMESTAMP '2026-09-25 10:00:00', 'P001', 'C001',
                'Payment', 'Retail', 125.00, 'BRL', 'App', 'Mercado',
                'Retail', 'Brazil', 'Sao Paulo', 'Approved', false, 1.00
            )
            """
        )

        con.execute("CREATE TABLE challenge_customers AS SELECT * FROM customers")
        con.execute("CREATE TABLE challenge_products AS SELECT * FROM products")
        con.execute("CREATE TABLE challenge_transactions AS SELECT * FROM transactions")

        con.execute(
            """
            CREATE TABLE call_transcripts (
                transcript_id VARCHAR,
                interaction_id VARCHAR,
                process_date VARCHAR,
                customer_id VARCHAR,
                agent_id VARCHAR,
                customer_text VARCHAR,
                detected_language VARCHAR,
                main_topics VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO call_transcripts VALUES
            (
                'TR002', 'I002', '2026-09-25', 'C001', 'A001',
                'Qual é o estado do meu pagamento?', 'Portuguese', 'payments'
            ),
            (
                'TR001', 'I001', '2026-09-20', 'C001', 'A001',
                'Preciso de ajuda com minha conta.', 'Portuguese', 'account'
            )
            """
        )

        con.execute(
            """
            CREATE TABLE call_center_interactions (
                interaction_id VARCHAR,
                customer_id VARCHAR
            )
            """
        )
        con.execute("INSERT INTO call_center_interactions VALUES ('I001', 'C001')")

        for table in (
            "campaign_sends",
            "complaints",
            "digital_events",
            "satisfaction_surveys",
            "branches",
            "daily_exchange_rates",
            "marketing_campaigns",
            "service_agents",
        ):
            con.execute(f"CREATE TABLE {table} (fixture_id VARCHAR)")
            con.execute(f"INSERT INTO {table} VALUES ('fixture')")
    finally:
        con.close()


def _client(tmp_path: Path) -> TestClient:
    bank_path = tmp_path / "full-challenge.duckdb"
    _full_challenge_db(bank_path)
    context = build_app_context(
        Settings(
            bank_db_path=bank_path,
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="curated",
            interpretation_provider="deterministic",
        )
    )
    return TestClient(create_app(context))


def test_full_challenge_coverage_and_customer_message_access(tmp_path: Path) -> None:
    client = _client(tmp_path)

    coverage = client.get("/api/challenge/coverage")
    assert coverage.status_code == 200
    body = coverage.json()
    assert body["full_challenge_data"] is True
    assert body["table_counts"]["customers"] == 1
    assert body["table_counts"]["call_transcripts"] == 2

    search = client.get("/api/challenge/customers", params={"query": "C00"})
    assert search.status_code == 200
    customers = search.json()
    assert customers == [
        {
            "customer_id": "C001",
            "country": "Brazil",
            "detected_accent": "brasileiro",
            "customer_status": "Active",
            "default_language": "pt",
            "transcript_count": 2,
        }
    ]

    messages = client.get("/api/challenge/customers/C001/messages")
    assert messages.status_code == 200
    rows = messages.json()
    assert [row["transcript_id"] for row in rows] == ["TR002", "TR001"]
    assert rows[0]["customer_text"] == "Qual é o estado do meu pagamento?"
    assert rows[1]["customer_text"] == "Preciso de ajuda com minha conta."


def test_challenge_session_runs_through_existing_deterministic_policy(tmp_path: Path) -> None:
    client = _client(tmp_path)

    session_response = client.post(
        "/api/challenge/sessions",
        json={"customer_id": "C001"},
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["customer_id"] == "C001"
    assert session["language"] == "pt"
    assert session["transcript_count"] == 2
    assert session["synthetic_data"] is False

    turn = client.post(
        "/api/customer/turn",
        headers={"X-Demo-Session": session["session_id"]},
        json={"message": "Quero fazer uma transferência de 100 BRL para outra conta."},
    )
    assert turn.status_code == 200
    result = turn.json()
    assert result["route"] == "ABSTAIN"
    assert result["synthetic_data"] is False


def test_challenge_customer_access_is_exactly_scoped(tmp_path: Path) -> None:
    client = _client(tmp_path)

    missing = client.post(
        "/api/challenge/sessions",
        json={"customer_id": "C999"},
    )
    assert missing.status_code == 404

    messages = client.get("/api/challenge/customers/C999/messages")
    assert messages.status_code == 404


def test_curated_mode_serves_full_challenge_judge_shell(tmp_path: Path) -> None:
    client = _client(tmp_path)

    for route in ("/", "/demo"):
        response = client.get(route)
        assert response.status_code == 200
        html = response.text
        assert "Proof of One" in html
        assert "Deterministic Support Interlock" in html
        assert "Customer-scoped records · LLM interpretation" in html
        assert "Challenge data" in html
        assert "/api/challenge/coverage" in html
        assert "/api/challenge/customers" in html
        assert "/api/challenge/sessions" in html
        assert "/api/customer/turn" in html
        assert "Provided messages" in html
        assert "customer_text" in html
        assert "Lucía" not in html
        assert "Rafael" not in html


def test_full_challenge_shell_preserves_dataset_message_text_safely() -> None:
    html = render_challenge_ui(llm_connected=True)

    assert "LIVE LLM · FULL DATA" in html
    assert "OpenAI GPT-6 Luna · deterministic policy authority retained" in html
    assert "customer_text" in html
    assert "els.messageBox.value=m.customer_text" in html
    assert "els.response.textContent=data.response_text" in html
    assert "document_number" not in html
    assert "mobile_phone" not in html
    assert "email" not in html


def test_challenge_api_paths_are_visible_in_openapi(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/api/challenge/coverage" in paths
    assert "/api/challenge/customers" in paths
    assert "/api/challenge/customers/{customer_id}/messages" in paths
    assert "/api/challenge/sessions" in paths
