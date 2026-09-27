from __future__ import annotations

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import app.demo_data as demo_data
import app.main as main_module
from app.bootstrap import build_app_context
from app.settings import Settings


def _settings(tmp_path) -> Settings:
    return Settings(
        bank_db_path=tmp_path / "demo.duckdb",
        runtime_db_path=tmp_path / "runtime.sqlite",
        data_mode="synthetic",
    )


def test_repeated_startup_reuses_existing_synthetic_artifact(
    tmp_path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path)
    first = build_app_context(settings)

    original_write = demo_data._write_synthetic_demo_bank

    def unexpected_rebuild(path) -> None:
        raise AssertionError("recognized synthetic artifact must not be rebuilt")

    monkeypatch.setattr(demo_data, "_write_synthetic_demo_bank", unexpected_rebuild)
    second = build_app_context(settings)

    assert first.bank.database_path == second.bank.database_path
    assert first.store.path == second.store.path
    assert demo_data._is_recognized_synthetic_demo_bank(settings.bank_db_path)

    monkeypatch.setattr(demo_data, "_write_synthetic_demo_bank", original_write)


def test_concurrent_first_start_builds_once_and_initializes_runtime_safely(
    tmp_path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path)
    original_write = demo_data._write_synthetic_demo_bank
    write_count = 0
    count_lock = threading.Lock()
    start_barrier = threading.Barrier(4)

    def counted_write(path) -> None:
        nonlocal write_count
        with count_lock:
            write_count += 1
        # Keep the first builder inside the critical section long enough for the
        # other startup attempts to contend on the build lock.
        time.sleep(0.05)
        original_write(path)

    monkeypatch.setattr(demo_data, "_write_synthetic_demo_bank", counted_write)

    def start_context():
        start_barrier.wait()
        return build_app_context(settings)

    with ThreadPoolExecutor(max_workers=4) as executor:
        contexts = list(executor.map(lambda _: start_context(), range(4)))

    assert write_count == 1
    assert all(context.data_mode == "synthetic" for context in contexts)
    assert demo_data._is_recognized_synthetic_demo_bank(settings.bank_db_path)

    with sqlite3.connect(settings.runtime_db_path) as connection:
        row = connection.execute(
            "SELECT value FROM runtime_metadata WHERE key = 'schema_version'"
        ).fetchone()
    assert row is not None

    residue = {
        path.name
        for path in tmp_path.iterdir()
        if path.name.startswith(f".{settings.bank_db_path.name}.")
    }
    assert residue == set()


def test_default_app_builds_runtime_during_lifespan_before_requests(
    tmp_path,
    monkeypatch,
) -> None:
    context = build_app_context(_settings(tmp_path))
    calls = 0

    def counted_builder():
        nonlocal calls
        calls += 1
        return context

    monkeypatch.setattr(main_module, "build_app_context", counted_builder)
    application = main_module.create_app()

    assert getattr(application.state, "context", None) is None
    assert calls == 0

    with TestClient(application) as client:
        assert calls == 1
        assert application.state.context is context
        response = client.get("/api/demo/personas")
        assert response.status_code == 200
        assert calls == 1


def test_startup_validation_failure_prevents_application_start(
    monkeypatch,
) -> None:
    def fail_builder():
        raise RuntimeError("synthetic startup validation failed")

    monkeypatch.setattr(main_module, "build_app_context", fail_builder)
    application = main_module.create_app()

    with pytest.raises(RuntimeError, match="synthetic startup validation failed"):
        with TestClient(application):
            pass
