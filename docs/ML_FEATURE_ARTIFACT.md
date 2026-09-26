# R4B-B full-data feature artifact

The R4B-B builder materializes the frozen reduced feature contract over the complete curated transaction population.

## Private outputs

Default local paths:

- `ml/private/r4b/analytics.duckdb`
- `ml/private/r4b/analytics_manifest.json`

Both remain outside Git.

The builder refuses to overwrite an existing artifact. A later rerun must use an explicitly new artifact/version rather than silently replacing observed analytical state.

## Source binding

Before build:

- curated database SHA-256 must match the curated manifest;
- internal schema/builder metadata must match the manifest;
- customer/product/transaction row counts must match;
- Git working tree must be clean.

The output manifest records:

- feature artifact version;
- feature-contract version + SHA-256;
- implementation commit;
- curated database + curated manifest SHA-256;
- complete official split plan;
- exact model feature names/count;
- output DuckDB SHA-256;
- build duration.

It intentionally does **not** report fraud counts, prevalence, PR-AUC, or any model-selection/gate/test metric.

## Historical implementation

DuckDB windows use `RANGE ... EXCLUDE GROUP`.

This means every historical feature:
- sees only transactions at strictly earlier timestamps;
- excludes all transactions sharing the current timestamp;
- retains all current rows.

Reduced windows:

- lifetime;
- prior 24 hours;
- prior 30 days.

Separate lifetime windows also compute:
- prior amount mean within explicit currency;
- same-channel familiarity;
- same-merchant-category familiarity;
- same-transaction-country familiarity.

First-history rows remain present with zero count/sum history, explicit false history flags, and null values only where a quantity is genuinely undefined.

## Private analytical columns

The feature table contains three kinds of columns:

1. row/provenance keys — transaction/customer/product IDs, timestamp, segment;
2. model predictors — exactly the frozen 26-feature contract;
3. offline evaluation/reference columns — `is_fraud` target, `fraud_score_reference`, and `customer_country_eval`.

Only the model predictor names from the frozen contract may be passed to model fitting.

## Verification

Before reporting success the builder:

- verifies total and unique transaction rows;
- verifies exact segment row counts;
- verifies required feature nullability;
- verifies history/novelty flag invariants;
- checks that every customer's earliest timestamp group has zero prior history;
- independently recomputes lifetime/24h/30d/familiarity history for a deterministic source-backed sample;
- checkpoints and hashes the artifact;
- reopens the persisted artifact and repeats verification against the source database.

Synthetic CI additionally changes every target label and organizer reference score while holding transaction facts fixed and requires all 26 model features to remain identical.

R4B-B does not inspect supervised performance. Model fitting begins only in R4B-C.
