from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import duckdb
import pytest

from ml.calibration_contract import (
    C_B_IMPLEMENTATION_COMMIT,
    selected_gbdt_config,
)
from ml.calibration_gate import (
    CalibrationGateError,
    _load_segments,
    run_calibration_gate,
)
from ml.full_data_contract import MODEL_FEATURES, feature_contract_sha256


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


def _build_analytics(path: Path, *, flip_test_labels: bool = False) -> dict[str, int]:
    con = duckdb.connect(str(path))
    try:
        con.execute(
            """
            CREATE TABLE feature_rows (
                transaction_id VARCHAR,
                transaction_date TIMESTAMP,
                segment VARCHAR,
                is_fraud BOOLEAN,
                log_amount DOUBLE,
                hour_of_day DOUBLE,
                day_of_week DOUBLE,
                product_tenure_days DOUBLE,
                currency VARCHAR,
                transaction_type VARCHAR,
                transaction_category VARCHAR,
                channel VARCHAR,
                merchant_category VARCHAR,
                product_type VARCHAR,
                prior_tx_count_lifetime BIGINT,
                has_prior_transaction BOOLEAN,
                seconds_since_previous_tx DOUBLE,
                prior_24h_tx_count BIGINT,
                prior_24h_amount_sum DOUBLE,
                prior_30d_tx_count BIGINT,
                prior_30d_amount_sum DOUBLE,
                prior_currency_mean_amount_lifetime DOUBLE,
                has_prior_currency_amount_history BOOLEAN,
                amount_to_prior_currency_mean_ratio DOUBLE,
                prior_channel_count_lifetime BIGINT,
                channel_novelty BOOLEAN,
                prior_merchant_category_count_lifetime BIGINT,
                merchant_category_novelty BOOLEAN,
                prior_transaction_country_count_lifetime BIGINT,
                transaction_country_novelty BOOLEAN
            )
            """
        )

        counts = {
            "train": 240,
            "model_selection": 60,
            "calibration_gate": 60,
            "test": 80,
        }
        start = 0
        for segment, n_rows in counts.items():
            for local in range(n_rows):
                index = start + local
                fraud = local % 19 == 0
                if segment == "test" and flip_test_labels:
                    fraud = not fraud
                amount_ratio = 4.0 if fraud else 1.05 + (index % 5) * 0.05
                channel_novelty = bool(fraud or index % 13 == 0)
                country_novelty = bool(fraud or index % 17 == 0)
                merchant_novelty = bool(fraud or index % 11 == 0)
                con.execute(
                    """
                    INSERT INTO feature_rows VALUES (
                        ?,
                        TIMESTAMP '2025-01-01 00:00:00' + (? * INTERVAL '1 hour'),
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        'Purchase',
                        'Retail',
                        ?,
                        ?,
                        'Checking',
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    [
                        f"T-{index:05d}",
                        index,
                        segment,
                        fraud,
                        6.0 if fraud else 2.0 + (index % 7) * 0.1,
                        index % 24,
                        index % 7,
                        100 + index,
                        "COP" if index % 2 else "MXN",
                        "Web" if fraud else ("App" if index % 2 else "POS"),
                        "Services" if fraud else "Food",
                        index,
                        index > 0,
                        3600.0 if index > 0 else None,
                        7 if fraud else index % 3,
                        700.0 if fraud else float(index % 50),
                        25 if fraud else index % 10,
                        2500.0 if fraud else float(index % 200),
                        20.0,
                        True,
                        amount_ratio,
                        0 if channel_novelty else 4,
                        channel_novelty,
                        0 if merchant_novelty else 5,
                        merchant_novelty,
                        0 if country_novelty else 8,
                        country_novelty,
                    ],
                )
            start += n_rows
    finally:
        con.close()
    return counts


def _write_feature_manifest(
    path: Path,
    db_path: Path,
    counts: dict[str, int],
) -> None:
    payload = {
        "artifact_database_sha256": _sha256(db_path),
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


def _write_c_b_result(path: Path) -> str:
    payload = {
        "implementation_commit": C_B_IMPLEMENTATION_COMMIT,
        "selected_gbdt": {
            "id": "gbdt-small",
            "config": selected_gbdt_config(),
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return _sha256(path)


def _fixture(tmp_path: Path, *, flip_test_labels: bool = False):
    db = tmp_path / "analytics.duckdb"
    manifest = tmp_path / "analytics_manifest.json"
    c_b = tmp_path / "model_selection.json"
    counts = _build_analytics(db, flip_test_labels=flip_test_labels)
    _write_feature_manifest(manifest, db, counts)
    c_b_sha = _write_c_b_result(c_b)
    repo_root = _init_git_repo(tmp_path)
    return db, manifest, c_b, c_b_sha, repo_root


def test_c_c2_loader_hard_rejects_test(tmp_path: Path) -> None:
    db, _, _, _, _ = _fixture(tmp_path)
    con = duckdb.connect(str(db), read_only=True)
    try:
        with pytest.raises(CalibrationGateError, match="test is forbidden"):
            _load_segments(con, ("test",), include_evaluation_fields=True)
    finally:
        con.close()


def test_c_c2_rejects_noncanonical_model_selection_result(tmp_path: Path) -> None:
    db, manifest, c_b, _, repo_root = _fixture(tmp_path)

    with pytest.raises(CalibrationGateError, match="Model-selection result SHA mismatch"):
        run_calibration_gate(
            feature_database_path=db,
            feature_manifest_path=manifest,
            model_selection_result_path=c_b,
            output_path=tmp_path / "gate.json",
            repo_root=repo_root,
            expected_c_b_sha256="0" * 64,
            bootstrap_iterations=100,
        )


def test_c_c2_runs_gate_without_test_access_and_refuses_overwrite(
    tmp_path: Path,
) -> None:
    db, manifest, c_b, c_b_sha, repo_root = _fixture(tmp_path)
    output = tmp_path / "gate.json"

    result = run_calibration_gate(
        feature_database_path=db,
        feature_manifest_path=manifest,
        model_selection_result_path=c_b,
        output_path=output,
        repo_root=repo_root,
        expected_c_b_sha256=c_b_sha,
        bootstrap_iterations=100,
    )

    assert result["c_b_result_sha256"] == c_b_sha
    assert result["information_boundary"] == {
        "refit_segments": ["train", "model_selection"],
        "gate_segment": "calibration_gate",
        "test_read": False,
    }
    assert result["refit"]["rows"] == 300
    assert result["calibration_gate"]["rows"] == 60
    assert result["selected_gbdt"]["id"] == "gbdt-small"
    assert result["selected_gbdt"]["pr_auc_bootstrap_95"]["iterations"] == 100
    assert "convergence_warning" in result["baselines"]["regularized_logistic"]
    assert "n_iter" in result["baselines"]["regularized_logistic"]
    assert result["calibration"]["diagnostic_scope"].startswith("calibrator fit")
    assert isinstance(result["gate_decision"]["passed"], bool)
    assert result["test_authorized"] == result["gate_decision"]["passed"]

    with pytest.raises(CalibrationGateError, match="already exists"):
        run_calibration_gate(
            feature_database_path=db,
            feature_manifest_path=manifest,
            model_selection_result_path=c_b,
            output_path=output,
            repo_root=repo_root,
            expected_c_b_sha256=c_b_sha,
            bootstrap_iterations=100,
        )


def test_test_label_changes_cannot_change_gate_metrics(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()

    first = _fixture(first_root, flip_test_labels=False)
    second = _fixture(second_root, flip_test_labels=True)

    first_result = run_calibration_gate(
        feature_database_path=first[0],
        feature_manifest_path=first[1],
        model_selection_result_path=first[2],
        output_path=first_root / "gate.json",
        repo_root=first[4],
        expected_c_b_sha256=first[3],
        bootstrap_iterations=100,
    )
    second_result = run_calibration_gate(
        feature_database_path=second[0],
        feature_manifest_path=second[1],
        model_selection_result_path=second[2],
        output_path=second_root / "gate.json",
        repo_root=second[4],
        expected_c_b_sha256=second[3],
        bootstrap_iterations=100,
    )

    assert first_result["refit"] == second_result["refit"]
    assert first_result["calibration_gate"] == second_result["calibration_gate"]
    assert first_result["baselines"]["prevalence"] == second_result["baselines"]["prevalence"]
    assert (
        first_result["baselines"]["behavioral_heuristic"]
        == second_result["baselines"]["behavioral_heuristic"]
    )

    first_logistic = dict(first_result["baselines"]["regularized_logistic"])
    second_logistic = dict(second_result["baselines"]["regularized_logistic"])
    first_logistic.pop("fit_seconds")
    second_logistic.pop("fit_seconds")
    assert first_logistic == second_logistic

    first_gbdt = dict(first_result["selected_gbdt"])
    second_gbdt = dict(second_result["selected_gbdt"])
    first_gbdt.pop("fit_seconds")
    second_gbdt.pop("fit_seconds")
    assert first_gbdt == second_gbdt

    assert first_result["calibration"] == second_result["calibration"]
    assert first_result["gate_decision"] == second_result["gate_decision"]
    assert first_result["test_authorized"] == second_result["test_authorized"]
