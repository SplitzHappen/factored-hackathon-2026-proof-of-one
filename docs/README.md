# Proof of One documentation map

This folder contains the public documentation and evidence records for the Factored AI & Data Hackathon 2026 submission. Start with the short judge-facing files first; the remaining documents preserve technical evidence, historical design records, and explicit limitations.

## Start here

- [FINAL_DEMO_DEPLOYMENT.md](FINAL_DEMO_DEPLOYMENT.md) — final public demo contract, deployment boundary, verification checklist, and final submission package.
- [DATA_EVIDENCE_SPINE.md](DATA_EVIDENCE_SPINE.md) — concise public narrative for the data and evidence decisions behind the submission.
- [POLICY_PRECEDENCE_AND_DECISION_EVIDENCE.md](POLICY_PRECEDENCE_AND_DECISION_EVIDENCE.md) — deterministic route authority, policy precedence, Decision Evidence, and ACT -> VERIFY semantics.
- [LIMITATIONS.md](LIMITATIONS.md) — active product boundaries and limitations. A limitation listed there is not treated as solved.

## Architecture and runtime evidence

- [R3D_API_WALKING_SKELETON.md](R3D_API_WALKING_SKELETON.md) — API boundary, scoped-session mechanics, and runtime-safety skeleton.
- [R3E_VERTICAL_SLICE_PROOF.md](R3E_VERTICAL_SLICE_PROOF.md) — bilingual normal, clarify, handoff, and escalation vertical-slice proof matrix.
- [LLM_INTERPRETATION_BOUNDARY.md](LLM_INTERPRETATION_BOUNDARY.md) — provider-neutral interpretation boundary and limits on model authority.
- [READ_ONLY_QUERY_BOUNDARY.md](READ_ONLY_QUERY_BOUNDARY.md) — read-only banking-query boundary.
- [EVIDENCE_SERVICE.md](EVIDENCE_SERVICE.md) — evidence-service contract and verification semantics.
- [JUDGE_FACING_UI_SHELL.md](JUDGE_FACING_UI_SHELL.md) — historical local UI-shell provenance, not the final hosted-runtime contract.

## Data, analytical, and ML evidence

- [ANALYTICAL_DECISION_LEDGER.md](ANALYTICAL_DECISION_LEDGER.md) — detailed evidence -> decision -> consequence record.
- [BEHAVIORAL_UNUSUALNESS.md](BEHAVIORAL_UNUSUALNESS.md) — descriptive behavioral-unusualness fallback; not a fraud probability or fraud determination.
- [CURATED_DATA.md](CURATED_DATA.md) — historical minimized curated-data record and integrity rules.
- [ML_FULLDATA_CONTRACT.md](ML_FULLDATA_CONTRACT.md) — full-data ML contract.
- [ML_FEATURE_ARTIFACT.md](ML_FEATURE_ARTIFACT.md) — point-in-time feature artifact record.
- [ML_MODEL_SELECTION.md](ML_MODEL_SELECTION.md) — model-selection evidence.
- [ML_CALIBRATION_GATE_CONTRACT.md](ML_CALIBRATION_GATE_CONTRACT.md) and [ML_CALIBRATION_GATE_RUN.md](ML_CALIBRATION_GATE_RUN.md) — pre-registered calibration/usefulness gate and run record.
- [ML_NULL_RESULT.md](ML_NULL_RESULT.md) — supervised fraud-risk model null result and non-deployment decision.
- [ML_SIGNAL_PROBE.md](ML_SIGNAL_PROBE.md) — signal-probe evidence.

## Evaluation and language-stress records

- [HELDOUT_EVALUATION.md](HELDOUT_EVALUATION.md) — held-out evaluation design and owner-gated boundary. This repository does not claim a held-out PASS.
- [PROVIDER_BAKEOFF.md](PROVIDER_BAKEOFF.md) — provider-selection and language-stress evidence.
- [REALISTIC_LANGUAGE_SLICE.md](REALISTIC_LANGUAGE_SLICE.md) — synthetic realistic-language v1 boundary; not admissible for baseline-vs-LLM uplift claims.
- [REALISTIC_LANGUAGE_V2_FREEZE_PROTOCOL.md](REALISTIC_LANGUAGE_V2_FREEZE_PROTOCOL.md) — requirements for a future blind-authored/sealed v2 language evaluation.

## Historical audit packages

- [FULL_PROJECT_AUDIT_PACKAGE_2026-09-26.md](FULL_PROJECT_AUDIT_PACKAGE_2026-09-26.md) — historical full-project audit package.
- [INTEGRATED_PRODUCT_API_SAFETY_AUDIT_PACKAGE_2026-09-26.md](INTEGRATED_PRODUCT_API_SAFETY_AUDIT_PACKAGE_2026-09-26.md) — historical integrated product/API safety audit package.

## Claim boundaries

The final public submission remains a hackathon prototype over organizer-provided synthetic challenge data. It is not fraud detection, not a live-bank integration, not production-ready, not pilot-ready, and not a claim of real-customer-data performance.
