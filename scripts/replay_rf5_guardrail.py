"""Deterministic RF5 replay guardrail harness.

This script uses public/non-held-out development surfaces only. It produces
machine-readable evidence for RF5 no-regression checks and for RF5 component
coverage when the authoritative detector is treated as silent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

# Support both:
#   python -m scripts.replay_rf5_guardrail ...
#   python scripts/replay_rf5_guardrail.py ...
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.interpretation import InterpretationService
from app.unauthorized_signals import is_explicit_unauthorized_assertion

try:  # RF5 does not exist on older/main checkouts.
    from app.rf5_stage1 import (
        rf5_stage1_failure_to_pay_cleanup_candidate,
        rf5_stage1_findings,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised only on pre-RF5 branches.
    rf5_stage1_findings = None  # type: ignore[assignment]
    rf5_stage1_failure_to_pay_cleanup_candidate = None  # type: ignore[assignment]


CaseBucket = Literal[
    "positive_preserve",
    "benign_preserve",
    "rf5_positive_control",
    "rf5_gain_control",
    "ftp2_cleanup_control",
]


@dataclass(frozen=True, slots=True)
class ReplayCase:
    case_id: str
    bucket: CaseBucket
    source: str
    message: str
    expected_main_escalates: bool | None
    expected_current_escalates: bool
    rationale: str
    expected_rf5_families: tuple[str, ...] = ()
    expect_rf5_component_gain: bool = False
    expect_ftp2_cleanup_candidate: bool | None = None


# Sources are public/non-held-out tests, RF5 repair controls, and bounded synthetic
# component controls with no customer identity, transaction reference, account
# reference, production data, or held-out wording.
REPLAY_CASES: tuple[ReplayCase, ...] = (
    ReplayCase(
        "rf1u-positive-fraud-characterization-es-001",
        "positive_preserve",
        "tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        "Esto fue un consumo fraudulento con la tarjeta débito.",
        True,
        True,
        "Existing public RF1U fraud-characterization positive must not be lost.",
        ("m4_scam_social_engineering_activity",),
    ),
    ReplayCase(
        "rf1u-positive-non-recognition-pt-001",
        "positive_preserve",
        "tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        "Não reconheço este movimento de cinquenta reais.",
        True,
        True,
        "Existing RF1U non-recognition positive must not be lost.",
    ),
    ReplayCase(
        "rf1u-positive-third-party-es-001",
        "positive_preserve",
        "tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        "Ese pago lo realizó alguien más, y no yo.",
        True,
        True,
        "Existing RF1U third-party-authorship positive must not be lost.",
    ),
    ReplayCase(
        "rf5-benign-resolved-fraud-es-001",
        "benign_preserve",
        "tests/test_rf1u_product_repair.py::_NAMED_NEGATIVES and RF5 repair-2 validation",
        "Tenía un pago fraudulento pero ya lo reversaron.",
        False,
        False,
        "Resolved/reversed fraud mention must remain benign.",
    ),
    ReplayCase(
        "rf5-benign-prevention-question-es-001",
        "benign_preserve",
        "tests/test_rf1u_product_repair.py::_NAMED_NEGATIVES and RF5 repair-2 validation",
        "¿Cómo detectar un consumo fraudulento?",
        False,
        False,
        "Prevention/education question must remain benign.",
    ),
    ReplayCase(
        "rf5-benign-hypothetical-pt-001",
        "benign_preserve",
        "tests/test_rf3_product_repair.py and RF5 repair-2 validation",
        "Caso alguém use meu cartão sem minha autorização, o que faço?",
        False,
        False,
        "Hypothetical/procedural Portuguese question must remain benign.",
    ),
    ReplayCase(
        "rf5-benign-lawful-cause-es-001",
        "benign_preserve",
        "tests/test_rf4_failsafe_floor.py and RF5 repair-2 validation",
        "La DIAN me retuvo plata de la cuenta sin mi autorización por un impuesto pendiente.",
        False,
        False,
        "Lawful tax-authority withholding must remain benign.",
    ),
    ReplayCase(
        "rf1u-benign-authorized-transfer-es-001",
        "benign_preserve",
        "tests/test_rf1u_product_repair.py::_BENIGN",
        "La transferencia la hizo otra persona con mi autorización.",
        False,
        False,
        "Authorized third-party transfer must remain benign.",
    ),
    ReplayCase(
        "rf5-control-bloqueou-m1-pt-001",
        "rf5_positive_control",
        "tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        "O banco bloqueou o cartão, mas há um pagamento na conta sem minha permissão.",
        None,
        True,
        "The word 'bloqueou' must not suppress a true positive.",
        ("m1_no_authorization_activity",),
        True,
    ),
    ReplayCase(
        "rf5-control-retuvo-m4-es-001",
        "rf5_positive_control",
        "tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        "La tienda retuvo el pedido, pero hay un pago fraudulento en mi cuenta.",
        None,
        True,
        "The word 'retuvo' must not suppress a true M4 positive.",
        ("m4_scam_social_engineering_activity",),
        True,
    ),
    ReplayCase(
        "rf5-gain-m1-silent-detector-es-001",
        "rf5_gain_control",
        "RF5 D1-D3 non-held-out synthetic component control",
        "Tengo un cobro en la cuenta sin mi permiso.",
        False,
        True,
        "M1 RF5 component control when the authoritative detector is silent.",
        ("m1_no_authorization_activity",),
        True,
    ),
    ReplayCase(
        "rf5-gain-m2-silent-detector-es-001",
        "rf5_gain_control",
        "RF5 D1-D3 non-held-out synthetic component control",
        "Jamás reconocí 83.000 pesos en el extracto.",
        False,
        True,
        "M2 RF5 component control when the authoritative detector is silent.",
        ("m2_money_reference_disowning",),
        True,
    ),
    ReplayCase(
        "rf5-gain-m4-silent-detector-es-001",
        "rf5_gain_control",
        "RF5 D1-D3 non-held-out synthetic component control",
        "Me engañaron por mensaje y apareció un avance en la cuenta.",
        False,
        True,
        "M4 RF5 component control when the authoritative detector is silent.",
        ("m4_scam_social_engineering_activity",),
        True,
    ),
    ReplayCase(
        "ftp2-cleanup-benign-es-001",
        "ftp2_cleanup_control",
        "tests/test_rf5_stage1.py::test_ordinary_failure_to_pay_is_cleanup_candidate_not_raise",
        "Se me olvidó pagar la cuota del préstamo.",
        False,
        False,
        "FTP-2 cleanup candidate must not become an escalation.",
        expect_ftp2_cleanup_candidate=True,
    ),
    ReplayCase(
        "ftp2-positive-loss-guard-es-001",
        "ftp2_cleanup_control",
        "tests/test_rf5_stage1.py::test_failure_to_pay_with_positive_guard_is_not_cleanup_candidate",
        "No reconozco este cargo por 120 pesos y no pagué la cuota.",
        True,
        True,
        "FTP-2 must not mark a positive unauthorized case as cleanup-removable.",
        ("m2_money_reference_disowning",),
        expect_ftp2_cleanup_candidate=False,
    ),
)


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _rf5_families(message: str) -> list[str]:
    if rf5_stage1_findings is None:
        return []
    return sorted(
        {
            finding.family
            for finding in rf5_stage1_findings(message)
            if finding.effect == "raise"
        }
    )


def _ftp2_cleanup_candidate(message: str) -> bool:
    if rf5_stage1_failure_to_pay_cleanup_candidate is None:
        return False
    return bool(rf5_stage1_failure_to_pay_cleanup_candidate(message))


def evaluate_case(case: ReplayCase) -> dict[str, Any]:
    unauthorized = is_explicit_unauthorized_assertion(case.message)
    failsafe_floor = InterpretationService._failsafe_floor(
        case.message,
        unauthorized=unauthorized,
    )
    silent_detector_failsafe_floor = InterpretationService._failsafe_floor(
        case.message,
        unauthorized=False,
    )
    would_escalate = bool(unauthorized or failsafe_floor)
    rf5_families = _rf5_families(case.message)
    return {
        "case_id": case.case_id,
        "bucket": case.bucket,
        "source": case.source,
        "message": case.message,
        "expected_main_escalates": case.expected_main_escalates,
        "expected_current_escalates": case.expected_current_escalates,
        "expected_rf5_families": list(case.expected_rf5_families),
        "expect_rf5_component_gain": case.expect_rf5_component_gain,
        "expect_ftp2_cleanup_candidate": case.expect_ftp2_cleanup_candidate,
        "rationale": case.rationale,
        "unauthorized_activity_asserted": unauthorized,
        "failsafe_floor": failsafe_floor,
        "silent_detector_failsafe_floor": silent_detector_failsafe_floor,
        "would_escalate": would_escalate,
        "route_policy_would_escalate": would_escalate,
        "rf5_raise_families": rf5_families,
        "ftp2_cleanup_candidate": _ftp2_cleanup_candidate(case.message),
        "rf5_component_gain": bool(
            case.expect_rf5_component_gain
            and silent_detector_failsafe_floor
            and rf5_families
        ),
    }


def _baseline_by_case_id(baseline_json: Path | None) -> dict[str, bool]:
    if baseline_json is None:
        return {}
    payload = json.loads(baseline_json.read_text(encoding="utf-8"))
    return {
        str(case["case_id"]): bool(case["would_escalate"])
        for case in payload.get("cases", [])
    }


def _family_table(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    families = (
        "m1_no_authorization_activity",
        "m2_money_reference_disowning",
        "m4_scam_social_engineering_activity",
    )
    table = {
        family: {
            "case_count": 0,
            "silent_detector_gain_count": 0,
            "actual_route_escalate_count": 0,
        }
        for family in families
    }
    for result in results:
        result_families = set(result["rf5_raise_families"])
        for family in families:
            if family not in result_families:
                continue
            table[family]["case_count"] += 1
            if result["rf5_component_gain"]:
                table[family]["silent_detector_gain_count"] += 1
            if result["route_policy_would_escalate"]:
                table[family]["actual_route_escalate_count"] += 1
    return table


def build_report(*, baseline_json: Path | None = None) -> dict[str, Any]:
    baseline_results = _baseline_by_case_id(baseline_json)
    case_by_id = {case.case_id: case for case in REPLAY_CASES}
    results = [evaluate_case(case) for case in REPLAY_CASES]

    positive_loss: list[str] = []
    benign_removal_regression: list[str] = []
    expected_rf5_gain: list[str] = []
    rf5_component_gain: list[str] = []
    current_expectation_failures: list[str] = []
    rf5_family_expectation_failures: list[str] = []
    ftp2_expectation_failures: list[str] = []
    changed_from_baseline_json: list[dict[str, Any]] = []

    for result in results:
        case = case_by_id[str(result["case_id"])]
        current = bool(result["would_escalate"])
        if current != case.expected_current_escalates:
            current_expectation_failures.append(case.case_id)

        expected_families = set(case.expected_rf5_families)
        actual_families = set(result["rf5_raise_families"])
        if expected_families and not expected_families.issubset(actual_families):
            rf5_family_expectation_failures.append(case.case_id)

        if (
            case.expect_ftp2_cleanup_candidate is not None
            and bool(result["ftp2_cleanup_candidate"]) != case.expect_ftp2_cleanup_candidate
        ):
            ftp2_expectation_failures.append(case.case_id)

        baseline_expected = case.expected_main_escalates
        if baseline_expected is True and current is False:
            positive_loss.append(case.case_id)
        if baseline_expected is False and current is True and case.bucket == "benign_preserve":
            benign_removal_regression.append(case.case_id)
        if baseline_expected is False and current is True and case.expected_current_escalates:
            expected_rf5_gain.append(case.case_id)
        if result["rf5_component_gain"]:
            rf5_component_gain.append(case.case_id)

        if case.case_id in baseline_results:
            baseline_current = baseline_results[case.case_id]
            if baseline_current != current:
                changed_from_baseline_json.append(
                    {
                        "case_id": case.case_id,
                        "baseline_would_escalate": baseline_current,
                        "current_would_escalate": current,
                        "bucket": case.bucket,
                    }
                )

    summary = {
        "case_count": len(results),
        "positive_preserve_count": sum(c.bucket == "positive_preserve" for c in REPLAY_CASES),
        "benign_preserve_count": sum(c.bucket == "benign_preserve" for c in REPLAY_CASES),
        "rf5_positive_control_count": sum(c.bucket == "rf5_positive_control" for c in REPLAY_CASES),
        "rf5_gain_control_count": sum(c.bucket == "rf5_gain_control" for c in REPLAY_CASES),
        "ftp2_cleanup_control_count": sum(c.bucket == "ftp2_cleanup_control" for c in REPLAY_CASES),
        "positive_loss_count": len(positive_loss),
        "benign_removal_regression_count": len(benign_removal_regression),
        "current_expectation_failure_count": len(current_expectation_failures),
        "rf5_family_expectation_failure_count": len(rf5_family_expectation_failures),
        "ftp2_expectation_failure_count": len(ftp2_expectation_failures),
        "changed_from_baseline_json_count": len(changed_from_baseline_json),
        "expected_rf5_gain_count": len(expected_rf5_gain),
        "rf5_component_gain_count": len(rf5_component_gain),
    }
    return {
        "schema_version": "rf5-replay-guardrail-v2",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "baseline_json": str(baseline_json) if baseline_json is not None else None,
        "replay_surfaces": {
            "direct_detector": True,
            "failsafe_floor": True,
            "silent_detector_rf5_component": True,
            "route_policy_escalation_proxy": "unauthorized_activity_asserted or failsafe_floor",
            "interpret_to_route_policy": False,
            "interpret_to_route_policy_blocker": (
                "The minimal harness does not instantiate demo app state or runtime stores; "
                "active-route replay is represented by the deterministic predicate "
                "that supplies route-policy escalation input."
            ),
            "ftp2_cleanup_candidate": True,
        },
        "summary": summary,
        "family_table": _family_table(results),
        "positive_loss_case_ids": positive_loss,
        "benign_removal_regression_case_ids": benign_removal_regression,
        "expected_rf5_gain_case_ids": expected_rf5_gain,
        "rf5_component_gain_case_ids": rf5_component_gain,
        "current_expectation_failure_case_ids": current_expectation_failures,
        "rf5_family_expectation_failure_case_ids": rf5_family_expectation_failures,
        "ftp2_expectation_failure_case_ids": ftp2_expectation_failures,
        "changed_from_baseline_json": changed_from_baseline_json,
        "cases": results,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic RF5 replay guardrail on non-held-out cases.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for machine-readable replay output.",
    )
    parser.add_argument(
        "--baseline-json",
        type=Path,
        help="Optional prior output to compare by case_id.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Return exit code 0 even when guardrail failures are detected.",
    )
    args = parser.parse_args(argv)

    report = build_report(baseline_json=args.baseline_json)
    if args.json_output is not None:
        _write_json(args.json_output, report)

    summary = report["summary"]
    print("RF5 replay guardrail")
    print(f"cases: {summary['case_count']}")
    print(f"positive_loss: {summary['positive_loss_count']}")
    print(f"benign_removal_regression: {summary['benign_removal_regression_count']}")
    print(f"current_expectation_failures: {summary['current_expectation_failure_count']}")
    print(f"rf5_family_expectation_failures: {summary['rf5_family_expectation_failure_count']}")
    print(f"ftp2_expectation_failures: {summary['ftp2_expectation_failure_count']}")
    print(f"rf5_component_gain: {summary['rf5_component_gain_count']}")
    print(f"changed_from_baseline_json: {summary['changed_from_baseline_json_count']}")

    failed = bool(
        summary["positive_loss_count"]
        or summary["benign_removal_regression_count"]
        or summary["current_expectation_failure_count"]
        or summary["rf5_family_expectation_failure_count"]
        or summary["ftp2_expectation_failure_count"]
    )
    if failed:
        print("guardrail: FAIL")
        return 0 if args.allow_failures else 1
    print("guardrail: PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
