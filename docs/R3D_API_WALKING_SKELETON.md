# R3D Synthetic API Walking Skeleton

Status: **implemented before live provider selection**

## Purpose

R3D proves the complete customer-resolution path without making provider selection a
product dependency.

The walking skeleton is intentionally narrow:

`public demo persona -> server-issued session -> deterministic interpretation -> verified
read-only retrieval -> deterministic policy -> deterministic ES/PT response -> optional
verified human handoff`

The current interpreter is a deterministic stub behind the same
`StructuredInterpretationProvider` protocol used by later model adapters.

## Public synthetic data

The default runtime mode is:

`DATA_MODE=synthetic`

On first application use, the service builds a small deterministic DuckDB artifact containing
two public demo personas:

- Lucía — Spanish / Colombia
- Rafael — Portuguese / Brazil

The synthetic bank contains no organizer rows, customer IDs, or transaction values.

It is consumed through the same `BankRepository` used for curated organizer-backed local
runs.

For private/local organizer-backed execution:

`DATA_MODE=curated`

and `BANK_DB_PATH` points at the locally built curated `bank.duckdb`.

The application code and repository boundary do not change.

## Server-issued identity boundary

The client may request only a public `persona_id` and optional response language.

The client cannot supply:

- `customer_id`;
- `tenant_id`;
- role;
- arbitrary banking identity.

`POST /api/demo/sessions` maps the public persona to a server-controlled
`AuthenticatedSession` containing:

- generated UUID session ID;
- fixed demo tenant ID;
- server-issued customer role;
- server-side customer ID;
- selected language.

Tenant, role, persona, customer identity, and language are persisted together in the
operational SQLite store and are immutable for the life of that session.

## HTTP surfaces

### List demo personas

`GET /api/demo/personas`

Returns only public persona metadata and `synthetic_data=true`.

### Create customer session

`POST /api/demo/sessions`

Example request:

```json
{
  "persona_id": "lucia",
  "language": "es"
}
```

The response deliberately omits `customer_id`.

### Resolve customer turn

`POST /api/customer/turn`

Header:

`X-Demo-Session: <server-issued UUID>`

Body:

```json
{
  "message": "¿Cuál es el estado de la transacción DEMO-ES-1001?"
}
```

The server:

1. resolves the persisted session;
2. rejects unknown tenant/role/session context;
3. derives `reference_date` from the server-side persona timezone;
4. calls the provider-neutral interpretation boundary;
5. verifies transaction ownership inside `BankRepository`;
6. applies deterministic policy;
7. returns deterministic ES/PT copy populated only with verified records;
8. persists bounded structured conversation state;
9. persists and re-verifies an escalation ticket when the customer asserts unauthorized activity.

## Current deterministic behavior

Supported answer paths include:

- transaction lookup/status by explicit demo transaction ID;
- recent transaction history.

Deterministic non-answer paths include:

- ambiguous/missing/unowned references -> `CLARIFY` plus support availability;
- prohibited banking mutations -> `ABSTAIN` plus support availability;
- unsupported decline-cause explanation -> `ABSTAIN` without inventing causality;
- explicit customer unauthorized/non-recognition assertion -> `ESCALATE` with verified ticket persistence.

The fraud-specific mandatory escalation trigger remains the customer's unauthorized-activity
assertion. A missing or unowned record by itself does not become a fraud escalation.

## Isolation properties

HTTP tests prove:

- Lucía cannot retrieve Rafael's transactions;
- a cross-customer transaction reference returns no other-customer data;
- malformed and unknown session IDs are rejected;
- a persisted analyst-role session cannot call the customer endpoint;
- a persisted session from another tenant cannot call the customer endpoint;
- `customer_id` never appears in persona/session API responses;
- recent history is restricted to the authenticated customer's records.

## Time semantics

Relative-date interpretation is anchored by a server-authoritative `reference_date`.

For demo mode, that date is derived from the selected persona's configured IANA timezone:

- Lucía: `America/Bogota`
- Rafael: `America/Sao_Paulo`

The interpreter cannot choose or override that timezone.

## Explicit non-goals of R3D

R3D does not:

- select or call a live LLM provider;
- expose organizer data publicly;
- implement the final React UI;
- implement analyst Workbench/Intelligence;
- execute the held-out suite;
- display Behavioral Unusualness;
- implement final rate/cost caps or full session-expiry controls.

Those remain later roadmap items.

## Demo marker

Every public persona/session/customer-turn response that depends on the public demo artifact
includes `synthetic_data=true`.

The UI must preserve a visible **Synthetic demo data** indicator when it is added.
