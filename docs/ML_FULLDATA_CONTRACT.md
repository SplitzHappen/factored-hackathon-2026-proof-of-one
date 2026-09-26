# R4B reduced full-data ML contract

This document freezes the exact split and reduced feature semantics selected by the pre-registered R4A signal probe.

## Official chronological segments

All 4,425,008 transactions are assigned by complete timestamp group:

- earliest 70%: base training;
- next 7.5%: model selection;
- next 7.5%: calibration + usefulness gate;
- final 15%: untouched test.

A cutoff is the first complete timestamp group whose cumulative row count reaches the global target fraction. A timestamp group is never split.

The test segment stays sealed unless the calibration/usefulness gate passes.

## Reduced predictor breadth

The R4A probe selected the audited **reduced** path. R4B therefore uses all approved intrinsic features plus only compact lifetime + 24-hour + 30-day behavioral history.

### Intrinsic

- log amount;
- hour of day;
- day of week;
- product tenure;
- explicit currency;
- transaction type;
- transaction category;
- channel;
- merchant category;
- product type.

### Historical

- lifetime prior transaction count;
- explicit no-prior-transaction indicator;
- seconds since previous transaction;
- prior 24h transaction count and amount sum;
- prior 30d transaction count and amount sum;
- lifetime prior mean amount within explicit currency;
- explicit prior-currency-history indicator;
- current amount relative to prior currency mean;
- lifetime prior same-channel count and channel novelty;
- lifetime prior same-merchant-category count and novelty;
- lifetime prior same-transaction-country count and novelty.

Historical means **strictly earlier transaction timestamps**. Transactions at the same timestamp never count as history for one another.

Rows with no prior history are retained. Counts become zero, explicit history flags become false, and genuinely undefined values such as time-since-previous or prior mean remain null for downstream preprocessing.

## Non-predictor analytical columns

The private analytical artifact may retain identifiers/timestamps/segment for row identity and `is_fraud` as the target. They are never passed to the model matrix.

`fraud_score` may be retained only as a separately named reference/evaluation column and is never a Proof of One predictor.

## Explicitly omitted breadth

The reduced path omits:

- 10-minute and 1-hour historical windows;
- 7-day and 90-day historical windows;
- city familiarity;
- raw merchant-name representation;
- broader transaction-type/category frequency families;
- target-derived history or fraud-rate encodings.

This is the pre-authorized descoping ladder after a null-like training-only probe, not post-validation feature selection.

## Still sealed in R4B-A

R4B-A does **not** inspect:
- model-selection performance;
- calibration/gate performance;
- test labels or performance.

The next sub-sprint builds the full leakage-safe analytical artifact from this contract.
