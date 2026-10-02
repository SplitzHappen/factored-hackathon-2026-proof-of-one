from __future__ import annotations

import json
import subprocess
import sys

from scripts.replay_rf5_guardrail import REPLAY_CASES, build_report, main


def test_rf5_replay_guardrail_cases_are_named_and_unique() -> None:
    case_ids = [case.case_id for case in REPLAY_CASES]

    assert case_ids
    assert len(case_ids) == len(set(case_ids))
    assert {case.bucket for case in REPLAY_CASES} == {
        "positive_preserve",
        "benign_preserve",
        "rf5_positive_control",
        "rf5_gain_control",
        "ftp2_cleanup_control",
    }


def test_rf5_replay_guardrail_passes_current_checkout() -> None:
    report = build_report()
    summary = report["summary"]

    assert summary["case_count"] == len(REPLAY_CASES)
    assert summary["positive_preserve_count"] > 0
    assert summary["benign_preserve_count"] > 0
    assert summary["rf5_positive_control_count"] > 0
    assert summary["rf5_gain_control_count"] >= 3
    assert summary["ftp2_cleanup_control_count"] >= 2
    assert summary["positive_loss_count"] == 0
    assert summary["benign_removal_regression_count"] == 0
    assert summary["current_expectation_failure_count"] == 0
    assert summary["rf5_family_expectation_failure_count"] == 0
    assert summary["ftp2_expectation_failure_count"] == 0
    assert summary["rf5_component_gain_count"] >= 3

    family_table = report["family_table"]
    assert family_table["m1_no_authorization_activity"]["case_count"] > 0
    assert family_table["m2_money_reference_disowning"]["case_count"] > 0
    assert family_table["m4_scam_social_engineering_activity"]["case_count"] > 0
    assert report["replay_surfaces"]["ftp2_cleanup_candidate"] is True


def test_rf5_replay_guardrail_writes_json_output(tmp_path) -> None:
    output = tmp_path / "rf5_replay.json"

    assert main(["--json-output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rf5-replay-guardrail-v2"
    assert payload["summary"]["case_count"] == len(REPLAY_CASES)
    assert payload["summary"]["positive_loss_count"] == 0
    assert payload["summary"]["benign_removal_regression_count"] == 0
    assert payload["summary"]["current_expectation_failure_count"] == 0
    assert payload["summary"]["rf5_family_expectation_failure_count"] == 0
    assert payload["summary"]["ftp2_expectation_failure_count"] == 0


def test_rf5_replay_guardrail_file_path_invocation_writes_json(tmp_path) -> None:
    output = tmp_path / "rf5_replay_file_path.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/replay_rf5_guardrail.py",
            "--json-output",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "guardrail: PASS" in completed.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rf5-replay-guardrail-v2"
    assert payload["summary"]["rf5_component_gain_count"] >= 3
