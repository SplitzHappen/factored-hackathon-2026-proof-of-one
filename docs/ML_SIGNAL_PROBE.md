# R4A training-only ML signal probe

This probe decides **feature-engineering breadth only**. It is not the final fraud model, not the validation/gate experiment, and not test evidence.

## Data boundary

The probe may use:
- timestamp counts from the complete dataset only to define a chronological 70% training cutoff while keeping identical timestamps in one partition;
- labels and feature values only from the earliest 70% training region.

It may not inspect:
- fraud prevalence after the training cutoff;
- validation/gate labels or model performance;
- untouched test labels or model performance.

Inside the earliest 70%, the probe creates a second chronological split:
- earliest 80% of the training region: internal probe training;
- latest 20% of the training region: internal probe holdout.

Identical timestamp groups remain intact.

## Full-training descriptive profiles

The complete earliest-70% region is used for aggregate signal profiles:
- channel;
- transaction type;
- transaction category;
- merchant category;
- hour of day;
- day of week;
- amount decile;
- channel novelty;
- merchant-category novelty;
- transaction-country novelty.

Novelty is defined by whether the transaction timestamp equals the customer's first timestamp for that value. Same-timestamp peers are all treated as first-observed; one peer never becomes historical evidence for another peer at the same timestamp.

Organizer `fraud_score` is never a predictor. The probe reports only its training-region coverage and label prevalence among score-present/score-missing rows as a provenance diagnostic.

## Quick intrinsic GBDT

The quick probe model uses only the approved intrinsic predictors:

Numeric:
- log amount;
- hour of day;
- day of week;
- product tenure at transaction time.

Categorical:
- explicit currency;
- transaction type;
- transaction category;
- channel;
- merchant category;
- product type.

Target:
- `is_fraud`.

Explicitly excluded:
- `fraud_score`;
- transaction status;
- customer country;
- detected accent;
- identifiers;
- current balance;
- last-updated / last-transaction snapshot fields;
- target-derived history;
- future rows/labels.

For speed, the quick GBDT uses a deterministic target-blind 1-in-4 transaction-ID hash sample independently inside the internal training and internal holdout periods. All descriptive profiles still use the complete earliest-70% region. The later R4B experiment returns to the complete dataset.

The model is a scikit-learn histogram gradient-boosted classifier using class weighting and categorical encoding. Scikit-learn remains an offline/development dependency and is not installed in the production FastAPI Docker image.

## Pre-registered breadth rule

This rule is frozen before running the organizer data.

Use **full feature breadth** in R4B only if the quick intrinsic GBDT internal holdout has:

1. at least **100 fraud-positive rows**;
2. PR-AUC at least **3x** the internal-holdout prevalence; and
3. recall of at least **3%** inside the top **0.5%** review budget.

Otherwise use the **reduced feature set** rather than chasing signal.

This is only a complexity-budget rule. It is not permission to present the classifier as operationally useful. The much stricter validation/gate and untouched-test survival criteria frozen in the audited expansion design remain authoritative for that claim.

## Result artifact

The full probe output is written locally to git-ignored:

`ml/private/r4a_signal_probe.json`

The terminal prints a safe aggregate subset only:
- source hashes;
- split boundaries/counts;
- training prevalence and organizer-score coverage;
- quick GBDT rare-event metrics;
- breadth decision.

No customer IDs, product IDs, transaction IDs, merchant names, or raw banking rows are printed or committed.
