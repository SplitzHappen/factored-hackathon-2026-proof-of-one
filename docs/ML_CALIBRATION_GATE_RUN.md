# R4B-C-C2 real calibration/usefulness-gate runner

C-C2 is the first sprint allowed to inspect the real `calibration_gate` segment.

The untouched `test` segment remains sealed.

## Required private inputs

- `ml/private/r4b/analytics.duckdb`
- `ml/private/r4b/analytics_manifest.json`
- `ml/private/r4b/model_selection.json`

The model-selection result must match the canonical C-B SHA-256 frozen in C-C1. A different or modified C-B result fails closed.

## Information boundary

C-C2 may load only:

- `train`;
- `model_selection`;
- `calibration_gate`.

Any request for `test` raises a hard error.

Refit data are exactly `train + model_selection`.

Gate data are exactly `calibration_gate`.

## Symmetric refit

The runner refits:

1. selected `gbdt-small` on train + model_selection;
2. fixed regularized logistic baseline on the same train + model_selection set.

It also evaluates:

- combined-refit prevalence baseline;
- frozen target-free behavioral heuristic.

No hyperparameter is selected or changed in C-C2.

## Logistic convergence diagnostics

The logistic configuration remains frozen even if scikit-learn emits `ConvergenceWarning`.

The result records:

- whether a convergence warning occurred;
- warning message(s);
- fitted `n_iter_`;
- encoded feature count;
- fit duration.

The warning cannot trigger a max-iteration increase or comparator exclusion after C-B.

## GBDT gate scoring

The gate uses the selected GBDT's **uncalibrated decision score** for:

- PR-AUC;
- ROC-AUC;
- top 0.1%, 0.5%, and 1% review budgets;
- 2,000-iteration PR-AUC bootstrap;
- the frozen usefulness decision.

This keeps the ranking gate independent of calibration fitting.

## Platt probability calibration

A one-dimensional Platt/sigmoid calibrator is fit to the GBDT decision score on the calibration/gate segment.

The runner reports:

- raw GBDT probability Brier score;
- Platt-calibrated Brier score on the same segment;
- calibrator coefficient/intercept;
- calibration convergence diagnostics.

Because calibration is fit and diagnosed on the same segment, the calibrated Brier result is explicitly **in-sample calibration diagnostics**, not independent evidence and not a gate criterion.

## Frozen gate

Untouched test is authorized only if every existing frozen condition passes:

1. GBDT PR-AUC bootstrap 95% lower bound > best non-GBDT point PR-AUC;
2. top-0.5% recall >= 5%;
3. top-0.5% precision lift >= 10x gate prevalence.

The best non-GBDT baseline is the maximum PR-AUC among:

- prevalence;
- frozen behavioral heuristic;
- fixed regularized logistic.

## Output

Default private output:

`ml/private/r4b/calibration_gate.json`

It is non-overwritable after observation.

The terminal prints a safe aggregate result including the exact gate decision and:

`test_authorized: true|false`

If false, the supervised fraud model follows the already-approved null/limited-result path and **test stays sealed**.

If true, a separate C-D action is required before any test access.
