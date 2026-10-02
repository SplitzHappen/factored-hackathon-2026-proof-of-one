from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.replay_rf5_guardrail import REPLAY_CASES, build_report, main


def test_rf5_replay_guardrail_cases_are_named_and_unique() -> None:
    case_ids = [case.case_id for case in REPLAY_CASES]

    assert case_ids
    assert len(case_ids) == len(set(case_ids))
    assert {
        "positive_preserve",
        "benign_preserve",
        "rf5_gain_control",
        "rf5_component_control",
        "ftp2_control",
        "ftp2_limitation",
    }.issubset({case.bucket for case in REPLAY_CASES})
    assert {"m1", "m2", "m4", "ftp2"}.issubset(
        {case.family for case in REPLAY_CASES}
    )


def test_rf5_replay_guardrail_passes_current_checkout() -> None:
    report = build_report()
    summary = report["summary"]

    assert summary["case_count"] == len(REPLAY_CASES)
    assert summary["positive_preserve_count"] > 0
    assert summary["benign_preserve_count"] > 0
    assert summary["rf5_gain_control_count"] == 1
    assert summary["rf5_component_control_count"] > 0
    assert summary["ftp2_control_count"] >= 2
    assert summary["ftp2_limitation_count"] == 1
    assert summary["positive_loss_count"] == 0
    assert summary["benign_removal_regression_count"] == 0
    assert summary["current_expectation_failure_count"] == 0
    assert summary["rf5_family_expectation_failure_count"] == 0
    assert summary["ftp2_expectation_failure_count"] == 0
    assert summary["full_path_expectation_failure_count"] == 0
    assert summary["predicate_full_path_disagreement_count"] == 0
    assert summary["hypothetical_positive_loss_if_wired_count"] == 1

    gain_case = next(
        case
        for case in report["cases"]
        if case["case_id"] == "rf5-gain-m4-silent-detector-es-001"
    )
    assert gain_case["would_escalate"] is True
    assert gain_case["unauthorized_activity_asserted"] is False
    assert gain_case["rf4_floor"] is False
    assert gain_case["rf5_only_component_gain"] is True
    assert gain_case["full_path_interpretation_status"] == "verified"
    assert gain_case["full_path_route"] == "ESCALATE"
    assert gain_case["full_path_escalates"] is True
    assert gain_case["route_policy_would_escalate"] is True
    assert gain_case["full_path_reason_codes"] == [
        "possible_unauthorized_activity"
    ]

    family_rows = report["plan_tables"]["per_family_replay_coverage"]
    assert {"m1", "m2", "m4"}.issubset({row["family"] for row in family_rows})
    ftp2_rows = report["plan_tables"]["ftp2_cleanup_candidate_cases"]
    assert len(ftp2_rows) >= 3
    assert any(row["ftp2_cleanup_candidate"] for row in ftp2_rows)
    assert any("positive_loss_guard" in row["ftp2_blocked_by"] for row in ftp2_rows)
    assert any(row["hypothetical_positive_loss_if_wired"] for row in ftp2_rows)
    assert report["replay_surfaces"]["interpret_to_route_policy"] is True
    assert (
        report["replay_surfaces"]["interpretation_provider"]
        == "DeterministicDemoInterpretationProvider"
    )
    assert report["replay_surfaces"]["synthetic_bank"] is True
    assert report["replay_surfaces"]["held_out_material"] is False
    assert report["replay_surfaces"]["live_provider"] is False

    benign = next(
        case
        for case in report["cases"]
        if case["case_id"] == "rf5-benign-prevention-question-es-001"
    )
    assert benign["full_path_route"] != "ESCALATE"
    assert benign["full_path_escalates"] is False


def test_rf5_replay_guardrail_writes_json_output(tmp_path) -> None:
    output = tmp_path / "rf5_replay.json"

    assert main(["--json-output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rf5-replay-guardrail-v5"
    assert payload["summary"]["case_count"] == len(REPLAY_CASES)
    assert payload["summary"]["positive_loss_count"] == 0
    assert payload["summary"]["benign_removal_regression_count"] == 0
    assert payload["summary"]["current_expectation_failure_count"] == 0
    assert payload["summary"]["ftp2_expectation_failure_count"] == 0
    assert payload["summary"]["full_path_expectation_failure_count"] == 0
    assert payload["summary"]["predicate_full_path_disagreement_count"] == 0
    assert payload["summary"]["hypothetical_positive_loss_if_wired_count"] == 1
    assert "plan_tables" in payload
    assert "measured_attribution_counts" in payload


def test_rf5_replay_guardrail_file_path_invocation_from_other_cwd(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "replay_rf5_guardrail.py"
    output = tmp_path / "rf5_replay_file_path.json"

    completed = subprocess.run(
        [sys.executable, str(script), "--json-output", str(output)],
        cwd=tmp_path,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "guardrail: PASS" in completed.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rf5-replay-guardrail-v5"


def test_rf5_replay_guardrail_measured_baseline_attribution(tmp_path) -> None:
    # Simulate the measured main baseline for the one intended RF5-only route gain:
    # main is silent, current PR escalates through the RF5 component while the
    # authoritative detector and RF4 floor are silent.
    baseline = build_report()
    for case in baseline["cases"]:
        if case["case_id"] == "rf5-gain-m4-silent-detector-es-001":
            case["would_escalate"] = False
            case["route_policy_would_escalate"] = False

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

    report = build_report(baseline_json=baseline_path)

    assert report["summary"]["changed_from_baseline_json_count"] == 1
    assert report["summary"]["measured_rf5_only_gain_count"] == 1
    assert report["measured_attribution_case_ids"]["rf5_only_component_gain"] == [
        "rf5-gain-m4-silent-detector-es-001"
    ]
    assert report["changed_from_baseline_json"] == [
        {
            "case_id": "rf5-gain-m4-silent-detector-es-001",
            "baseline_would_escalate": False,
            "current_would_escalate": True,
            "bucket": "rf5_gain_control",
            "classification": "rf5_only_component_gain",
        }
    ]


def test_rf5_replay_guardrail_records_full_interpret_to_policy_evidence() -> None:
    report = build_report()

    assert report["replay_surfaces"]["interpret_to_route_policy"] is True
    assert report["summary"]["full_path_expectation_failure_count"] == 0
    assert report["summary"]["predicate_full_path_disagreement_count"] == 0

    assert len(report["cases"]) == len(REPLAY_CASES)
    for case in report["cases"]:
        assert case["full_path_interpretation_status"] in {
            "verified",
            "safe_fallback",
        }
        assert case["full_path_route"] in {
            "ANSWER",
            "CLARIFY",
            "ABSTAIN",
            "ESCALATE",
        }
        assert isinstance(case["full_path_reason_codes"], list)
        assert (
            case["route_policy_would_escalate"]
            is case["full_path_escalates"]
        )


def test_rf5_replay_guardrail_keeps_ftp2_unwired_in_full_path() -> None:
    report = build_report()
    limitation = next(
        case
        for case in report["cases"]
        if case["case_id"] == "rf5-ftp2-gap-no-la-autorice-es-001"
    )

    assert limitation["hypothetical_positive_loss_if_wired"] is True
    assert limitation["full_path_route"] == "ESCALATE"
    assert limitation["full_path_escalates"] is True

    residuals = report["plan_tables"]["residual_active_route_limitations"]
    ftp2 = next(row for row in residuals if row["surface"] == "ftp2_cleanup_activation")
    assert ftp2["implemented"] is False
