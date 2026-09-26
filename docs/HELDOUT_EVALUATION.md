# Held-out conversational evaluation

The semantic held-out suite is frozen before any LLM prompt/provider optimization.

## Public versus private artifacts

This public repository contains:
- evaluation contracts;
- quota validation;
- deterministic generation/scoring code;
- tests;
- final aggregate/versioned results.

Generated held-out prompts, organizer-backed record locators, and answer keys are **not committed**. They live under git-ignored `evaluation/private/` during local evaluation.

The runtime application never reads answer-key files.

## Frozen v1 composition

Total: 200 cases.

| Category | ES | PT | Total |
|---|---:|---:|---:|
| Normal supported | 45 | 15 | 60 |
| Ambiguity / clarification | 22 | 8 | 30 |
| Data quality / grounding | 19 | 6 | 25 |
| Authorization / prohibited | 23 | 7 | 30 |
| Fraud / escalation | 19 | 6 | 25 |
| Adversarial / prompt injection | 22 | 8 | 30 |
| **Total** | **150** | **50** | **200** |

At least 50 cases are multi-turn.

The 85 authorization + fraud + adversarial cases form the exact repeated high-risk set required for three-run safety testing.

## Portuguese construction

Portuguese prompts are team-generated because the organizer supplied no Portuguese transcript corpus.

Each Portuguese case must:
- have provenance `team_generated`;
- have language provenance `team_generated_portuguese`;
- point to an existing Spanish `source_pair_id` representing the equivalent factual scenario.

This makes language comparisons interpretable without claiming organizer Portuguese provenance.

## Fraud/escalation boundary

Fraud/escalation cases are triggered by the user's own semantic assertion that a transaction is unrecognized, unauthorized, or suspected fraudulent.

The case prompt and runtime context never expose retrospective `is_fraud` or organizer `fraud_score` as customer facts.

Every fraud/escalation answer key requires:
- final route `ESCALATE`;
- mandatory escalation;
- no autonomous fraud adjudication.

## Freeze identity

The final generated case file and answer-key file receive separate SHA-256 hashes plus a combined SHA-256 manifest.

Hashing canonicalizes case/key order by immutable case ID so file-generation ordering cannot change the frozen suite identity.

Any held-out case used in development loses held-out status and must be replaced before refreezing.
