from __future__ import annotations

import json

from scripts.replay_rf5_guardrail import REPLAY_CASES, build_report, main


def test_rf5_replay_guardrail_cases_are_named_and_unique() -> None:
    case_ids = [case.case_id for case in REPLAY_CASES]

    assert case_ids
    assert len(case_ids) == len(set(case_ids))
    assert {case.bucket for case in REPLAY_CASES} == {
        "positive_preserve",
        "benign_preserve",
        "rf5_positive_control",
    }


def test_rf5_replay_guardrail_passes_current_checkout() -> None:
    report = build_report()
    summary = report["summary"]

    assert summary["case_count"] == len(REPLAY_CASES)
    assert summary["positive_preserve_count"] > 0
    assert summary["benign_preserve_count"] > 0
    assert summary["rf5_positive_control_count"] > 0
    assert summary["positive_loss_count"] == 0
    assert summary["benign_removal_regression_count"] == 0
    assert summary["current_expectation_failure_count"] == 0


def test_rf5_replay_guardrail_writes_json_output(tmp_path) -> None:
    output = tmp_path / "rf5_replay.json"

    assert main(["--json-output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rf5-replay-guardrail-v1"
    assert payload["summary"]["case_count"] == len(REPLAY_CASES)
    assert payload["summary"]["positive_loss_count"] == 0
    assert payload["summary"]["benign_removal_regression_count"] == 0
    assert payload["summary"]["current_expectation_failure_count"] == 0
