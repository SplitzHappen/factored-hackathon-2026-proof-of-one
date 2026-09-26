# R4B-C-B bounded model selection

C-B is the only sub-sprint allowed to inspect the official `model_selection` segment.

It may read:
- `train` for fitting;
- `model_selection` for baseline/candidate selection.

It may **not** read:
- `calibration_gate`;
- `test`.

The untouched test remains sealed.

## Predeclared model surface

### Target-free baselines

- training-prevalence constant score;
- frozen deterministic behavioral heuristic from C-A.

### Regularized logistic baseline

Implementation:
- `SGDClassifier(loss="log_loss")`;
- L2 penalty;
- alpha `1e-4`;
- balanced class weights;
- max 40 epochs;
- tolerance `1e-4`;
- averaged coefficients;
- seed `20260926`.

Preprocessing:
- numeric features: train-fitted standardization;
- categorical features: train-fitted one-hot encoding;
- minimum categorical frequency: 50;
- unseen selection categories are ignored.

The logistic configuration is fixed before model-selection results. It is a baseline, not a hyperparameter search.

### Histogram GBDT candidates

All candidates use:
- scikit-learn `HistGradientBoostingClassifier`;
- balanced class weights;
- `early_stopping=False`;
- seed `20260926`;
- train-fitted ordinal categorical encoding;
- unknown later categories treated as missing;
- minimum categorical frequency 50.

Candidate order is simplest to more complex:

1. **gbdt-small**
   - learning rate 0.08
   - 120 iterations
   - 15 leaves
   - min leaf 100
   - L2 1.0

2. **gbdt-medium**
   - learning rate 0.06
   - 160 iterations
   - 31 leaves
   - min leaf 100
   - L2 1.0

3. **gbdt-regularized**
   - learning rate 0.05
   - 200 iterations
   - 31 leaves
   - min leaf 200
   - L2 5.0

No candidate may be added after model-selection outcomes are observed.

## Selection rule

Choose the candidate with the highest model-selection PR-AUC.

If candidates have exactly equal PR-AUC, retain the earlier candidate in the predeclared order. This is a fixed simpler-model tie break.

Top-0.5% recall/precision are reported but do not alter candidate selection.

## Full-data use

The complete official training segment is used for fitting:
- 3,097,506 rows in the verified real artifact.

The complete official model-selection segment is used for selection:
- 331,876 rows in the verified real artifact.

There is no training subsample in C-B.

## Dependency choice

C-B uses the already-validated scikit-learn histogram GBDT fallback rather than adding LightGBM.

This is allowed by the audited design and is preferred on the reduced path because:
- the training-only R4A probe was null-like;
- the competition schedule favors a bounded, reproducible experiment;
- scikit-learn 1.9.1 is already pinned and CI-validated;
- adding a new native training dependency would not be justified by current evidence.

This choice does not change the frozen usefulness gate.

## Result artifact

Default private output:

`ml/private/r4b/model_selection.json`

The result records:
- application implementation commit;
- Python/DuckDB/scikit-learn versions;
- feature-artifact and feature-manifest SHA-256;
- feature-contract SHA-256;
- metric-contract SHA-256;
- model-selection-contract SHA-256;
- train/model-selection counts and prevalence;
- prevalence/heuristic/logistic point metrics;
- all three GBDT candidate metrics;
- selected GBDT configuration;
- fit durations.

It contains no raw transactions.

The output is non-overwritable after observation.

## Next step

C-B does not persist a fitted model. C-C uses the selected configuration to refit:
- GBDT on train + model-selection;
- logistic on the same train + model-selection information set.

Only then may C-C read the calibration/gate segment.

C-C still does not read test unless the frozen usefulness gate passes.
