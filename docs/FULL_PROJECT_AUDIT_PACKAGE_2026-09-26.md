# Full Project Audit Package — Factored AI & Data Hackathon 2026

Date: 2026-09-26  
Purpose: independent full-project audit before further implementation

## Freeze

Audit the public implementation as two immutable layers:

1. **Public main baseline**
   - repository: `SplitzHappen/factored-hackathon-2026-proof-of-one`
   - commit: `2dcd67e994f6836ff6ad30b35e0ffa2c059552a4`

2. **Unmerged provider-refresh overlay**
   - PR: `#26`
   - exact head: `18e2a1b66faf87fc307a2946db2facbde7f2fbd4`
   - base: `2dcd67e994f6836ff6ad30b35e0ffa2c059552a4`

Do not substitute moving branches or later commits.

The audit-package branch itself is documentation-only and is not the implementation candidate.

## Scope

This is not a narrow R3C audit. Review the **entire current public repository** and compare it against the canonical Continuity design, decisions, evaluation contracts, roadmap, and evidence.

The requested review includes implementation correctness, statistical rigor, security/privacy, data engineering, evaluation isolation, model methodology, product/safety boundaries, test quality, CI/deployment readiness, documentation accuracy, portfolio claims, and hackathon submission compatibility.

## Public repository inventory

### Root / deployment

- `.dockerignore`
- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `requirements-dev.txt`
- `requirements-ml.txt`
- `README.md`

Review:
- credential/privacy hygiene;
- production dependency sufficiency;
- development-only dependency separation;
- image reproducibility;
- container runtime assumptions;
- whether CI meaningfully validates the production image;
- public/private artifact exclusions;
- whether a judge-accessible deployment can be built safely from this repository.

### Application layer

- `app/bank.py`
- `app/behavioral_evidence.py`
- `app/evidence_service.py`
- `app/interpretation.py`
- `app/main.py`
- `app/policy.py`
- `app/provider_adapters.py`
- `app/runtime.py`
- `app/schemas.py`
- `app/settings.py`

Review:
- identity/session authority;
- ownership enforcement;
- read-only banking guarantees;
- mutable operational-state separation;
- cross-customer disclosure paths;
- policy-router determinism;
- escalation semantics;
- prohibited-action handling;
- transaction ambiguity behavior;
- LLM authority boundaries;
- provider failure/fallback behavior;
- prompt-injection exposure;
- untrusted model-output validation;
- evidence-service authorization;
- behavioral-evidence semantics;
- concurrency/state risks;
- missing production controls or assumptions.

### Curated-data build

- `scripts/build_curated_bank.py`

Review:
- raw-to-curated lineage;
- field minimization;
- schema/version checks;
- integrity gates;
- failure atomicity;
- deterministic/reproducible output;
- accidental target/reference-field exposure;
- whether the builder correctly encodes the R0 trust findings.

### Evaluation

- `evaluation/contracts.py`
- `evaluation/freeze.py`
- `evaluation/generate.py`
- `evaluation/portuguese_stress.py`
- `evaluation/provider_bakeoff.py`
- `evaluation/scoring.py`
- `evaluation/suite.py`

Review:
- development/held-out isolation;
- leakage or path-bypass risks;
- deterministic generation/freeze;
- answer-key construction;
- scoring correctness;
- whether hard safety metrics fail closed;
- multilingual provenance;
- paired ES/PT construction;
- category/intent target validity;
- multi-turn semantics;
- high-risk repeat logic;
- telemetry/provenance sufficiency;
- whether evaluator bugs could systematically flatter or punish the system;
- provider-selection fairness;
- whether post-checks mask provider quality in a way that compromises the bake-off;
- whether any held-out information could influence development decisions.

Do **not** inspect private frozen case contents during this code/contract audit.

### ML / analytics

- `ml/build_full_features.py`
- `ml/calibration_contract.py`
- `ml/calibration_gate.py`
- `ml/evaluation_metrics.py`
- `ml/full_data_contract.py`
- `ml/model_selection.py`
- `ml/null_result_contract.py`
- `ml/signal_probe.py`

Review:
- target leakage;
- same-timestamp/future leakage;
- split construction;
- history-window semantics;
- feature allowlist;
- target/reference-score exclusion;
- category encoding;
- baseline fairness;
- rare-event metric correctness;
- bootstrap methodology;
- calibration methodology;
- model-selection/usefulness separation;
- untouched-test survival logic;
- convergence-warning handling;
- negative-result interpretation;
- whether the behavioral fallback is genuinely target-free and non-predictive;
- any statistical flaw that changes the current null-result conclusion or its confidence.

### Public analytical / technical documentation

Audit every claim in:

- `docs/ANALYTICAL_DECISION_LEDGER.md`
- `docs/BEHAVIORAL_UNUSUALNESS.md`
- `docs/CURATED_DATA.md`
- `docs/DATA_EVIDENCE_SPINE.md`
- `docs/EVIDENCE_SERVICE.md`
- `docs/HELDOUT_EVALUATION.md`
- `docs/LLM_INTERPRETATION_BOUNDARY.md`
- `docs/ML_CALIBRATION_GATE_CONTRACT.md`
- `docs/ML_CALIBRATION_GATE_RUN.md`
- `docs/ML_EVALUATION_CONTRACT.md`
- `docs/ML_FEATURE_ARTIFACT.md`
- `docs/ML_FULLDATA_CONTRACT.md`
- `docs/ML_MODEL_SELECTION.md`
- `docs/ML_NULL_RESULT.md`
- `docs/ML_SIGNAL_PROBE.md`
- `docs/PROVIDER_BAKEOFF.md`
- `docs/READ_ONLY_QUERY_BOUNDARY.md`

Review:
- code/document divergence;
- unsupported quantitative claims;
- hindsight-biased narrative;
- synthetic-data overgeneralization;
- misuse of causal/predictive language;
- accidental exposure of participant-only/private information;
- whether the Data Excellence story is technically defensible;
- whether negative results and limitations are represented accurately.

### Tests

Review the complete `tests/` tree, including:

- repository hygiene;
- bank repository;
- curated builder;
- runtime state;
- policy;
- interpretation;
- evidence service;
- behavioral evidence;
- evaluation suite/generator/freeze/scoring;
- provider bake-off;
- ML signal/full-data/model-selection/calibration/null-result contracts.

Do not merely count tests. Identify:
- untested critical branches;
- tests that mirror implementation and therefore cannot detect the same bug;
- brittle mocks;
- missing integration tests;
- false confidence from synthetic fixtures;
- missing adversarial/concurrency/error cases;
- tests whose assertions encode a questionable business/statistical assumption.

## Known implementation history to challenge, not assume correct

The audit should independently verify rather than trust these prior conclusions:

- account/payment inquiries are the evidence-leading workflow;
- source primary keys are clean but several business identifiers are not identity-safe;
- complaint/product/digital product relationships are semantically unsafe;
- customer/product/transaction ownership chain is trusted;
- runtime banking data can remain read-only;
- retrospective fraud fields are excluded from runtime;
- held-out and development pools are isolated;
- point-in-time feature engineering is leakage-safe;
- the supervised fraud model failed a valid predeclared usefulness gate;
- keeping the untouched test sealed was methodologically correct;
- Behavioral Unusualness is truly descriptive rather than covert prediction;
- offline/runtime evidence semantics are aligned;
- R3C model output is safely subordinate to deterministic post-checks;
- the provider bake-off target builder and ranking rule are fair;
- the current public documentation accurately reflects implementation and evidence.

If any of these are wrong, say so.

## Provider-refresh overlay

Also audit PR #26 exact head `18e2a1b66faf87fc307a2946db2facbde7f2fbd4`.

Independently verify against current official provider documentation where possible:

- GPT-6 Luna API model identifier;
- Responses API structured-output payload;
- `reasoning.effort=none`;
- current standard pricing used by the harness;
- Qwen3.7-Flash exact API identifier;
- strict structured-output support;
- regional endpoint behavior;
- current Singapore international pricing;
- DeepSeek V4.1 Flash / `deepseek-flash` identifier;
- JSON-mode behavior;
- thinking-disable parameter;
- current peak/off-peak pricing.

Check whether the three candidates form a fair and defensible low-cost comparison for this narrow ES/PT extraction task.

## Cross-repository consistency

The public repository must be compared against the canonical Continuity project frozen for this audit.

Continuity repository:
`SplitzHappen/personal-ai-workspace`

Continuity freeze:
`1a8b687a4af98264d0f31bbd2aadedb3b0aa6c16`

Project root:
`projects/factored-ai-data-hackathon-2026/`

Any mismatch among:
- design;
- decisions;
- roadmap;
- state;
- public code;
- public documentation;
- test assumptions;
- claimed evidence;

is in scope.

## Audit dimensions

At minimum provide explicit findings for:

1. competition/problem-fit and submission compliance;
2. source-data audit quality;
3. data contracts, lineage, privacy, minimization;
4. workflow-selection methodology;
5. architecture and separation of concerns;
6. authentication/session/tenant/role model, including missing future obligations;
7. authorization and ownership safety;
8. deterministic policy and escalation;
9. LLM interpretation boundary;
10. provider bake-off design;
11. held-out methodology and leakage isolation;
12. multilingual ES/PT methodology;
13. evaluation metrics and statistical thresholds;
14. ML signal-probe design;
15. point-in-time feature engineering;
16. baseline/model-selection methodology;
17. calibration/usefulness gate;
18. null-result conclusion;
19. behavioral-evidence fallback;
20. runtime/offline semantic parity;
21. test quality and missing tests;
22. CI/container/deployment readiness;
23. security/privacy/secret handling;
24. public-repository hygiene;
25. Data Excellence narrative and portfolio claims;
26. code/docs/Continuity consistency;
27. roadmap sequencing and hidden dependencies;
28. unnecessary complexity/overengineering;
29. missing functionality required for a credible submission;
30. schedule risk for a solo entrant;
31. any issue that should be repaired before further feature development.

## Severity and output expectations

Use:
- BLOCKER
- MAJOR
- MODERATE
- MINOR
- NOTE

For each finding include:
- exact repository/file/location;
- factual failure mode;
- why it matters;
- smallest defensible repair;
- whether existing downstream work is invalidated;
- what should be revalidated after repair.

Do not inflate stylistic preferences into defects.

## Final judgment requested

End with:

- overall disposition:
  - `PASS_TO_CONTINUE`
  - `REPAIR_BEFORE_CONTINUING`
  - `FUNDAMENTAL_RETHINK_REQUIRED`
- ordered repair queue;
- what can safely continue unchanged;
- what must remain frozen until repaired;
- whether public PR #26 may merge;
- whether R3C-B live provider execution may begin;
- whether any completed R0–R4 evidence/result must be recomputed or withdrawn.

This audit package intentionally asks for a harsh review. The goal is to find defects now, before more implementation is layered on top.
