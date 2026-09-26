# Runtime Behavioral Evidence Service

This module connects the frozen Behavioral Unusualness contract to verified
transaction access paths. It does not create a new risk model and does not
change any deterministic policy rule.

## Access paths

### Customer session

`BehavioralEvidenceService.for_customer_session(...)` requires the complete
server-controlled `AuthenticatedSession` to match the persisted operational
session exactly. The caller supplies a transaction ID, but the banking
repository returns evidence facts only when both the transaction and its linked
product belong to that persisted customer.

### Verified escalation ticket

`BehavioralEvidenceService.for_verified_escalation_ticket(...)` accepts only a
ticket ID. The operational store resolves:

`ticket -> persisted session -> customer -> transaction`

only for a persistence-verified ticket with a transaction reference. The
banking repository then re-verifies transaction/product ownership before any
behavioral facts are calculated. There is no analyst-side arbitrary customer-ID
or transaction-ID lookup in this service.

The later API vertical slice is responsible for placing the server-controlled
analyst role/tenant boundary in front of this application service. R4C does not
change the runtime SQLite schema.

## Historical semantics

For a target transaction at time `t`, evidence facts use only transactions for
the same customer with timestamps strictly earlier than `t`. Same-timestamp
peers and future transactions are excluded.

The service derives only the frozen D-B inputs:

- prior lifetime transaction count;
- target-product tenure at the target timestamp;
- same-currency amount ratio when a positive baseline exists;
- channel novelty;
- merchant-category presence/novelty;
- transaction-country novelty;
- prior 24-hour transaction count;
- prior 30-day transaction count.

These inputs are passed unchanged to `compute_behavioral_evidence`. Synthetic
demo databases therefore use the same formulas, availability rules, composite
thresholds, labels, and disclaimer as organizer-backed runtime data.

## Explicit non-authority

The runtime query never selects `is_fraud` or organizer `fraud_score`.
Behavioral evidence remains descriptive only. It cannot:

- classify or adjudicate fraud;
- represent a fraud probability or fraud-risk score;
- trigger or suppress mandatory escalation;
- prioritize an analyst queue;
- authorize a banking action.

Required display meaning:

> Descriptive behavioral evidence only; not a fraud probability or fraud determination.

No HTTP endpoint is added in this sprint. API exposure belongs to the later
tenant/role-bound vertical-slice work.
