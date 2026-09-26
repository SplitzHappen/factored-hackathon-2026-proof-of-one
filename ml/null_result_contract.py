from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any


NULL_RESULT_CONTRACT_VERSION = "factored-r4b-null-result-v1"

GATE_IMPLEMENTATION_COMMIT = "df2398a2fca4c1997ded552711deef11a89e275b"
GATE_RESULT_SHA256 = "af23e3436578455a17a0567d3e6e97126b9fc428f7f53af0eca9ca455682f341"
C_B_RESULT_SHA256 = "31825d493fa6bdb7658a0e2f9e44d2ac2d0065c1e33c72690e7a55ca06dfaefe"

GATE_METRICS = {
    "rows": 331876,
    "positive_rows": 300,
    "prevalence": 0.0009039520784871458,
    "selected_gbdt_pr_auc": 0.0008868433466811729,
    "selected_gbdt_pr_auc_lower_95": 0.0007636378685136978,
    "best_non_gbdt_pr_auc": 0.0009245944836474085,
    "top_0_5_recall": 0.0,
    "top_0_5_precision_lift": 0.0,
}

GATE_CHECKS = {
    "pr_auc_lower_bound_exceeds_best_non_gbdt": False,
    "top_0_5_precision_lift_at_least_10x": False,
    "top_0_5_recall_at_least_5_percent": False,
}


class SupervisedModelStatus(StrEnum):
    REJECTED_AT_VALIDATION_GATE = "rejected_at_validation_gate"


class TestStatus(StrEnum):
    SEALED_NOT_RUN = "sealed_not_run"


class RuntimeEvidenceMode(StrEnum):
    BEHAVIORAL_UNUSUALNESS = "behavioral_unusualness"
    COMPONENT_EVIDENCE = "component_evidence"


PROHIBITED_RUNTIME_CLAIMS = (
    "fraud_probability",
    "fraud_risk_score",
    "fraud_prediction",
    "fraud_adjudication",
    "ml_queue_priority",
    "ml_mandatory_escalation",
)

ALLOWED_BEHAVIORAL_COMPONENTS = (
    "amount_surprise",
    "channel_novelty",
    "merchant_category_novelty",
    "transaction_country_novelty",
    "velocity_24h",
    "velocity_30d",
)


def null_result_contract_dict() -> dict[str, Any]:
    return {
        "version": NULL_RESULT_CONTRACT_VERSION,
        "supervised_model_status": SupervisedModelStatus.REJECTED_AT_VALIDATION_GATE.value,
        "test_status": TestStatus.SEALED_NOT_RUN.value,
        "provenance": {
            "gate_implementation_commit": GATE_IMPLEMENTATION_COMMIT,
            "gate_result_sha256": GATE_RESULT_SHA256,
            "c_b_result_sha256": C_B_RESULT_SHA256,
        },
        "gate": {
            "passed": False,
            "test_authorized": False,
            "metrics": dict(GATE_METRICS),
            "checks": dict(GATE_CHECKS),
        },
        "runtime": {
            "allowed_evidence_modes": [
                RuntimeEvidenceMode.BEHAVIORAL_UNUSUALNESS.value,
                RuntimeEvidenceMode.COMPONENT_EVIDENCE.value,
            ],
            "allowed_behavioral_components": list(ALLOWED_BEHAVIORAL_COMPONENTS),
            "prohibited_claims": list(PROHIBITED_RUNTIME_CLAIMS),
            "behavioral_evidence_is_fraud_probability": False,
            "behavioral_evidence_may_drive_mandatory_escalation": False,
            "behavioral_evidence_may_adjudicate_fraud": False,
            "behavioral_evidence_may_prioritize_queue": False,
        },
        "display": {
            "intelligence_may_show_negative_result": True,
            "workbench_label": "Behavioral Unusualness",
            "required_disclaimer": (
                "Descriptive behavioral evidence only; not a fraud probability "
                "or fraud determination."
            ),
            "forbid_high_performing_language": True,
        },
    }


def null_result_contract_sha256() -> str:
    payload = json.dumps(
        null_result_contract_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_runtime_claim_allowed(claim: str) -> bool:
    return claim not in PROHIBITED_RUNTIME_CLAIMS
