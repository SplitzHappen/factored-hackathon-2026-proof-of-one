# R4B-D-A supervised-ML negative result

Proof of One's supervised fraud model **failed the pre-registered validation/usefulness gate**.

This is a product constraint, not merely an evaluation footnote.

## Canonical gate result

- calibration/gate rows: 331,876
- fraud-positive rows: 300
- segment prevalence: 0.0009039520784871458
- selected GBDT PR-AUC: 0.0008868433466811729
- GBDT bootstrap 95% lower bound: 0.0007636378685136978
- best non-GBDT PR-AUC: 0.0009245944836474085
- top-0.5% review recall: 0.0
- top-0.5% precision lift: 0.0

All three frozen usefulness checks failed.

Canonical gate artifact SHA-256:

`af23e3436578455a17a0567d3e6e97126b9fc428f7f53af0eca9ca455682f341`

## Untouched test

The gate returned:

`test_authorized = false`

Therefore the final 15% / 663,750-row test partition is **sealed and not run**.

Proof of One does not need test performance to support the negative result: the model already failed the pre-registered gate required to justify test unsealing.

## Runtime prohibition

The product must not expose or claim any Proof of One:

- fraud probability;
- fraud-risk score;
- fraud prediction;
- fraud adjudication;
- ML-driven queue priority;
- ML-driven mandatory escalation.

The failed supervised experiment remains visible in Resolution Intelligence as a transparent negative result.

## Fallback behavioral evidence

The Human Resolution Workbench may use deterministic behavioral evidence such as:

- amount surprise relative to prior same-currency history;
- channel novelty;
- merchant-category novelty;
- transaction-country novelty;
- 24-hour transaction velocity;
- 30-day transaction velocity.

A composite may be labeled **Behavioral Unusualness**, but it must be explicitly described as descriptive behavioral evidence.

Required meaning:

> Descriptive behavioral evidence only; not a fraud probability or fraud determination.

It cannot route mandatory escalation, adjudicate fraud, or prioritize the analyst queue.

## Product interpretation

This negative result is evidence that the available leakage-safe organizer features did not support a defensible supervised fraud classifier under the pre-registered operational criteria.

Proof of One therefore keeps the statistically defensible parts of the system:
- deterministic safety/policy controls;
- verified banking facts;
- behavioral context;
- transparent escalation;
- conversational evaluation;
- human review.

It does not manufacture a predictive claim that the evidence did not earn.
