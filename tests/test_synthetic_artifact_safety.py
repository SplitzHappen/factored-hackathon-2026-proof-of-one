from __future__ import annotations

import hashlib

import duckdb
import pytest

import app.demo_data as demo_data


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_curated_marker(path) -> None:
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
        connection.execute("INSERT INTO build_metadata VALUES (1, 'r3b-1')")
        connection.execute("CREATE TABLE sentinel(value VARCHAR)")
        connection.execute("INSERT INTO sentinel VALUES ('preserve-me')")
        connection.execute("CHECKPOINT")
    finally:
        connection.close()


def test_builder_refuses_curated_artifact_and_preserves_hash(tmp_path) -> None:
    target = tmp_path / "bank.duckdb"
    _write_curated_marker(target)
    before = _sha256(target)

    with pytest.raises(
        demo_data.SyntheticArtifactSafetyError,
        match="not a recognized Proof of One synthetic demo artifact",
    ):
        demo_data.build_synthetic_demo_bank(target)

    assert _sha256(target) == before


def test_builder_refuses_unrelated_file_and_preserves_hash(tmp_path) -> None:
    target = tmp_path / "bank.duckdb"
    target.write_bytes(b"not-a-duckdb-artifact\n")
    before = _sha256(target)

    with pytest.raises(
        demo_data.SyntheticArtifactSafetyError,
        match="not a recognized Proof of One synthetic demo artifact",
    ):
        demo_data.build_synthetic_demo_bank(target)

    assert _sha256(target) == before


def test_builder_may_refresh_only_recognized_synthetic_artifact(tmp_path) -> None:
    target = tmp_path / "demo.duckdb"
    demo_data.build_synthetic_demo_bank(target)

    connection = duckdb.connect(str(target))
    try:
        connection.execute("CREATE TABLE scratch(value INTEGER)")
        connection.execute("INSERT INTO scratch VALUES (1)")
        connection.execute("CHECKPOINT")
    finally:
        connection.close()

    demo_data.build_synthetic_demo_bank(target)

    connection = duckdb.connect(str(target), read_only=True)
    try:
        metadata = connection.execute(
            "SELECT schema_version, builder_version FROM build_metadata"
        ).fetchall()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert metadata == [
        (
            demo_data.SYNTHETIC_SCHEMA_VERSION,
            demo_data.SYNTHETIC_BUILDER_VERSION,
        )
    ]
    assert "scratch" not in tables


def test_replace_failure_preserves_existing_hash_and_cleans_temp(
    tmp_path,
    monkeypatch,
) -> None:
    target = tmp_path / "demo.duckdb"
    demo_data.build_synthetic_demo_bank(target)
    before = _sha256(target)

    def fail_replace(source, destination) -> None:
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(demo_data.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated atomic replace failure"):
        demo_data.build_synthetic_demo_bank(target)

    assert _sha256(target) == before
    assert [
        path
        for path in tmp_path.iterdir()
        if path.name.startswith(f".{target.name}.")
    ] == []
