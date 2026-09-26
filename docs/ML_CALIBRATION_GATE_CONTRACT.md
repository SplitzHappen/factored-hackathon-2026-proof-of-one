# R4B-C-C1 calibration and usefulness-gate contract

C-C1 freezes methodology only. It uses synthetic/contract tests and **does not inspect real calibration-gate outcomes**.

The untouched test remains sealed.

## Upstream frozen result

C-B selected **gbdt-small** using the predeclared highest model-selection PR-AUC rule.

Selected configuration:

- learning rate: 0.08
- iterations: 120
- max leaves: 15
- minimum samples per leaf: 100
- L2: 1.0

No GBDT candidate may be changed after C-B.

C-C is bound to the canonical C-B provenance:
- implementation commit: `9d14bc4df27ed5a4719a98e63d7645ddf380684d`;
- private model-selection result SHA-256: `31825d493fa6bdb7658a0e2f9e44d2ac2d0065c1e33c72690e7a55ca06dfaefe`.

C-C2 must refuse a model-selection result whose SHA-256 does not match this identity.

## Symmetric refit

Before calibration/gate scoring:

- the selected GBDT is refit on **train + model_selection**;
- the fixed regularized logistic baseline is refit on the **same train + model_selection information set**;
- prevalence baseline uses the same combined information set;
- the behavioral heuristic remains target-free and unchanged.

No model is fit on test.

## Logistic convergence-warning policy

C-B's fixed logistic baseline reached its predeclared `max_iter=40` before convergence.

That is a diagnostic limitation, not permission to change the model after seeing C-B results.

C-C therefore:

- preserves the exact frozen logistic configuration;
- captures whether a `ConvergenceWarning` occurs;
- records `n_iter_`;
- reports non-convergence explicitly;
- does not exclude the logistic comparator merely because it warned;
- does not increase `max_iter` or otherwise retune it.

The validation gate compares the GBDT against the **best** non-GBDT baseline, so a weaker/nonconverged logistic cannot lower the hurdle below a stronger prevalence or behavioral baseline.

## Probability calibration

Calibration method: **Platt/sigmoid scaling**.

Implementation contract:

- input: selected GBDT decision score;
- calibrator: one-dimensional logistic regression;
- solver: LBFGS;
- C: 1,000,000;
- max iterations: 1,000;
- tolerance: 1e-8;
- fit only on the calibration/gate segment.

This calibrator exists for probability interpretation/Brier reporting and, if the usefulness gate passes, application to the untouched test.

### Critical anti-optimism rule

The calibration/gate segment is also the only permitted calibration-fitting segment. Therefore:

- GBDT gate PR-AUC and top-review-budget metrics use the **uncalibrated GBDT ranking score**;
- the fitted calibrator cannot improve or alter the gate ranking decision;
- calibrated Brier/probability diagnostics on the calibration-fitting segment are explicitly labeled **in-sample calibration diagnostics**, not independent gate evidence.

## Frozen usefulness gate

The existing metric contract remains binding.

The selected GBDT proceeds to untouched test only if **all three** hold on the calibration/gate segment:

1. 2,000-iteration bootstrap PR-AUC 95% lower bound > best non-GBDT baseline PR-AUC point estimate;
2. top-0.5% recall >= 5%;
3. top-0.5% precision lift >= 10x segment prevalence.

Non-GBDT comparators are exactly:

- prevalence;
- frozen behavioral heuristic;
- fixed regularized logistic.

No threshold changes are allowed after observing gate outcomes.

## Test boundary

C-C code/tooling must not load the test segment.

Only a PASS from the frozen gate can authorize the separate C-D untouched-test unseal action.
