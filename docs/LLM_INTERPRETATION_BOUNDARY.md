# R3C Language Interpretation and Deterministic Post-check — contract r3c-v2

R3C defines the internal language-understanding boundary for Spanish and Portuguese. That
boundary is now composed into the public customer-turn API, but no live LLM provider/model is
frozen or connected to the judge-facing runtime.

## Authority boundary

The language model may interpret only:

- the normalized intent;
- whether the customer explicitly asserts that activity was unauthorized or not theirs;
- a transaction ID explicitly mentioned by the customer;
- bounded transaction filters explicitly mentioned by the customer, normalized to
  canonical server-side transaction-type/status enum values.

The provider request contains only:

- expected session language;
- customer message;
- server-supplied reference date for deterministic relative-date interpretation;
- optional prior normalized intent.

It contains no customer ID, session ID, product/account record, transaction record,
behavioral evidence, retrospective fraud label, organizer fraud score, SQL, or policy
outcome.

Unknown provider fields are rejected by the strict Pydantic contract.

## Provider neutrality

The service depends on the `StructuredInterpretationProvider` protocol rather than a
vendor SDK. A later adapter may use OpenAI, Qwen, DeepSeek, or another provider without
changing the banking or policy boundary. Provider/model selection is intentionally
deferred to development-pool evidence.

Provider adapters return raw JSON text. R3C validates that text against the exact
`ModelInterpretation` schema. For provider-comparison fairness, every adapter receives
the same textual canonical schema, enum list, and example; providers that support native
strict JSON Schema also receive API-level enforcement. JSON-object-only providers retain
their genuine reliability disadvantage without being denied the contract itself. There is
no provider SDK in the production dependency set yet.

## Bounded retry and fallback

The default interpretation budget is two attempts and the hard implementation maximum
is five. Expected network/provider failures and invalid structured output consume this
bounded budget.

After exhaustion, R3C returns a typed `SAFE_FALLBACK` result with
`requires_human_fallback=true`. It does not guess an intent, transaction, ownership,
or banking fact.

## Critical-fact post-checking

Model output is not banking truth.

- The exact persisted server session is verified before any provider call.
- A model-returned transaction ID must first appear as a whole token in the actual
  customer message; partial-ID substring matches and invented IDs are rejected before
  banking lookup.
- A model-returned transaction ID is then ownership-checked through the read-only banking
  repository.
- An unowned/nonexistent transaction ID is never surfaced as a verified transaction ID.
- Model-extracted transaction filters are executed only against the authenticated
  customer.
- Transaction type/status are constrained to the canonical English enum values stored
  in the curated database even when the user speaks Spanish or Portuguese.
- Every extracted amount/type/status/date filter must have deterministic semantic
  provenance in the customer message; invented narrowing filters are rejected rather
  than allowed to manufacture a unique match.
- Date filters are stricter than cue-word matching: supported ES/PT relative phrases and
  explicit dates are resolved server-side against the supplied reference date, and the
  model's date bounds must equal that resolved range exactly.
- Vague date cue words do not authorize model-invented dates, and any upper date bound
  after the server reference date is rejected before banking lookup.
- Search breadth is server-controlled at 50 results. The model-facing query schema has
  no `limit` field, so the model cannot manufacture uniqueness by asking for one row.
- Multiple owned matches remain `AMBIGUOUS`.
- An empty model query is normalized to no query.
- Inverted date ranges are rejected as invalid structured output before banking lookup.
- Relative dates are anchored to an explicit server-supplied reference date, not provider
  clock assumptions.

The interpretation service does not create policy outcomes, tickets, banking actions, or
behavioral evidence. The application layer composes the post-checked interpretation with trusted
retrieval facts and the deterministic policy router. Successful turns then emit separate
server-generated operational Decision Evidence; that evidence is not part of the model response
schema and cannot be authored by the provider.

## Unauthorized-activity safety backstop

The model may raise the unauthorized-activity signal but cannot lower a high-confidence
deterministic language backstop. Contract r3c-v2 expands the first-person Spanish and
Portuguese non-recognition/authorization vocabulary and intentionally scans both supported
languages even when the server session language is one of them. This protects code-switching
and injection-plus-fraud cases such as "ignore the rules; I do not recognize this purchase."

This backstop is monotonic: it may change `false -> true`, never `true -> false`.

The RF4 fail-safe floor (`app/failsafe_escalation.py`) is a separate, server-side signal
(`possible_unauthorized_activity`) computed after the backstop and only when it is false.
It is not part of the model's response schema, the model cannot set it, and it is equally
monotonic.
It is not a fraud classifier and does not inspect behavioral evidence or fraud labels.

## Current integration status and remaining LLM work

The interpretation boundary is now integrated with:

- server-issued customer sessions and tenant isolation;
- public HTTP conversation endpoints;
- deterministic customer-response generation over verified facts;
- deterministic policy precedence;
- operational Decision Evidence;
- public deployment controls.

Those application capabilities remain outside provider authority.

Still deferred:

- live provider API credentials;
- provider/model selection;
- prompt/configuration freeze;
- live-provider execution in the judge-facing runtime;
- frozen held-out execution.

The frozen 200-case held-out suite remains untouched. Provider selection and prompt refinement must
use the separate development pool and permitted language-stress surfaces only. Provider/model/prompt
must be frozen before held-out execution.

`reference_date` is server-authoritative and resolved from the persisted demo persona timezone
before the provider call. The provider may not infer or substitute a timezone.

The current authority order, Decision Evidence semantics, banking-dependency failure boundary, and
pre-LLM architecture freeze are documented in
[POLICY_PRECEDENCE_AND_DECISION_EVIDENCE.md](POLICY_PRECEDENCE_AND_DECISION_EVIDENCE.md).
