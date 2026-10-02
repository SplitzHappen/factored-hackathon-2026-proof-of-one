"""Minimal deterministic RF5 replay guardrail harness.

This script intentionally uses public/non-held-out development surfaces only. It
is designed to make RF5 replay evidence reproducible without touching held-out
case content, live providers, semantic providers, hosted CI, or production data.

Default behavior evaluates the current checkout against named replay cases whose
baseline expectations are derived from existing public/non-held-out tests. When a
previous JSON output is supplied with --baseline-json, the script also compares
current outcomes against those baseline results by case_id.
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

from app.interpretation import InterpretationService
from app.unauthorized_signals import is_explicit_unauthorized_assertion

try:  # RF5 does not exist on older/main checkouts.
    from app.rf5_stage1 import rf5_stage1_findings
except ModuleNotFoundError:  # pragma: no cover - exercised only on pre-RF5 branches.
    rf5_stage1_findings = None  # type: ignore[assignment]


CaseBucket = Literal["positive_preserve", "benign_preserve", "rf5_positive_control"]


@dataclass(frozen=True, slots=True)
class ReplayCase:
    case_id: str
    bucket: CaseBucket
    source: str
    message: str
    expected_main_escalates: bool | None
    expected_current_escalates: bool
    rationale: str


# Case sources are existing public/non-held-out tests and the RF5 repair-2
# controls. No held-out case wording is embedded here.
REPLAY_CASES: tuple[ReplayCase, ...] = (
    ReplayCase(
        case_id="rf1u-positive-fraud-characterization-es-001",
        bucket="positive_preserve",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Esto fue un consumo fraudulento con la tarjeta débito.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        rationale="Existing public RF1U fraud-characterization positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf1u-positive-fraud-characterization-pt-001",
        bucket="positive_preserve",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Esse foi um saque fraudulento, eu estava viajando.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        rationale="Existing Portuguese RF1U fraud-characterization positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf1u-positive-non-recognition-pt-001",
        bucket="positive_preserve",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Não reconheço este movimento de cinquenta reais.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        rationale="Existing RF1U non-recognition positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf1u-positive-third-party-es-001",
        bucket="positive_preserve",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Ese pago lo realizó alguien más, y no yo.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        rationale="Existing RF1U third-party-authorship positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf1u-positive-data-misuse-es-001",
        bucket="positive_preserve",
        source="tests/test_rf1u_product_repair.py::_FAMILY_POSITIVES",
        message="Utilizaron mis datos bancarios para pedir un microcrédito.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        rationale="Existing RF1U data-misuse positive must not be lost.",
    ),
    ReplayCase(
        case_id="rf1u-positive-scam-activity-es-001",
        bucket="positive_preserve",
        source="tests/test_rf1u_product_repair.py::_STILL_REPORTS",
        message="Caí en un phishing. Después sacaron un avance a mi nombre.",
        expected_main_escalates=True,
        expected_current_escalates=True,
        rationale="Existing scam-activity report must not be lost.",
    ),
    ReplayCase(
        case_id="rf5-benign-resolved-fraud-es-001",
        bucket="benign_preserve",
        source="tests/test_rf1u_product_repair.py::_NAMED_NEGATIVES and RF5 repair-2 validation",
        message="Tenía un pago fraudulento pero ya lo reversaron.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Resolved/reversed fraud mention must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-prevention-question-es-001",
        bucket="benign_preserve",
        source="tests/test_rf1u_product_repair.py::_NAMED_NEGATIVES and RF5 repair-2 validation",
        message="¿Cómo detectar un consumo fraudulento?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Prevention/education question must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-hypothetical-pt-001",
        bucket="benign_preserve",
        source="tests/test_rf3_product_repair.py and RF5 repair-2 validation",
        message="Caso alguém use meu cartão sem minha autorização, o que faço?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Hypothetical/procedural Portuguese question must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-lawful-cause-es-001",
        bucket="benign_preserve",
        source="tests/test_rf4_failsafe_floor.py and RF5 repair-2 validation",
        message="La DIAN me retuvo plata de la cuenta sin mi autorización por un impuesto pendiente.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Lawful tax-authority withholding must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-benign-lawful-cause-pt-001",
        bucket="benign_preserve",
        source="tests/test_rf4_failsafe_floor.py and RF5 repair-2 validation",
        message="A Receita Federal bloqueou dinheiro da minha conta sem minha permissão; como consulto?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Lawful Receita Federal blocking/withholding must remain benign.",
    ),
    ReplayCase(
        case_id="rf1u-benign-status-es-001",
        bucket="benign_preserve",
        source="tests/test_rf1u_product_repair.py::_BENIGN",
        message="¿Cuál es el estado de mi pago de ayer?",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Ordinary payment-status request must remain benign.",
    ),
    ReplayCase(
        case_id="rf1u-benign-account-movements-pt-001",
        bucket="benign_preserve",
        source="tests/test_rf1u_product_repair.py::_BENIGN",
        message="Quero ver os movimentos da minha conta desta semana.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Ordinary account-movement lookup must remain benign.",
    ),
    ReplayCase(
        case_id="rf1u-benign-authorized-transfer-es-001",
        bucket="benign_preserve",
        source="tests/test_rf1u_product_repair.py::_BENIGN",
        message="La transferencia la hizo otra persona con mi autorización.",
        expected_main_escalates=False,
        expected_current_escalates=False,
        rationale="Authorized third-party transfer must remain benign.",
    ),
    ReplayCase(
        case_id="rf5-control-si-m1-es-001",
        bucket="rf5_positive_control",
        source="tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        message="Sí, tengo un débito en mi cuenta sin mi autorización.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        rationale="RF5 guard word 'si/sí' must not suppress a true positive.",
    ),
    ReplayCase(
        case_id="rf5-control-caso-m1-es-001",
        bucket="rf5_positive_control",
        source="tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        message="Mi caso es que tengo un pago en mi cuenta sin mi autorización.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        rationale="RF5 guard word 'caso' must not suppress a true positive.",
    ),
    ReplayCase(
        case_id="rf5-control-bloqueo-m1-es-001",
        bucket="rf5_positive_control",
        source="tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        message="Pedí el bloqueo de mi tarjeta porque tengo un débito sin mi autorización.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        rationale="The word 'bloqueo' must not suppress a true positive.",
    ),
    ReplayCase(
        case_id="rf5-control-bloqueou-m1-pt-001",
        bucket="rf5_positive_control",
        source="tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        message="O banco bloqueou o cartão, mas há um pagamento na conta sem minha permissão.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        rationale="The word 'bloqueou' must not suppress a true positive.",
    ),
    ReplayCase(
        case_id="rf5-control-retuvo-m4-es-001",
        bucket="rf5_positive_control",
        source="tests/test_rf5_stage1.py::test_rf5_guard_words_do_not_suppress_true_positive_controls",
        message="La tienda retuvo el pedido, pero hay un pago fraudulento en mi cuenta.",
        expected_main_escalates=None,
        expected_current_escalates=True,
        rationale="The word 'retuvo' must not suppress a true M4 positive.",
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


def evaluate_case(case: ReplayCase) -> dict[str, Any]:
    unauthorized = is_explicit_unauthorized_assertion(case.message)
    failsafe_floor = InterpretationService._failsafe_floor(
        case.message,
        unauthorized=unauthorized,
    )
    would_escalate = bool(unauthorized or failsafe_floor)
    return {
        "case_id": case.case_id,
        "bucket": case.bucket,
        "source": case.source,
        "message": case.message,
        "expected_main_escalates": case.expected_main_escalates,
        "expected_current_escalates": case.expected_current_escalates,
        "rationale": case.rationale,
        "unauthorized_activity_asserted": unauthorized,
        "failsafe_floor": failsafe_floor,
        "would_escalate": would_escalate,
        "rf5_raise_families": _rf5_families(case.message),
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


def build_report(*, baseline_json: Path | None = None) -> dict[str, Any]:
    baseline_results = _baseline_by_case_id(baseline_json)
    case_by_id = {case.case_id: case for case in REPLAY_CASES}
    results = [evaluate_case(case) for case in REPLAY_CASES]

    positive_loss: list[str] = []
    benign_removal_regression: list[str] = []
    expected_rf5_gain: list[str] = []
    current_expectation_failures: list[str] = []
    changed_from_baseline_json: list[dict[str, Any]] = []

    for result in results:
        case = case_by_id[str(result["case_id"])]
        current = bool(result["would_escalate"])
        expected_current = case.expected_current_escalates

        if current != expected_current:
            current_expectation_failures.append(case.case_id)

        baseline_expected = case.expected_main_escalates
        if baseline_expected is True and current is False:
            positive_loss.append(case.case_id)
        if (
            baseline_expected is False
            and current is True
            and case.bucket == "benign_preserve"
        ):
            benign_removal_regression.append(case.case_id)
        if baseline_expected is False and current is True and case.expected_current_escalates:
            expected_rf5_gain.append(case.case_id)

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
        "positive_preserve_count": sum(
            case.bucket == "positive_preserve" for case in REPLAY_CASES
        ),
        "benign_preserve_count": sum(
            case.bucket == "benign_preserve" for case in REPLAY_CASES
        ),
        "rf5_positive_control_count": sum(
            case.bucket == "rf5_positive_control" for case in REPLAY_CASES
        ),
        "positive_loss_count": len(positive_loss),
        "benign_removal_regression_count": len(benign_removal_regression),
        "current_expectation_failure_count": len(current_expectation_failures),
        "changed_from_baseline_json_count": len(changed_from_baseline_json),
    }
    return {
        "schema_version": "rf5-replay-guardrail-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "baseline_json": str(baseline_json) if baseline_json is not None else None,
        "summary": summary,
        "positive_loss_case_ids": positive_loss,
        "benign_removal_regression_case_ids": benign_removal_regression,
        "expected_rf5_gain_case_ids": expected_rf5_gain,
        "current_expectation_failure_case_ids": current_expectation_failures,
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
    print(f"changed_from_baseline_json: {summary['changed_from_baseline_json_count']}")

    failed = bool(
        summary["positive_loss_count"]
        or summary["benign_removal_regression_count"]
        or summary["current_expectation_failure_count"]
    )
    if failed:
        print("guardrail: FAIL")
        return 0 if args.allow_failures else 1
    print("guardrail: PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
