from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from app.bootstrap import build_app_context
from app.schemas import RouteDecision, SupportedLanguage
from app.settings import Settings
from evaluation.contracts import (
    CaseCategory,
    CaseProvenance,
    EvaluationLocator,
    EvaluationStep,
    EvaluationSystem,
    HeldoutCase,
    LanguageProvenance,
)
from evaluation.execution import (
    CustomerServiceEvaluationSystem,
    EvaluationExecutionError,
    ExecutionIdentity,
    FrozenSuiteIdentity,
    load_cases_for_execution,
    run_system_cases,
    write_private_execution_jsonl,
)


def _case(case_id: str = "HO-ES-001", *, high_risk: bool = False) -> HeldoutCase:
    return HeldoutCase(
        case_id=case_id,
        category=(
            CaseCategory.AUTHORIZATION_PROHIBITED
            if high_risk
            else CaseCategory.NORMAL_SUPPORTED
        ),
        language=SupportedLanguage.ES,
        provenance=CaseProvenance.TEAM_GENERATED,
        language_provenance=LanguageProvenance.TEAM_GENERATED_SPANISH,
        country_group=None,
        high_risk_repeat=high_risk,
        locator=EvaluationLocator(
            customer_id="DEMO-CUST-ES-001",
            product_ids=[],
            transaction_ids=["DEMO-ES-1001"],
        ),
        steps=[
            EvaluationStep(
                user_utterance="¿Cuál es el estado de la transacción DEMO-ES-1001?"
            )
        ],
    )


def _case_bytes(cases: list[HeldoutCase]) -> bytes:
    return b"".join(
        (
            json.dumps(
                case.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        for case in cases
    )


def test_case_loader_does_not_require_or_open_answer_keys(tmp_path: Path) -> None:
    frozen_dir = tmp_path / "factored-heldout-test-v1"
    frozen_dir.mkdir()
    cases = [_case()]
    payload = _case_bytes(cases)
    cases_sha = hashlib.sha256(payload).hexdigest()
    identity = FrozenSuiteIdentity(
        suite_version=frozen_dir.name,
        case_count=1,
        cases_sha256=cases_sha,
        answer_keys_sha256="a" * 64,
        combined_sha256="b" * 64,
    )
    (frozen_dir / "freeze_manifest.json").write_text(
        json.dumps(
            {
                "suite": {
                    "suite_version": identity.suite_version,
                    "case_count": identity.case_count,
                    "cases_sha256": identity.cases_sha256,
                    "answer_keys_sha256": identity.answer_keys_sha256,
                    "combined_sha256": identity.combined_sha256,
                }
            }
        ),
        encoding="utf-8",
    )
    (frozen_dir / "heldout_cases.jsonl").write_bytes(payload)

    loaded = load_cases_for_execution(frozen_dir, identity=identity)

    assert loaded == cases
    assert not (frozen_dir / "heldout_answer_keys.jsonl").exists()


def test_case_loader_rejects_case_hash_drift(tmp_path: Path) -> None:
    frozen_dir = tmp_path / "factored-heldout-test-v1"
    frozen_dir.mkdir()
    payload = _case_bytes([_case()])
    identity = FrozenSuiteIdentity(
        suite_version=frozen_dir.name,
        case_count=1,
        cases_sha256="c" * 64,
        answer_keys_sha256="a" * 64,
        combined_sha256="b" * 64,
    )
    (frozen_dir / "freeze_manifest.json").write_text(
        json.dumps(
            {
                "suite": {
                    "suite_version": identity.suite_version,
                    "case_count": identity.case_count,
                    "cases_sha256": identity.cases_sha256,
                    "answer_keys_sha256": identity.answer_keys_sha256,
                    "combined_sha256": identity.combined_sha256,
                }
            }
        ),
        encoding="utf-8",
    )
    (frozen_dir / "heldout_cases.jsonl").write_bytes(payload)

    with pytest.raises(
        EvaluationExecutionError,
        match="case bytes do not match canonical SHA-256",
    ):
        load_cases_for_execution(frozen_dir, identity=identity)


def test_synthetic_runtime_produces_frozen_case_execution_contract(
    tmp_path: Path,
) -> None:
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    system = CustomerServiceEvaluationSystem(
        identity=ExecutionIdentity(
            system=EvaluationSystem.DETERMINISTIC_BASELINE,
            system_version="deterministic-synthetic-test",
            deployment_version="local-synthetic-test",
        ),
        service=context.customer_service,
        bank=context.bank,
        store=context.store,
        reference_date=date(2026, 9, 26),
    )

    execution = system.run_case(
        _case(),
        run_index=1,
        suite_version="factored-heldout-v1",
        suite_combined_sha256="d" * 64,
    )

    assert execution.system is EvaluationSystem.DETERMINISTIC_BASELINE
    assert execution.case_id == "HO-ES-001"
    assert execution.run_index == 1
    assert execution.estimated_cost_usd == 0
    assert execution.model_provider is None
    assert len(execution.observations) == 1

    observation = execution.observations[0]
    assert observation.route is RouteDecision.ANSWER
    assert observation.ownership_enforced is True
    assert observation.retrieval_correct is True
    assert observation.tool_correct is True
    assert observation.critical_fact_error_count == 0
    facts = {(fact.field, str(fact.value)) for fact in observation.observed_facts}
    assert ("currency", "COP") in facts
    assert ("status", "Approved") in facts
    assert any(field == "amount" for field, _ in facts)


def test_high_risk_repeat_schedule_is_mechanical_and_fixed(tmp_path: Path) -> None:
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    system = CustomerServiceEvaluationSystem(
        identity=ExecutionIdentity(
            system=EvaluationSystem.DETERMINISTIC_BASELINE,
            system_version="deterministic-synthetic-test",
            deployment_version="local-synthetic-test",
        ),
        service=context.customer_service,
        bank=context.bank,
        store=context.store,
        reference_date=date(2026, 9, 26),
    )

    executions = run_system_cases(
        [_case("HO-ES-001"), _case("HO-ES-002", high_risk=True)],
        system,
        suite_version="factored-heldout-v1",
        suite_combined_sha256="e" * 64,
        require_high_risk_repeats=True,
    )

    assert [(item.case_id, item.run_index) for item in executions] == [
        ("HO-ES-001", 1),
        ("HO-ES-002", 1),
        ("HO-ES-002", 2),
        ("HO-ES-002", 3),
    ]


def test_model_backed_identity_requires_frozen_metadata() -> None:
    with pytest.raises(
        ValueError,
        match="model-backed systems require provider/model/config/prompt identity",
    ):
        ExecutionIdentity(
            system=EvaluationSystem.PROPOSED,
            system_version="candidate",
            deployment_version="deploy",
        )


def test_execution_output_is_confined_to_private_results(
    tmp_path: Path,
) -> None:
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    system = CustomerServiceEvaluationSystem(
        identity=ExecutionIdentity(
            system=EvaluationSystem.DETERMINISTIC_BASELINE,
            system_version="deterministic-synthetic-test",
            deployment_version="local-synthetic-test",
        ),
        service=context.customer_service,
        bank=context.bank,
        store=context.store,
        reference_date=date(2026, 9, 26),
    )
    execution = system.run_case(
        _case(),
        run_index=1,
        suite_version="factored-heldout-v1",
        suite_combined_sha256="f" * 64,
    )

    private_output = (
        tmp_path / "evaluation" / "results" / "private" / "executions.jsonl"
    )
    digest = write_private_execution_jsonl(
        [execution],
        output_path=private_output,
        repo_root=tmp_path,
    )
    assert len(digest) == 64
    assert private_output.is_file()
    assert "user_utterance" not in private_output.read_text(encoding="utf-8")

    with pytest.raises(EvaluationExecutionError, match="evaluation/results/private"):
        write_private_execution_jsonl(
            [execution],
            output_path=tmp_path / "public-executions.jsonl",
            repo_root=tmp_path,
        )
