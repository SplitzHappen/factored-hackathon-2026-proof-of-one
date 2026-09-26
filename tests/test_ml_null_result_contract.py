from ml.null_result_contract import (
    GATE_CHECKS,
    GATE_METRICS,
    PROHIBITED_RUNTIME_CLAIMS,
    SupervisedModelStatus,
    TestStatus,
    is_runtime_claim_allowed,
    null_result_contract_dict,
    null_result_contract_sha256,
)


def test_supervised_model_is_rejected_and_test_stays_sealed() -> None:
    contract = null_result_contract_dict()

    assert (
        contract["supervised_model_status"]
        == SupervisedModelStatus.REJECTED_AT_VALIDATION_GATE.value
    )
    assert contract["test_status"] == TestStatus.SEALED_NOT_RUN.value
    assert contract["gate"]["passed"] is False
    assert contract["gate"]["test_authorized"] is False
    assert all(value is False for value in GATE_CHECKS.values())


def test_gate_metrics_match_canonical_negative_result() -> None:
    assert GATE_METRICS["rows"] == 331876
    assert GATE_METRICS["positive_rows"] == 300
    assert GATE_METRICS["selected_gbdt_pr_auc"] < GATE_METRICS["prevalence"]
    assert (
        GATE_METRICS["selected_gbdt_pr_auc_lower_95"]
        < GATE_METRICS["best_non_gbdt_pr_auc"]
    )
    assert GATE_METRICS["top_0_5_recall"] == 0.0
    assert GATE_METRICS["top_0_5_precision_lift"] == 0.0


def test_runtime_fraud_claims_are_prohibited() -> None:
    for claim in PROHIBITED_RUNTIME_CLAIMS:
        assert is_runtime_claim_allowed(claim) is False

    assert is_runtime_claim_allowed("behavioral_unusualness") is True
    assert is_runtime_claim_allowed("amount_surprise") is True


def test_behavioral_evidence_cannot_drive_fraud_decisions() -> None:
    runtime = null_result_contract_dict()["runtime"]

    assert runtime["behavioral_evidence_is_fraud_probability"] is False
    assert runtime["behavioral_evidence_may_drive_mandatory_escalation"] is False
    assert runtime["behavioral_evidence_may_adjudicate_fraud"] is False
    assert runtime["behavioral_evidence_may_prioritize_queue"] is False


def test_null_result_contract_hash_is_stable() -> None:
    first = null_result_contract_sha256()
    second = null_result_contract_sha256()

    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")
