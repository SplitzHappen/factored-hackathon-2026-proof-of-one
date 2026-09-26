from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import duckdb
import pytest

from ml.full_data_contract import MODEL_FEATURES, feature_contract_sha256
from ml.model_selection import (
    LOGISTIC_CONFIG,
    ModelSelectionError,
    model_selection_contract_dict,
    model_selection_contract_sha256,
    run_model_selection,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _init_git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _schema_for_feature(name: str, kind: str) -> str:
    if kind == "categorical":
        return f'"{name}" VARCHAR'
    if kind == "boolean":
        return f'"{name}" BOOLEAN'
    return f'"{name}" DOUBLE'


def _build_analytics(path: Path, *, flip_later_labels: bool) -> dict[str, int]:
    counts = {
        "train": 400,
        "model_selection": 160,
        "calibration_gate": 120,
        "test": 120,
    }
    con = duckdb.connect(str(path))
    try:
        feature_columns = ",\n".join(
            _schema_for_feature(feature.name, feature.kind)
            for feature in MODEL_FEATURES
        )
        con.execute(
            f"""
            CREATE TABLE feature_rows (
                transaction_id VARCHAR,
                transaction_date TIMESTAMP,
                segment VARCHAR,
                is_fraud BOOLEAN,
                {feature_columns}
            )
            """
        )

        offset = 0
        for segment, rows in counts.items():
            for local_index in range(rows):
                global_index = offset + local_index
                strong_signal = local_index % 20 == 0
                label = strong_signal
                if segment in {"calibration_gate", "test"} and flip_later_labels:
                    label = not label

                values: dict[str, object] = {}
                for feature in MODEL_FEATURES:
                    if feature.kind == "categorical":
                        if feature.name == "currency":
                            values[feature.name] = "COP" if strong_signal else "MXN"
                        elif feature.name == "channel":
                            values[feature.name] = "Web" if strong_signal else "App"
                        elif feature.name == "merchant_category":
                            values[feature.name] = "Travel" if strong_signal else "Retail"
                        elif feature.name == "transaction_type":
                            values[feature.name] = "Purchase"
                        elif feature.name == "transaction_category":
                            values[feature.name] = "Card Purchase"
                        else:
                            values[feature.name] = "Checking"
                    elif feature.kind == "boolean":
                        values[feature.name] = bool(strong_signal)
                    else:
                        if feature.name == "log_amount":
                            values[feature.name] = 8.0 if strong_signal else 2.0
                        elif feature.name == "amount_to_prior_currency_mean_ratio":
                            values[feature.name] = 8.0 if strong_signal else 1.0
                        elif feature.name == "prior_24h_tx_count":
                            values[feature.name] = 5.0 if strong_signal else 0.0
                        elif feature.name == "prior_30d_tx_count":
                            values[feature.name] = 20.0 if strong_signal else 1.0
                        elif feature.name == "seconds_since_previous_tx":
                            values[feature.name] = 60.0 if strong_signal else 86400.0
                        else:
                            values[feature.name] = float((global_index % 7) + 1)

                columns = [
                    "transaction_id",
                    "transaction_date",
                    "segment",
                    "is_fraud",
                    *[feature.name for feature in MODEL_FEATURES],
                ]
                placeholders = ", ".join("?" for _ in columns)
                row = [
                    f"T-{global_index:05d}",
                    f"2025-01-01 00:{global_index % 60:02d}:00",
                    segment,
                    label,
                    *[values[feature.name] for feature in MODEL_FEATURES],
                ]
                con.execute(
                    f"""
                    INSERT INTO feature_rows (
                        {", ".join(f'"{column}"' for column in columns)}
                    ) VALUES ({placeholders})
                    """,
                    row,
                )
            offset += rows
    finally:
        con.close()
    return counts


def _write_manifest(path: Path, db: Path, counts: dict[str, int]) -> None:
    payload = {
        "artifact_database_sha256": _sha256(db),
        "contract_sha256": feature_contract_sha256(),
        "model_feature_count": len(MODEL_FEATURES),
        "split_plan": {
            "train_rows": counts["train"],
            "model_selection_rows": counts["model_selection"],
            "calibration_gate_rows": counts["calibration_gate"],
            "test_rows": counts["test"],
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _tiny_candidates():
    base = {
        "learning_rate": 0.1,
        "max_iter": 12,
        "max_leaf_nodes": 7,
        "min_samples_leaf": 10,
        "l2_regularization": 1.0,
    }
    return (
        {"id": "first", **base},
        {"id": "second", **base},
    )


def _fast_logistic():
    config = dict(LOGISTIC_CONFIG)
    config["max_iter"] = 10
    config["tol"] = 1e-3
    return config


def _selection_signature(result: dict) -> dict:
    return {
        "train": result["train"],
        "model_selection": result["model_selection"],
        "baselines": result["baselines"],
        "logistic": {
            "config": result["logistic"]["config"],
            "encoded_feature_count": result["logistic"]["encoded_feature_count"],
            "selection": result["logistic"]["selection"],
        },
        "gbdt_candidates": [
            {
                "id": item["id"],
                "config": item["config"],
                "selection": item["selection"],
            }
            for item in result["gbdt_candidates"]
        ],
        "selected_gbdt": result["selected_gbdt"],
    }


def test_model_selection_never_depends_on_gate_or_test_labels(tmp_path: Path) -> None:
    repo_root = _init_git_repo(tmp_path)

    first_db = tmp_path / "first.duckdb"
    first_manifest = tmp_path / "first_manifest.json"
    first_counts = _build_analytics(first_db, flip_later_labels=False)
    _write_manifest(first_manifest, first_db, first_counts)

    second_db = tmp_path / "second.duckdb"
    second_manifest = tmp_path / "second_manifest.json"
    second_counts = _build_analytics(second_db, flip_later_labels=True)
    _write_manifest(second_manifest, second_db, second_counts)

    first = run_model_selection(
        feature_database_path=first_db,
        feature_manifest_path=first_manifest,
        output_path=tmp_path / "first_result.json",
        repo_root=repo_root,
        candidate_configs=_tiny_candidates(),
        logistic_config=_fast_logistic(),
    )
    second = run_model_selection(
        feature_database_path=second_db,
        feature_manifest_path=second_manifest,
        output_path=tmp_path / "second_result.json",
        repo_root=repo_root,
        candidate_configs=_tiny_candidates(),
        logistic_config=_fast_logistic(),
    )

    assert _selection_signature(first) == _selection_signature(second)
    assert first["information_boundary"]["calibration_gate_read"] is False
    assert first["information_boundary"]["test_read"] is False


def test_exact_gbdt_tie_keeps_earlier_simpler_candidate(tmp_path: Path) -> None:
    repo_root = _init_git_repo(tmp_path)
    db = tmp_path / "analytics.duckdb"
    manifest = tmp_path / "manifest.json"
    counts = _build_analytics(db, flip_later_labels=False)
    _write_manifest(manifest, db, counts)

    result = run_model_selection(
        feature_database_path=db,
        feature_manifest_path=manifest,
        output_path=tmp_path / "result.json",
        repo_root=repo_root,
        candidate_configs=_tiny_candidates(),
        logistic_config=_fast_logistic(),
    )

    first, second = result["gbdt_candidates"]
    assert first["selection"]["pr_auc"] == second["selection"]["pr_auc"]
    assert result["selected_gbdt"]["id"] == "first"


def test_model_selection_contract_is_frozen_and_hashed() -> None:
    contract = model_selection_contract_dict()
    assert contract["information_boundary"] == {
        "fit": ["train"],
        "select": ["model_selection"],
        "forbidden": ["calibration_gate", "test"],
    }
    assert contract["logistic_config"]["alpha"] == 1e-4
    assert [item["id"] for item in contract["gbdt_candidates"]] == [
        "gbdt-small",
        "gbdt-medium",
        "gbdt-regularized",
    ]
    assert contract["gbdt_implementation"] == "sklearn.HistGradientBoostingClassifier"

    digest = model_selection_contract_sha256()
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_model_selection_refuses_overwrite(tmp_path: Path) -> None:
    repo_root = _init_git_repo(tmp_path)
    db = tmp_path / "analytics.duckdb"
    manifest = tmp_path / "manifest.json"
    counts = _build_analytics(db, flip_later_labels=False)
    _write_manifest(manifest, db, counts)
    output = tmp_path / "result.json"
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ModelSelectionError, match="already exists"):
        run_model_selection(
            feature_database_path=db,
            feature_manifest_path=manifest,
            output_path=output,
            repo_root=repo_root,
            candidate_configs=_tiny_candidates(),
            logistic_config=_fast_logistic(),
        )
