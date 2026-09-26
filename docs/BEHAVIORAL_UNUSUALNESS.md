# Behavioral Unusualness fallback contract

Proof of One's supervised fraud model failed its frozen usefulness gate. The product therefore uses **descriptive behavioral evidence**, not a replacement predictive fraud score.

This contract is target-free and frozen before any association reporting for the fallback.

## Purpose

The Human Resolution Workbench may show:
- six transparent component evidence cards;
- an optional 0–100 **Behavioral Unusualness** composite when enough history exists.

The composite describes deviation from the customer's own prior transaction behavior. It is **not**:
- a fraud probability;
- a fraud-risk score;
- a fraud determination;
- a queue-priority score;
- an escalation trigger.

Required UI disclaimer:

> Descriptive behavioral evidence only; not a fraud probability or fraud determination.

## Inputs

All inputs come from the already leakage-safe, strictly-prior feature pipeline.

Allowed components:

1. amount surprise;
2. channel novelty;
3. merchant-category novelty;
4. transaction-country novelty;
5. 24-hour velocity;
6. 30-day velocity.

No `is_fraud`, organizer `fraud_score`, final transaction status, future data, customer identifiers, or learned target-derived values may enter this calculation.

## Component formulas

### Amount surprise

Uses the current amount divided by the customer's prior same-currency mean amount.

`score = min(abs(log2(ratio)) / 2, 1)`

Examples:
- 1x prior mean -> 0;
- 2x or 0.5x -> 0.5;
- 4x or 0.25x -> 1.

The symmetry is deliberate: this measures deviation, not fraud direction.

If no prior same-currency history exists, the component is unavailable.

### Channel novelty

Binary:
- previously observed -> 0;
- first observed in prior history -> 1.

With no prior transaction history, the component is unavailable rather than automatically unusual.

### Merchant-category novelty

Binary:
- previously observed -> 0;
- first observed -> 1.

If the current transaction has no merchant category, the component is unavailable.

With no prior transaction history, the component is also unavailable.

### Transaction-country novelty

Binary:
- previously observed -> 0;
- first observed -> 1.

With no prior transaction history, the component is unavailable.

### 24-hour velocity

Requires at least five prior transactions within the prior 30-day window.

Baseline:

`expected_24h = prior_30d_count / 30`

Rate ratio:

`prior_24h_count / expected_24h`

Score:
- <=1x recent daily rate -> 0;
- elevated rates increase logarithmically;
- saturates at 1 at 8x recent daily rate.

This component measures elevated activity only; unusually quiet periods do not increase the score.

### 30-day velocity

Requires:
- at least five prior lifetime transactions;
- at least 60 days of product tenure.

Long-run baseline:

`expected_30d = prior_lifetime_count / product_tenure_days * 30`

Score:
- <=1x long-run rate -> 0;
- elevated rates increase logarithmically;
- saturates at 1 at 4x the tenure-adjusted long-run rate.

## Composite

Behavioral Unusualness is:

`100 * unweighted mean(available component scores)`

No learned weights are permitted.

A composite is shown only when:
- at least 5 prior lifetime transactions exist; and
- at least 4 of the 6 components are available.

Otherwise:
- composite = unavailable;
- component facts may still be shown;
- the UI must state that behavioral history/coverage is insufficient.

This cold-start rule prevents a new customer from appearing maximally unusual merely because everything is first-observed.

## Presentation bands

Bands are descriptive UI labels only:

- 0–<25: low observed deviation;
- 25–<50: moderate observed deviation;
- 50–<75: elevated observed deviation;
- 75–100: high observed deviation.

They are not operating thresholds and cannot affect policy/routing.

## Runtime authority

Behavioral evidence has no authority to:
- classify fraud;
- force escalation;
- suppress escalation;
- prioritize analyst queues;
- change customer identity/ownership;
- authorize banking actions.

Mandatory unauthorized-activity escalation remains driven by the customer's assertion and deterministic policy.

## Offline association reporting

After this formula is frozen, Proof of One may evaluate the index against `is_fraud` **only for transparent association reporting** on the already-open calibration/gate segment.

That evaluation:
- may not fit weights;
- may not alter formulas;
- may not tune bands;
- may not authorize predictive language;
- may not unseal the untouched test.

If association is weak, Resolution Intelligence must state that explicitly.

## Provenance

This contract is downstream of the public supervised-ML null-result contract and includes that contract's SHA-256 in its own deterministic identity.
