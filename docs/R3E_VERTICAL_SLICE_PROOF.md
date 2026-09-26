# R3E Bilingual Vertical-Slice Proof

Status: **candidate proof surface; validate in CI before merge**

R3E does not broaden the product. It proves that the R3D HTTP walking skeleton can execute
the four intended customer-resolution outcomes in both supported languages while preserving
the deterministic authority boundary.

## Proof matrix

| Behavior | Spanish | Portuguese | Expected route |
|---|---:|---:|---|
| Verified normal answer | yes | yes | `ANSWER` |
| Genuine same-customer ambiguity | yes | yes | `CLARIFY` |
| Multi-turn selection of one candidate | yes | yes | `ANSWER` |
| Prohibited banking action | yes | yes | `ABSTAIN` + human handoff available |
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
2. the response exposes at most ten **owned, verified transaction IDs only**;
3. those IDs are persisted in bounded conversation state;
4. the customer selects one explicit ID in the next turn;
5. the existing interpretation post-check re-verifies that ID against the authenticated
   customer before any answer;
6. conversation state transitions from `clarification_required=true` to `false`.

No model or deterministic interpreter receives the candidate list.

## Cross-customer boundary

A transaction ID belonging to the other demo persona is not returned as a clarification
candidate.

The response contains:

- no transaction record;
- no candidate ID;
- no escalation ticket unless the customer separately asserts unauthorized activity.

Missing/unowned references therefore remain distinct from fraud-specific escalation.

## Human handoff boundary

Prohibited mutation requests are not executed. They produce:

- `ABSTAIN`;
- `prohibited_banking_action`;
- no banking mutation;
- no escalation ticket;
- `handoff_available=true`.

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

## What R3E does not prove

R3E is a deterministic synthetic integration proof. It does **not** establish:

- production-language generalization;
- live-LLM quality;
- native-reviewed Portuguese quality;
- held-out performance;
- production-scale concurrency;
- final abuse/rate/session-expiry controls;
- analyst Workbench/Intelligence behavior.

Those claims remain governed by their separate evaluation and audit gates.

## Independent audit gate

After this proof is merged, the project must stop and run the standing independent Claude
**integrated product/API/safety** audit before the product surface is treated as
submission-stable.
