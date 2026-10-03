from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.bootstrap import build_app_context
from app.main import create_app
from app.settings import Settings


def _live_provider_client(tmp_path) -> TestClient:
    base_context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(replace(base_context, llm_connected=True)))


def test_live_provider_demo_shell_removes_no_live_llm_copy(tmp_path) -> None:
    client = _live_provider_client(tmp_path)

    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "OpenAI GPT-6 Luna · deterministic policy authority retained" in html
    assert "Live LLM · synthetic" in html
    assert (
        "Synthetic data · live LLM interpretation · deterministic policy · "
        "not fraud detection · not production/pilot-ready"
    ) in html
    assert "live-provider interpretation behind deterministic policy" in html
    assert "LLM interprets language<br>Deterministic checks override intent<br>Not fraud detection" in html
    assert "LLM interprets language · deterministic checks override intent · Not fraud detection" not in html
    assert "no live LLM" not in html.casefold()
    assert "no live-provider readiness claim" not in html.casefold()


def test_live_provider_status_is_exposed_in_readiness_and_health(tmp_path) -> None:
    client = _live_provider_client(tmp_path)

    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 200
    assert health.json()["llm_connected"] is True
    assert ready.json()["llm_connected"] is True
