# R3D Synthetic API Walking Skeleton

Status: **implemented before live provider selection**

## Purpose

R3D proves the complete customer-resolution path without making provider selection a
product dependency.

The walking skeleton is intentionally narrow:

`public demo persona -> server-issued session -> deterministic interpretation -> verified
read-only retrieval -> deterministic policy -> deterministic ES/PT response -> optional
verified escalation/support-ticket handoff`

The current interpreter is a deterministic stub behind the same
`StructuredInterpretationProvider` protocol used by later model adapters.

## Public synthetic data

The default runtime mode is:

`DATA_MODE=synthetic`

During application startup, the service ensures a small deterministic DuckDB artifact exists containing
two public demo personas:

- Lucía — Spanish / Colombia
- Rafael — Portuguese / Brazil

The synthetic bank contains no organizer rows, customer IDs, or transaction values.

It is consumed through the same `BankRepository` used for curated organizer-backed local
runs.

For private/local organizer-backed execution:

`DATA_MODE=curated`

and `BANK_DB_PATH` points at the locally built curated `bank.duckdb`. A separate curated runtime SQLite path is used.

At startup, the runtime reads immutable `build_metadata` from the DuckDB and fails closed if the configured mode does not match the artifact identity. The operational SQLite store is also bound to that resolved mode so synthetic and curated session/ticket state cannot be silently mixed. The default Docker Compose surface remains synthetic-only and does not mount curated organizer-derived data.

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
- fresh opaque per-visitor tenant ID;
- server-issued customer role;
- server-side customer ID;
- selected language.

Tenant, role, persona, customer identity, and language are persisted together in the
operational SQLite store and are immutable for the life of that session. Every escalation
ticket also persists the originating tenant ID and is resolved only when that tenant still
matches the immutable session identity.

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
2. rejects unknown sessions and non-customer roles while preserving the persisted tenant binding;
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

- genuine owned ambiguity -> `CLARIFY` with owned/re-verified candidate context and no automatic handoff flag;
- missing/unowned supported references -> `CLARIFY` with an actionable opt-in support-handoff path;
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
- separate public demo sessions receive distinct server-issued tenants;
- an existing session ID cannot be rebound to another tenant or role;
- verified escalation-ticket listing is tenant-scoped and joins back through the immutable
  session tenant; direct ticket-tenant tampering therefore fails closed;
- `customer_id` never appears in persona/session API responses;
- recent history is restricted to the authenticated customer's records.

## Session and abuse lifecycle

The public synthetic API now enforces bounded operational state:

- active customer sessions expire **4 hours** after server issuance;
- customers may explicitly revoke their current demo session with `DELETE /api/demo/session`;
- expired or revoked sessions cannot call customer turn/handoff endpoints;
- verified support tickets remain internally reviewable during the retained tenant window even
  after customer authentication expires;
- tenant/session/ticket state is retained for at most **24 hours** from session creation before
  cleanup;
- new demo-session creation is limited by persistent peer-scoped counters (default:
  **10 successful sessions per hour**);
- authenticated customer requests are limited by persistent per-session counters (default:
  **60 requests per minute**);
- escalation creation is retry-safe by session + transaction + reason and allows at most
  **5 distinct tickets per session**;
- abuse-limit state is SQLite-backed and therefore survives process restarts;
- limit failures return HTTP `429`; expired/revoked sessions return HTTP `401`.

These controls bound the public demo's writable SQLite growth and prevent a failed turn followed
by a client retry from creating duplicate verified support tickets.

## Deployment-readiness and request safety

The deployment surface separates liveness from dependency readiness:

- `GET /health` reports process liveness only;
- `GET /ready` revalidates the banking artifact identity/schema, runtime schema and
  data-mode binding, runtime-store writability, and SQLite WAL mode;
- readiness reports the active `data_mode` and `synthetic_data` marker and returns HTTP
  `503` when a required dependency is unavailable or inconsistent;
- the container health check targets `/ready`, not `/health`.

All HTTP request bodies are capped at **64 KiB before request-model parsing**. Oversized
bodies return HTTP `413` without echoing the payload. Validation errors return bounded
field/type/message metadata and deliberately omit FastAPI/Pydantic's rejected `input`
value.

The operational SQLite database runs in **WAL** mode on a single-host/local-volume
deployment. Session authentication and per-session throttling share one SQLite
transaction, reducing one connection from the authenticated request path. The subsequent
RD4 assurance suite covers concurrent customer flows, locked-SQLite failure, mixed ownership,
and a running production-container smoke without changing this single-host/local-volume
storage assumption.

## Integration and concurrency assurance

The post-hardening integration suite exercises the boundaries that unit and injected-context
tests do not cover by themselves:

- a fresh Python process imports the module-level `app`, reads environment settings, runs the
  real FastAPI lifespan, builds the synthetic artifact/runtime store, and reaches `/ready`;
- missing `X-Demo-Session` headers return an intentional HTTP `401` rather than FastAPI's
  default validation `422`;
- a write-locked operational SQLite store fails closed as HTTP `503` with generic copy;
- eight concurrent customer flows share the WAL-backed runtime store while preserving
  customer/tenant isolation;
- a deliberately inconsistent mixed-ownership transaction row cannot enter another
  customer's clarification candidates or response text;
- explicit unauthorized assertions retain escalation precedence over ambiguity and prohibited
  action requests;
- prompt-injection wording cannot bypass the deterministic prohibited-action policy;
- HTTP clarification with twelve owned matches exposes only ten candidates and states
  `Mostrando 10 de 12 resultados.`;
- unknown intents abstain without banking-record disclosure;
- Linux CI starts the production container and performs a bounded readiness -> session ->
  customer-turn smoke sequence against the running image.

These tests remain synthetic-only and do not execute organizer-backed rows, private development
prompts, live providers, or held-out evaluation cases.

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
- implement live-provider cost caps (required in the same change that wires a live provider).

Those remain later roadmap items.

## Demo marker

Every public persona/session/customer-turn response that depends on the public demo artifact
includes `synthetic_data=true`.

The UI must preserve a visible **Synthetic demo data** indicator when it is added.
