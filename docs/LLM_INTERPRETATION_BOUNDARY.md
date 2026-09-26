# R3C Language Interpretation and Deterministic Post-check

R3C adds the internal language-understanding boundary for Spanish and Portuguese. It
does **not** expose a public HTTP endpoint and it does not freeze an LLM provider.

## Authority boundary

The language model may interpret only:

- the normalized intent;
- whether the customer explicitly asserts that activity was unauthorized or not theirs;
- a transaction ID explicitly mentioned by the customer;
- bounded transaction filters explicitly mentioned by the customer.

The provider request contains only:

- expected session language;
- customer message;
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
`ModelInterpretation` schema. There is no provider SDK in the production dependency
set yet.

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
- A model-returned transaction ID is ownership-checked through the read-only banking
  repository.
- An unowned/nonexistent transaction ID is never surfaced as a verified transaction ID.
- Model-extracted transaction filters are executed only against the authenticated
  customer.
- Search breadth is server-controlled at 50 results. The model-facing query schema has
  no `limit` field, so the model cannot manufacture uniqueness by asking for one row.
- Multiple owned matches remain `AMBIGUOUS`.
- An empty model query is normalized to no query.
- Inverted date ranges are rejected as invalid structured output before banking lookup.

The service does not create policy outcomes, tickets, banking actions, or behavioral
evidence. R3D will compose the post-checked interpretation with deterministic retrieval
facts and the already-frozen policy router.

## Unauthorized-activity safety backstop

The model may raise the unauthorized-activity signal but cannot lower a high-confidence
deterministic language backstop. R3C currently recognizes a deliberately narrow set of
first-person Spanish and Portuguese phrases such as "no reconozco / no fui yo" and
"não reconheço / não fui eu".

This backstop is monotonic: it may change `false -> true`, never `true -> false`.
It is not a fraud classifier and does not inspect behavioral evidence or fraud labels.

## Deferred to R3D and later evaluation

R3C deliberately does not add:

- tenant/analyst roles;
- HTTP conversation endpoints;
- provider API credentials;
- provider/model selection;
- customer response generation;
- public deployment rate limits;
- held-out prompt execution.

The frozen 200-case held-out suite remains untouched. Provider selection and prompt
refinement must use the separate development pool only, then freeze before held-out
execution.
