# R4B-C-A supervised metric and baseline contract

This sub-sprint freezes evaluation arithmetic **before** model-selection or calibration-gate performance is inspected.

## Baselines

R4B-C compares the proposed GBDT against:

1. **Prevalence baseline** — a constant probability equal to training-region prevalence.
2. **Deterministic behavioral heuristic** — target-free score defined below.
3. **Regularized logistic regression** — fitted later under the same information boundary as the GBDT.

The organizer `fraud_score` is not a Proof of One baseline for the validation gate. It remains a separately labeled reference-only comparison if later retained.

## Frozen deterministic behavioral heuristic

The score is a weighted sum in [0, 1]:

- 35% amount surprise versus prior same-currency mean;
- 15% channel novelty;
- 10% merchant-category novelty;
- 15% transaction-country novelty;
- 15% prior-24h velocity;
- 10% prior-30d velocity.

Amount surprise:
- <=1x prior mean => 0;
- 2x => one-third of the component;
- 4x => two-thirds;
- >=8x => full component;
- no prior same-currency history => 0.

Velocity uses log saturation:
- 24h component saturates at 5 prior transactions;
- 30d component saturates at 20 prior transactions.

This formula is target-free and cannot be tuned after model-selection/gate outcomes are observed.

## Rare-event metrics

Headline:
- PR-AUC;
- recall at top 0.5% review budget;
- precision and precision lift at the same budget.

Also report:
- ROC-AUC;
- top 0.1%, 0.5%, and 1% review-budget metrics;
- false positives per detected fraud;
- Brier score only for quantities represented as probabilities.

Accuracy is not a headline metric.

## Fixed review-budget tie handling

When rows have equal score, exact top-k membership is resolved by a deterministic target-blind 64-bit BLAKE2b hash of:

`transaction_id | proof-of-one-eval-tie-v1`

This prevents label-aware or accidental ordering from changing fixed-budget metrics.

## PR-AUC uncertainty

The validation gate uses a **2,000-iteration Poisson bootstrap** with fixed seed `20260926`.

The implementation groups identical score thresholds and samples positive/negative multiplicities from their empirical Poisson rates. This is the Poisson-bootstrap analogue of row resampling and avoids repeatedly sorting hundreds of thousands of rows.

The point estimate remains scikit-learn average precision.

## Frozen calibration/usefulness gate

On the calibration/gate segment, the GBDT proceeds to untouched test only if **all** hold:

1. GBDT PR-AUC bootstrap 95% lower bound > best non-GBDT baseline PR-AUC point estimate;
2. top-0.5% recall >= 5%;
3. top-0.5% precision lift >= 10x segment prevalence.

No threshold may be changed after outcomes are observed.

## Frozen untouched-test survival rule

If and only if the validation gate passes, test is unsealed once. Prominent supervised display requires **all**:

1. test GBDT PR-AUC > best non-GBDT test baseline point estimate;
2. test GBDT PR-AUC >= 50% of calibration/gate GBDT PR-AUC;
3. top-0.5% test recall >= 2.5%;
4. top-0.5% test precision lift >= 5x test prevalence.

Failing any condition preserves the supervised experiment as a limited/null result and activates the behavioral-evidence fallback.

## C-A data boundary

C-A contains no organizer performance result and performs no model fit. Tests use synthetic arrays only.

The next sub-sprint, C-B, may use:
- training segment labels for fitting;
- model-selection segment labels for hyperparameter/model selection.

C-B still may not inspect calibration-gate or test outcomes.
