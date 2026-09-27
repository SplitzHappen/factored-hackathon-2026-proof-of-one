# R3E Bilingual Vertical-Slice Proof

Status: **implemented and CI-validated; subsequently hardened by the RA–RD repair series**

R3E does not broaden the product. It proves that the R3D HTTP walking skeleton can execute
the four intended customer-resolution outcomes in both supported languages while preserving
the deterministic authority boundary.

## Proof matrix

| Behavior | Spanish | Portuguese | Expected route |
|---|---:|---:|---|
| Verified normal answer | yes | yes | `ANSWER` |
| Genuine same-customer ambiguity | yes | yes | `CLARIFY` |
| Explicit follow-up lookup after clarification | yes | yes | `ANSWER` |
| Prohibited banking action | yes | yes | `ABSTAIN` + opt-in support handoff available |
| Explicit unauthorized/non-recognition | yes | yes | `ESCALATE` + verified ticket |
| Cross-customer reference | yes | yes | `CLARIFY`, no record/candidate disclosure |

## Genuine ambiguity construction

The public synthetic artifact contains two same-customer transactions with the same amount
for each demo persona:

- Lucía: `DEMO-ES-1003` and `DEMO-ES-1004` at 54,000 COP;
- Rafael: `DEMO-PT-2003` and `DEMO-PT-2004` at 142.75 BRL.

The deterministic demo interpreter extracts an explicitly stated amount into the existing
`InterpretedTransactionQuery` contract. It does not receive banking data.

The existing ownership-scoped `BankRepository.find_transactions` call then determines
whether the query has zero, one, or multiple owned matches.

For multiple matches:

1. policy returns `CLARIFY`;
2. the response exposes at most ten **owned, re-verified candidate transactions**, with
   explicit ID, date, localized amount, and merchant/type context;
3. if more than ten candidates exist, the response states how many of the total are shown;
4. the full candidate-ID set is persisted as informational conversation state;
5. each later turn is nevertheless interpreted independently: an explicit transaction ID
   is treated as a fresh lookup and re-verified against the authenticated customer before
   any answer, whether or not it appeared in the prior candidate set;
6. ordinal follow-ups such as "the second one" are not implemented as candidate-bound state
   transitions and therefore do not resolve a prior candidate automatically.

No model or deterministic interpreter receives the candidate list. Persisted clarification
state records prior context but does not authorize or constrain a later explicit lookup.

## Cross-customer boundary

A transaction ID belonging to the other demo persona is not returned as a clarification
candidate.

The response contains:

- no transaction record;
- no candidate ID;
- no escalation ticket unless the customer separately asserts unauthorized activity.

Missing/unowned references therefore remain distinct from fraud-specific escalation.

## Opt-in support handoff boundary

Prohibited mutation requests are not executed. They produce:

- `ABSTAIN`;
- `prohibited_banking_action`;
- no banking mutation;
- no escalation ticket;
- `handoff_available=true`.

The customer may then call the explicit support-handoff endpoint, which persists a verified
demo support ticket. This proves an actionable support-request path; it does **not** claim that
a live human queue or analyst UI already exists.

This is tested separately in Spanish and Portuguese.

## Verified escalation boundary

Explicit first-person non-recognition/unauthorized assertions produce `ESCALATE`.

The ticket is:

- bound to the authenticated session;
- bound to the ownership-verified transaction when one is referenced;
- persisted;
- re-read;
- marked verified;
- resolved back through the persisted session/customer chain.

The proof test validates the final `VerifiedEscalationContext`, not merely the HTTP ticket ID.

## What the original R3E proof did not establish

R3E was a deterministic synthetic integration proof. At that checkpoint it did **not** establish
production-language generalization, live-LLM quality, native-reviewed Portuguese quality,
held-out performance, production-scale concurrency, final abuse/session controls, analyst
Workbench/Intelligence behavior, or candidate-bound ordinal selection semantics.

Subsequent RA–RD repairs now cover portability, artifact safety, eager startup/data-mode binding,
unauthorized-language breadth, answer/handoff/date/locale semantics, per-visitor tenancy,
session/abuse lifecycle, readiness/body/WAL hardening, and integration/concurrency smoke. They do
not change the remaining evaluation limits: live-provider evidence, blind realistic-language v2,
held-out evaluation, and analyst UI remain separately gated.

## Independent audit status

The standing independent Claude integrated product/API/safety audit was completed after R3E and
returned `REPAIR_BEFORE_CONTINUING`. The RA–RD repair series implements the accepted repair set;
a bounded Claude repair-diff confirmation remains required before the repaired surface is treated
as deployment/submission-stable.
