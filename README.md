# Proof of One — Factored AI & Data Hackathon 2026

Proof of One is a bounded account/payment customer-support prototype for the Factored AI & Data Hackathon 2026.

## Current implementation stage

Pre-LLM architecture freeze candidate after the signal-box UI, full interpreter-to-policy
replay evidence, first-class Decision Evidence / ACT -> VERIFY, and explicit trusted-bank
dependency fail-closed handling. The public runtime remains deliberately deterministic and uses
synthetic data; no live LLM is connected in the judge-facing runtime.

The final submission still requires external deployment verification, a 4–6 slide presentation,
and a video pitch no longer than 3 minutes. Blind realistic-language v2, held-out uplift claims,
live-provider execution, and production/pilot readiness are not part of the shipped claim set.

The application currently contains:
- a judge-facing signal-box web UI over the live local/public API, with public synthetic demo personas, fresh server-issued per-visitor tenants, explicit customer roles, four-hour session TTL/revocation, and bounded operational retention;
- strict Pydantic boundary contracts;
- Docker packaging;
- a deterministic curated-data builder for minimized trusted banking data;
- a bounded read-only DuckDB query layer with customer-isolation checks and an operational transaction projection that excludes retrospective fraud labels/reference scores;
- a separate writable SQLite operational store for tenant/role-bound authenticated demo sessions, bounded conversation state, and structured support/escalation tickets;
- a deterministic policy/router with fixed `ANSWER`, `CLARIFY`, `ABSTAIN`, and `ESCALATE` outcomes and intentional authority-ordered precedence;
- a strict server-generated Decision Evidence envelope that exposes interpretation status, controlling check/reason, action, execution status, and observable verification codes without exposing model chain-of-thought;
- persistence verification that re-reads an escalation ticket before the runtime may report success;
- a sanitized trusted-bank dependency failure contract that returns HTTP 503, claims no normal route in the failure payload, and releases no banking fact when the DuckDB/banking layer is unavailable;
- tests proving that model-facing transaction queries cannot supply a `customer_id`, conversation state cannot rebind identity, and the runtime store cannot contain authoritative banking tables;
- a provider-neutral Spanish/Portuguese interpretation boundary with strict typed extraction, bounded retries/fallback, deterministic transaction-reference verification, and no model authority over identity, ownership, banking truth, policy, or behavioral evidence;
- a deterministic stub interpreter behind that same provider protocol so end-to-end product integration does not wait for live provider selection;
- deterministic Spanish/Portuguese customer responses over verified facts, with cross-customer non-disclosure, verified escalation/support-ticket persistence, and an explicit customer-requested support-handoff endpoint;
- a frozen descriptive Behavioral Unusualness fallback after the supervised fraud-risk model failed its pre-registered usefulness gate;
- an RF5 replay guardrail that now exercises the real deterministic interpreter -> verified interpretation -> authoritative `route_policy()` path over the public/non-held-out replay cases.

No live LLM provider/model is connected to the frozen judge-facing runtime.

## Data & evaluation

Proof of One is deliberately positioning **data engineering, statistical discipline, and evidence-based product decisions** as first-class parts of the submission.

The governing pattern is:

> **Evidence → decision → consequence**

Current verified examples include:

- a read-only source audit covering 13 logical tables, 7,671 CSV files, and 23,495,188 parsed rows with zero unreadable files or malformed rows;
- a deterministic curated serving layer over 150,000 customers, 400,000 products, and 4,425,008 transactions;
- a private 200-case template-controlled conformance/safety suite frozen before provider/prompt optimization, plus a disjoint 100-case development pool;
- a separate frozen 32-case synthetic ES/PT realistic-language v1 surface for provider-selection/language-stress diagnostics only, with explicit non-organizer/non-native-review provenance; v1 is not admissible for baseline-vs-LLM uplift claims;
- a 26-feature point-in-time analytical surface with chronological splits and strict same-timestamp leakage prevention;
- a supervised fraud-risk model that **failed** its pre-registered usefulness gate and was therefore **not deployed**;
- a transparent descriptive behavioral-evidence fallback whose output is explicitly not a fraud probability or fraud determination.

Known product, language, evaluation, and safety boundaries are maintained in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

The concise public narrative is in [docs/DATA_EVIDENCE_SPINE.md](docs/DATA_EVIDENCE_SPINE.md). The detailed retrospective evidence → decision → consequence record is in [docs/ANALYTICAL_DECISION_LEDGER.md](docs/ANALYTICAL_DECISION_LEDGER.md). The realistic-language v1 evidence boundary is documented in [docs/REALISTIC_LANGUAGE_SLICE.md](docs/REALISTIC_LANGUAGE_SLICE.md), and the independent sealed-v2 requirements are in [docs/REALISTIC_LANGUAGE_V2_FREEZE_PROTOCOL.md](docs/REALISTIC_LANGUAGE_V2_FREEZE_PROTOCOL.md). No baseline-vs-LLM uplift claim is permitted until a compliant blind-authored v2 is reviewed and sealed.

## Safety architecture

The selected design intentionally separates:

1. **Authoritative banking data** — curated into `bank.duckdb` and opened read-only.
2. **Application-generated operational state** — persisted separately in `runtime.sqlite`.
3. **Deterministic policy and authorization** — implemented in Python outside model discretion.
4. **AI interpretation** — added only after deterministic identity, retrieval, routing, persistence, and evaluation controls pass tests.

The model will never receive arbitrary SQL access and will never control the authenticated customer identity. Retrospective `is_fraud` labels and organizer `fraud_score` values are also excluded from runtime transaction records and policy inputs; fraud-specific mandatory escalation is driven by the customer's reported non-recognition/unauthorized activity, not by a score. A conservative deterministic fail-safe floor additionally routes a clear first-person denial next to a money, card or account mention to human review under the distinct reason code `possible_unauthorized_activity` (see [docs/LIMITATIONS.md](docs/LIMITATIONS.md) §12A).

The writable SQLite store contains only operational metadata: server-established session identity references, bounded structured conversation state, rate-limit events, and structured escalation/support tickets. It contains no customer/product/transaction banking tables and rejects unexpected tables on initialization.

Escalation is a controlled Act -> Verify path: a support ticket is inserted, committed, re-read and compared with the intended handoff, marked verified, and read back again before success is returned. Persistence or verification failure is a hard failure and is never represented as a successful escalation.

Successful customer turns also emit compact server-generated operational Decision Evidence. This
records the controlling check/reason, permitted action, execution state, and observable
verification result; it is not model chain-of-thought. Banking dependency unavailability remains
separate from policy disposition: it fails closed with HTTP 503 and no banking fact release rather
than inventing a fifth route.

The full precedence rationale, Decision Evidence semantics, route-vs-execution distinction, and
pre-LLM freeze boundary are documented in
[docs/POLICY_PRECEDENCE_AND_DECISION_EVIDENCE.md](docs/POLICY_PRECEDENCE_AND_DECISION_EVIDENCE.md).

## Judge-facing demo and API

The public/default runtime uses fully synthetic demo data (`DATA_MODE=synthetic`). Start the service and open `/` or `/demo` for the signal-box UI. The API remains available through:

- `GET /api/demo/personas`
- `POST /api/demo/sessions`
- `POST /api/customer/turn` with the returned `X-Demo-Session` header
- `POST /api/customer/handoff` for an explicit demo support request
- `DELETE /api/demo/session` to revoke the current demo session

The client never supplies a `customer_id`, tenant, or role. Those are server-issued and persisted. Every demo response is marked `synthetic_data=true`.

For the exact API boundary, example requests, isolation guarantees, and curated-mode distinction, see [docs/R3D_API_WALKING_SKELETON.md](docs/R3D_API_WALKING_SKELETON.md). The bilingual normal/clarify/handoff/escalation proof matrix is in [docs/R3E_VERTICAL_SLICE_PROOF.md](docs/R3E_VERTICAL_SLICE_PROOF.md).

## Local setup

Python 3.14 is the development baseline.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --reload
```

The service exposes separate liveness and readiness endpoints:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/ready
```

`/health` is process liveness only. `/ready` revalidates the live banking artifact/schema,
runtime data-mode binding, SQLite writability, and WAL mode; deployment health checks use
`/ready` and receive HTTP 503 when a required dependency is not ready.

HTTP request bodies are capped at 64 KiB before FastAPI parses them, and validation-error
responses omit rejected input values rather than echoing customer payloads.

## Runtime schema lifecycle

The writable operational SQLite database is versioned and intentionally has **no in-place
migration path** at this prototype stage. An incompatible older runtime fails closed before
startup changes it. For the bounded synthetic demo, stop the service, preserve the old runtime
file only if it is useful for diagnostics, move/remove it, and restart to create the current
schema. Never edit the stored schema version manually or reuse one runtime database across
synthetic and curated modes. See
[docs/R3D_API_WALKING_SKELETON.md](docs/R3D_API_WALKING_SKELETON.md) for the exact policy.

## Docker

```powershell
docker compose up --build
```

The local Compose surface maps port 8000. The production image also accepts a host-assigned
`PORT` environment variable and points its container health check at that same port.

The default Docker surface is synthetic-only: it creates/uses the recognized synthetic demo
artifact and a synthetic-bound runtime SQLite store, and it does not mount the curated
organizer-derived artifact. Curated local runs use explicit `DATA_MODE=curated`, the locally
built curated `bank.duckdb`, and a separate curated runtime SQLite path outside the public
default Compose surface.

For the freeze/deployment contract and public-verification checklist, see
[docs/FINAL_DEMO_DEPLOYMENT.md](docs/FINAL_DEMO_DEPLOYMENT.md).

## Curated data build

The application does not query the complete organizer dataset directly. The deterministic R3B builder creates the minimized trusted `bank.duckdb` used by the service:

```powershell
python scripts/build_curated_bank.py `
  --data-root "$HOME\Documents\Factored-Hackathon-2026\data" `
  --output "data\curated\bank.duckdb" `
  --manifest "data\curated\build_manifest.json" `
  --overwrite
```

The builder is fail-closed on primary-key, foreign-key, and transaction/product/customer ownership violations and refuses to write any generated artifact into the raw organizer-data root. See `docs/CURATED_DATA.md` for the exact retained/excluded fields and reproducibility contract.

## Data policy

Raw organizer data is not committed to this public repository.

The raw dataset remains local and read-only. The reproducible build step creates only the minimized curated DuckDB artifact required by the application. Generated database files and runtime state are git-ignored.

The operational store deliberately avoids raw conversation transcripts and unnecessary profile data. Conversation state is limited to structured interpretation state such as prior supported intent, bounded query parameters, candidate transaction references, clarification status, and language preference.

## Submission status

This repository is the canonical public implementation/submission surface for the Proof of One
entry. Product behavior is in freeze preparation: feature/backend iteration is closed unless
deployment verification exposes a concrete blocker.

The official Factored submission requires a public repository, a working deployed solution,
a 4–6 slide presentation, and a video pitch of at most 3 minutes. Deployment verification,
deck/script finalization, final claims/design audit, video recording, and owner-approved
submission remain outstanding.

The public demo must continue to state its boundaries accurately: synthetic data, local/public
prototype runtime, no live LLM in the judge-facing runtime, not fraud detection, and no
production/pilot-readiness claim.
