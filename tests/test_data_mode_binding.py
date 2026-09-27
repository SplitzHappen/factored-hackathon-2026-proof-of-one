from __future__ import annotations

import sqlite3
from pathlib import Path

import duckdb
import pytest

from app.artifact_identity import (
    BankArtifactIdentityError,
    CURATED_BUILDER_VERSION,
    CURATED_SCHEMA_VERSION,
    identify_bank_artifact_mode,
)
from app.bootstrap import build_app_context
from app.demo_data import build_synthetic_demo_bank
from app.runtime import OperationalStore, RuntimeDataModeMismatchError
from app.settings import Settings


def _write_curated_identity(path: Path) -> None:
    connection = duckdb.connect(str(path))
    try:
        connection.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO build_metadata VALUES (?, ?)",
            [CURATED_SCHEMA_VERSION, CURATED_BUILDER_VERSION],
        )
    finally:
        connection.close()


def test_artifact_identity_distinguishes_synthetic_and_curated(tmp_path: Path) -> None:
    synthetic = tmp_path / "synthetic.duckdb"
    curated = tmp_path / "curated.duckdb"
    build_synthetic_demo_bank(synthetic)
    _write_curated_identity(curated)

    assert identify_bank_artifact_mode(synthetic) == "synthetic"
    assert identify_bank_artifact_mode(curated) == "curated"


def test_curated_label_cannot_relabel_synthetic_artifact(tmp_path: Path) -> None:
    bank_path = tmp_path / "bank.duckdb"
    build_synthetic_demo_bank(bank_path)

    with pytest.raises(BankArtifactIdentityError, match="does not match"):
        build_app_context(
            Settings(
                bank_db_path=bank_path,
                runtime_db_path=tmp_path / "runtime.sqlite",
                data_mode="curated",
            )
        )


def test_curated_context_uses_artifact_identity_and_binds_runtime(tmp_path: Path) -> None:
    bank_path = tmp_path / "curated.duckdb"
    runtime_path = tmp_path / "curated-runtime.sqlite"
    _write_curated_identity(bank_path)

    context = build_app_context(
        Settings(
            bank_db_path=bank_path,
            runtime_db_path=runtime_path,
            data_mode="curated",
        )
    )

    assert context.data_mode == "curated"
    with sqlite3.connect(runtime_path) as connection:
        row = connection.execute(
            "SELECT value FROM runtime_metadata WHERE key = 'data_mode'"
        ).fetchone()
    assert row == ("curated",)


def test_runtime_store_refuses_cross_mode_reuse(tmp_path: Path) -> None:
    store = OperationalStore(tmp_path / "runtime.sqlite")
    store.initialize(data_mode="synthetic")
    store.initialize(data_mode="synthetic")

    with pytest.raises(RuntimeDataModeMismatchError, match="does not match"):
        store.initialize(data_mode="curated")
