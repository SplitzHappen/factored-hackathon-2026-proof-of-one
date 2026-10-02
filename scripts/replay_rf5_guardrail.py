"""Deterministic RF5 replay guardrail harness.

This script uses public/non-held-out development surfaces only. It produces
machine-readable evidence for RF5 no-regression checks, measured-baseline
attribution, and replay-plan coverage tables without touching held-out case
content, live providers, semantic providers, hosted CI, or production data.

Default behavior evaluates the current checkout. When --baseline-json is supplied,
the script classifies measured outcome changes by case_id. That measured baseline
comparison is the only source of route-level RF5-gain attribution.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

# File-path invocation puts scripts/ on sys.path. Add the repository root before
# importing app modules so both
#   python scripts/replay_rf5_guardrail.py
# and
#   python -m scripts.replay_rf5_guardrail
# work from any current working directory.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.failsafe_escalation import is_failsafe_escalation
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
    "rf5_gain_control",
    "rf5_component_control",
    "ftp2_control",
]
Family = Literal["m1", "m2", "m4", "ftp2", "legacy"]


@dataclass(frozen=True, slots=True)
class ReplayCase:
    case_id: str
    bucket: CaseBucket
    family: Family
    language: str
    source: str
    message: str
    expected_current_escalates: bool
    expected_main_escalates: bool | None
    expected_rf5_families: tuple[str, ...]
    expected_ftp2_cleanup_candidate: bool | None
    rationale: str


# Case sources are public/non-held-out tests and synthetic component controls.
# RF5 route-gain attribution is measured only with --baseline-json; it is not
# inferred from expected_main_escalates labels.
REPLAY_CASES: tuple[ReplayCase, ...] = (
    ReplayCase(
        case_id="rf1u-positive-fraud-characterization-es-001",
        bucket="positive_preserve",
        family="m4",
        language="es",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Esto fue un consumo fraudulento con la tarjeta débito.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        expected_rf5_families=("m4_scam_social_engineering_activity",),
        expected_ftp2_cleanup_candidate=False,
        rationale="Existing public RF1U fraud-characterization positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf1u-positive-non-recognition-pt-001",
        bucket="positive_preserve",
        family="legacy",
        language="pt",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Não reconheço este movimento de cinquenta reais.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Existing RF1U non-recognition positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf5-benign-resolved-fraud-es-001",
        bucket="benign_preserve",
        family="m4",
        language="es",
        source="tests/test_rf1u_product_repair.py::_NAMED_NEGATIVES and RF5 repair validation",
        message="Tenía un pago fraudulento pero ya lo reversaron.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Resolved/reversed fraud mention must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-prevention-question-es-001",
        bucket="benign_preserve",
        family="m4",
        language="es",
        source="tests/test_rf1u_product_repair.py::_NAMED_NEGATIVES and RF5 repair validation",
        message="¿Cómo detectar un consumo fraudulento?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Prevention/education question must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-hypothetical-pt-001",
        bucket="benign_preserve",
        family="m1",
        language="pt",
        source="tests/test_rf3_product_repair.py and RF5 repair validation",
        message="Caso alguém use meu cartão sem minha autorização, o que faço?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Hypothetical/procedural Portuguese question must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-lawful-cause-es-001",
        bucket="benign_preserve",
        family="m1",
        language="es",
        source="tests/test_rf4_failsafe_floor.py and RF5 repair validation",
        message="La DIAN me retuvo plata de la cuenta sin mi autorización por un impuesto pendiente.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Lawful tax-authority withholding must remain benign.",
    ),
    ReplayCase(
        case_id="rf1u-benign-status-es-001",
        bucket="benign_preserve",
        family="legacy",
        language="es",
        source="tests/test_rf1u_product_repair.py::_BENIGN",
        message="¿Cuál es el estado de mi pago de ayer?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Ordinary payment-status request must remain benign.",
    ),
    ReplayCase(
        case_id="rf1u-benign-authorized-transfer-es-001",
        bucket="benign_preserve",
        family="legacy",
        language="es",
        source="tests/test_rf1u_product_repair.py::_BENIGN",
        message="La transferencia la hizo otra persona con mi autorización.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale="Authorized third-party transfer must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-gain-m4-silent-detector-es-001",
        bucket="rf5_gain_control",
        family="m4",
        language="es",
        source="RF5 public synthetic M4 component-gain control",
        message="Me engañaron en una llamada y luego hicieron un pago desde mi cuenta.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        expected_rf5_families=("m4_scam_social_engineering_activity",),
        expected_ftp2_cleanup_candidate=False,
        rationale=(
            "RF5 M4 should add a route-level raise only when the authoritative "
            "detector and RF4 floor are silent; measured baseline decides attribution."
        ),
    ),
    ReplayCase(
        case_id="rf5-component-m1-detector-handled-es-001",
        bucket="rf5_component_control",
        family="m1",
        language="es",
        source="tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        message="Sí, tengo un débito en mi cuenta sin mi autorización.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        expected_rf5_families=("m1_no_authorization_activity",),
        expected_ftp2_cleanup_candidate=False,
        rationale=(
            "M1 component coverage. This is not labeled as a route gain because "
            "the authoritative detector may already escalate it."
        ),
    ),
    ReplayCase(
        case_id="rf5-component-m2-detector-handled-es-001",
        bucket="rf5_component_control",
        family="m2",
        language="es",
        source="RF5 public synthetic M2 component control",
        message="No reconozco un pago de 50 dólares en mi cuenta.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        expected_rf5_families=("m2_money_reference_disowning",),
        expected_ftp2_cleanup_candidate=False,
        rationale=(
            "M2 component coverage. Route-level gain must be measured and must "
            "not be inferred from the component firing."
        ),
    ),
    ReplayCase(
        case_id="rf5-component-m2-detector-handled-pt-001",
        bucket="rf5_component_control",
        family="m2",
        language="pt",
        source="RF5 public synthetic M2 component control",
        message="Não reconheço um pagamento de 75 reais na minha conta.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        expected_rf5_families=("m2_money_reference_disowning",),
        expected_ftp2_cleanup_candidate=False,
        rationale=(
            "Portuguese M2 component coverage. Route-level gain must be measured "
            "and must not be inferred from the component firing."
        ),
    ),
    ReplayCase(
        case_id="rf5-ftp2-cleanup-benign-es-001",
        bucket="ftp2_control",
        family="ftp2",
        language="es",
        source="RF5 public synthetic FTP-2 cleanup-candidate control",
        message="No pude pagar la cuota del préstamo.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=True,
        rationale="FTP-2 cleanup candidate should remain non-escalating because FTP-2 is unwired.",
    ),
    ReplayCase(
        case_id="rf5-ftp2-positive-loss-guard-es-001",
        bucket="ftp2_control",
        family="ftp2",
        language="es",
        source="RF5 public synthetic FTP-2 positive-loss guard control",
        message="No pagué esta cuota porque no la autoricé.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        expected_rf5_families=(),
        expected_ftp2_cleanup_candidate=False,
        rationale=(
            "A positive-loss guard should prevent FTP-2 cleanup candidacy and "
            "the positive report must remain escalated."
        ),
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


def _rf5_findings(message: str) -> tuple[Any, ...]:
    if rf5_stage1_findings is None:
        return ()
    return tuple(rf5_stage1_findings(message))


def _rf5_raise_families(message: str) -> list[str]:
    return sorted(
        {
            str(finding.family)
            for finding in _rf5_findings(message)
            if finding.effect == "raise"
        }
    )


def _ftp2_detail(message: str) -> dict[str, Any]:
    findings = [
        finding
        for finding in _rf5_findings(message)
        if finding.family == "ftp2_failure_to_pay_cleanup_candidate"
    ]
    cleanup_candidate = (
        bool(rf5_stage1_failure_to_pay_cleanup_candidate(message))
        if rf5_stage1_failure_to_pay_cleanup_candidate is not None
        else False
    )
    return {
        "ftp2_cleanup_candidate": cleanup_candidate,
        "ftp2_finding_count": len(findings),
        "ftp2_blocked_by": sorted(
            {
                str(finding.blocked_by)
                for finding in findings
                if finding.blocked_by is not None
            }
        ),
    }


def evaluate_case(case: ReplayCase) -> dict[str, Any]:
    unauthorized = is_explicit_unauthorized_assertion(case.message)
    rf4_floor = is_failsafe_escalation(case.message)
    failsafe_floor = InterpretationService._failsafe_floor(
        case.message,
        unauthorized=unauthorized,
    )
    would_escalate = bool(unauthorized or failsafe_floor)
    rf5_families = _rf5_raise_families(case.message)
    rf5_component_raise = bool(rf5_families)
    rf5_only_component_gain = bool(
        rf5_component_raise and not unauthorized and not rf4_floor
    )
    ftp2 = _ftp2_detail(case.message)

    return {
        "case_id": case.case_id,
        "bucket": case.bucket,
        "family": case.family,
        "language": case.language,
        "source": case.source,
        "message": case.message,
        "expected_main_escalates": case.expected_main_escalates,
        "expected_current_escalates": case.expected_current_escalates,
        "expected_rf5_families": list(case.expected_rf5_families),
        "expected_ftp2_cleanup_candidate": case.expected_ftp2_cleanup_candidate,
        "rationale": case.rationale,
        "unauthorized_activity_asserted": unauthorized,
        "rf4_floor": rf4_floor,
        "rf5_raise_families": rf5_families,
        "rf5_component_raise": rf5_component_raise,
        "rf5_only_component_gain": rf5_only_component_gain,
        "failsafe_floor": failsafe_floor,
        "would_escalate": would_escalate,
        "route_policy_would_escalate": would_escalate,
        **ftp2,
    }


def _baseline_by_case_id(baseline_json: Path | None) -> dict[str, bool]:
    if baseline_json is None:
        return {}
    payload = json.loads(baseline_json.read_text(encoding="utf-8"))
    baseline_cases = payload.get("cases", [])
    return {
        str(case["case_id"]): bool(case["would_escalate"])
        for case in baseline_cases
    }


def _classify_change(result: dict[str, Any], baseline_would_escalate: bool) -> str:
    current = bool(result["would_escalate"])
    if baseline_would_escalate == current:
        return "unchanged"
    if baseline_would_escalate and not current:
        return "positive_loss"
    if not baseline_would_escalate and current:
        if bool(result["rf5_only_component_gain"]):
            return "rf5_only_component_gain"
        if bool(result["rf4_floor"]):
            return "rf4_floor_gain"
        if bool(result["unauthorized_activity_asserted"]):
            return "authoritative_detector_gain"
        return "ambiguous_gain"
    return "ambiguous_change"


def _plan_tables(
    *,
    results: list[dict[str, Any]],
    baseline_results: dict[str, bool],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for family in ("m1", "m2", "m4"):
        for language in ("es", "pt"):
            family_cases = [
                result
                for result in results
                if result["family"] == family and result["language"] == language
            ]
            if not family_cases:
                continue
            newly_escalated = 0
            already_escalated = 0
            lowered_positive = 0
            ordinary_benign_overescalation = 0
            ambiguous_or_non_discriminating = 0
            measured_count = 0
            for result in family_cases:
                case_id = str(result["case_id"])
                baseline = baseline_results.get(case_id)
                current = bool(result["would_escalate"])
                if baseline is None:
                    ambiguous_or_non_discriminating += 1
                    continue
                measured_count += 1
                if not baseline and current:
                    if result["bucket"] == "benign_preserve":
                        ordinary_benign_overescalation += 1
                    elif bool(result["rf5_only_component_gain"]):
                        newly_escalated += 1
                    else:
                        ambiguous_or_non_discriminating += 1
                elif baseline and current:
                    already_escalated += 1
                elif baseline and not current:
                    lowered_positive += 1

            rows.append(
                {
                    "family": family,
                    "language": language,
                    "case_count": len(family_cases),
                    "measured_baseline_case_count": measured_count,
                    "component_raise_count": sum(
                        bool(result["rf5_component_raise"])
                        for result in family_cases
                    ),
                    "rf5_only_component_gain_count": sum(
                        bool(result["rf5_only_component_gain"])
                        for result in family_cases
                    ),
                    "newly_escalated_count": newly_escalated,
                    "already_escalated_count": already_escalated,
                    "lowered_positive_count": lowered_positive,
                    "ordinary_benign_overescalation_count": ordinary_benign_overescalation,
                    "ambiguous_or_non_discriminating_count": ambiguous_or_non_discriminating,
                }
            )

    ftp2_cases = [result for result in results if result["family"] == "ftp2"]
    ftp2_cleanup_candidates = [
        {
            "case_id": result["case_id"],
            "language": result["language"],
            "ftp2_cleanup_candidate": result["ftp2_cleanup_candidate"],
            "ftp2_blocked_by": result["ftp2_blocked_by"],
            "would_escalate": result["would_escalate"],
            "expected_current_escalates": result["expected_current_escalates"],
            "expected_ftp2_cleanup_candidate": result[
                "expected_ftp2_cleanup_candidate"
            ],
        }
        for result in ftp2_cases
    ]
    ftp2_no_removal = [
        {
            "case_id": result["case_id"],
            "baseline_would_escalate": baseline_results.get(str(result["case_id"])),
            "current_would_escalate": result["would_escalate"],
            "positive_preserved": bool(result["would_escalate"]),
            "ftp2_cleanup_candidate": result["ftp2_cleanup_candidate"],
            "ftp2_blocked_by": result["ftp2_blocked_by"],
        }
        for result in ftp2_cases
        if result["expected_current_escalates"] is True
    ]

    return {
        "per_family_replay_coverage": rows,
        "ftp2_cleanup_candidate_cases": ftp2_cleanup_candidates,
        "ftp2_non_escalation_no_removal_evidence": ftp2_no_removal,
        "residual_active_route_limitations": {
            "interpret_to_route_policy_replay": False,
            "reason": (
                "The minimal harness evaluates the deterministic predicate stack "
                "used by the route floor. It does not instantiate the full "
                "HTTP/demo turn interpreter and route_policy replay surface."
            ),
            "route_policy_would_escalate_field": (
                "Alias of unauthorized-or-failsafe deterministic route predicate."
            ),
        },
    }


def build_report(*, baseline_json: Path | None = None) -> dict[str, Any]:
    baseline_results = _baseline_by_case_id(baseline_json)
    case_by_id = {case.case_id: case for case in REPLAY_CASES}
    results = [evaluate_case(case) for case in REPLAY_CASES]

    positive_loss: list[str] = []
    benign_removal_regression: list[str] = []
    current_expectation_failures: list[str] = []
    rf5_family_expectation_failures: list[str] = []
    ftp2_expectation_failures: list[str] = []
    changed_from_baseline_json: list[dict[str, Any]] = []
    attribution_case_ids: dict[str, list[str]] = {
        "rf5_only_component_gain": [],
        "rf4_floor_gain": [],
        "authoritative_detector_gain": [],
        "ambiguous_gain": [],
        "positive_loss": [],
        "ambiguous_change": [],
    }

    for result in results:
        case = case_by_id[str(result["case_id"])]
        current = bool(result["would_escalate"])

        if current != case.expected_current_escalates:
            current_expectation_failures.append(case.case_id)

        expected_families = sorted(case.expected_rf5_families)
        observed_families = sorted(str(family) for family in result["rf5_raise_families"])
        if observed_families != expected_families:
            rf5_family_expectation_failures.append(case.case_id)

        if case.expected_ftp2_cleanup_candidate is not None and (
            bool(result["ftp2_cleanup_candidate"])
            != case.expected_ftp2_cleanup_candidate
        ):
            ftp2_expectation_failures.append(case.case_id)

        baseline_expected = case.expected_main_escalates
        if baseline_expected is True and current is False:
            positive_loss.append(case.case_id)
        if (
            baseline_expected is False
            and current is True
            and case.bucket == "benign_preserve"
        ):
            benign_removal_regression.append(case.case_id)

        if case.case_id in baseline_results:
            baseline_current = baseline_results[case.case_id]
            classification = _classify_change(result, baseline_current)
            if classification != "unchanged":
                changed_from_baseline_json.append(
                    {
                        "case_id": case.case_id,
                        "baseline_would_escalate": baseline_current,
                        "current_would_escalate": current,
                        "bucket": case.bucket,
                        "classification": classification,
                    }
                )
                attribution_case_ids.setdefault(classification, []).append(case.case_id)

    attribution_counts = {
        key: len(value)
        for key, value in sorted(attribution_case_ids.items())
    }
    summary = {
        "case_count": len(results),
        "positive_preserve_count": sum(
            case.bucket == "positive_preserve" for case in REPLAY_CASES
        ),
        "benign_preserve_count": sum(
            case.bucket == "benign_preserve" for case in REPLAY_CASES
        ),
        "rf5_gain_control_count": sum(
            case.bucket == "rf5_gain_control" for case in REPLAY_CASES
        ),
        "rf5_component_control_count": sum(
            case.bucket == "rf5_component_control" for case in REPLAY_CASES
        ),
        "ftp2_control_count": sum(case.bucket == "ftp2_control" for case in REPLAY_CASES),
        "positive_loss_count": len(positive_loss),
        "benign_removal_regression_count": len(benign_removal_regression),
        "current_expectation_failure_count": len(current_expectation_failures),
        "rf5_family_expectation_failure_count": len(rf5_family_expectation_failures),
        "ftp2_expectation_failure_count": len(ftp2_expectation_failures),
        "rf5_only_component_gain_count": sum(
            bool(result["rf5_only_component_gain"]) for result in results
        ),
        "changed_from_baseline_json_count": len(changed_from_baseline_json),
        "measured_rf5_only_gain_count": attribution_counts.get(
            "rf5_only_component_gain", 0
        ),
        "measured_rf4_floor_gain_count": attribution_counts.get("rf4_floor_gain", 0),
        "measured_authoritative_detector_gain_count": attribution_counts.get(
            "authoritative_detector_gain", 0
        ),
        "measured_ambiguous_gain_count": attribution_counts.get("ambiguous_gain", 0),
    }
    return {
        "schema_version": "rf5-replay-guardrail-v3",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "baseline_json": str(baseline_json) if baseline_json is not None else None,
        "summary": summary,
        "positive_loss_case_ids": positive_loss,
        "benign_removal_regression_case_ids": benign_removal_regression,
        "current_expectation_failure_case_ids": current_expectation_failures,
        "rf5_family_expectation_failure_case_ids": rf5_family_expectation_failures,
        "ftp2_expectation_failure_case_ids": ftp2_expectation_failures,
        "changed_from_baseline_json": changed_from_baseline_json,
        "measured_attribution_case_ids": attribution_case_ids,
        "measured_attribution_counts": attribution_counts,
        "plan_tables": _plan_tables(results=results, baseline_results=baseline_results),
        "replay_surfaces": {
            "deterministic_predicate_stack": True,
            "file_path_invocation": True,
            "module_invocation": True,
            "interpret_to_route_policy": False,
            "hosted_ci": False,
            "held_out_material": False,
            "live_provider": False,
        },
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
    print(f"rf5_only_component_gain: {summary['rf5_only_component_gain_count']}")
    print(f"measured_rf5_only_gain: {summary['measured_rf5_only_gain_count']}")
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
