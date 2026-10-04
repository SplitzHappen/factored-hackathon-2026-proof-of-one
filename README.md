# Proof of One — Factored AI & Data Hackathon 2026

Proof of One is a bounded account/payment customer-support prototype for the Factored AI & Data Hackathon 2026.

## Current implementation stage

Finalization-stage candidate after the signal-box UI, full interpreter-to-policy replay evidence,
first-class Decision Evidence / ACT -> VERIFY, trusted-bank dependency fail-closed handling,
live provider qualification/wiring, and full challenge-data deployment.

The public Render runtime uses the organizer-provided challenge dataset in `DATA_MODE=curated`
and connects OpenAI GPT-6 Luna for bounded Spanish/Portuguese interpretation. The LLM does not
control authenticated identity, transaction ownership, banking truth, route disposition, or
operational action; deterministic policy remains authoritative.

The exact technical runtime candidate is pinned at product commit
`6dff2a889f11dba85465f43b20908c4331e1ce4c`. Final submission-candidate freeze still requires
final public-package consistency, a fresh direct public smoke after the latest UI repairs, final
claims/design assurance, video/package freeze, and explicit owner approval. The frozen held-out
suite remains sealed; no held-out PASS or production/pilot-readiness claim is made here.

The application currently contains:
- a judge-facing signal-box web UI over the public full-challenge-data API, with customer-scoped challenge records, provided transcript messages, fresh server-issued sessions, revocation, and bounded operational retention;
- strict Pydantic boundary contracts;
- Docker packaging;
- a deterministic full challenge-data artifact builder that preserves all 13 supplied table families while materializing the minimized canonical customer/product/transaction tables used by bounded banking operations;
- a bounded read-only DuckDB query layer with customer-isolation checks and an operational transaction projection that excludes retrospective fraud labels/reference scores;
- a separate writable SQLite operational store for tenant/role-bound sessions, bounded conversation state, and structured support/escalation tickets;
- a deterministic policy/router with fixed `ANSWER`, `CLARIFY`, `ABSTAIN`, and `ESCALATE` outcomes and intentional authority-ordered precedence;
- a strict server-generated Decision Evidence envelope that exposes interpretation status, controlling check/reason, action, execution status, and observable verification codes without exposing model chain-of-thought;
- persistence verification that re-reads an escalation ticket before the runtime may report success;
- a sanitized trusted-bank dependency failure contract that returns HTTP 503, claims no normal route in the failure payload, and releases no banking fact when the DuckDB/banking layer is unavailable;
- tests proving that model-facing transaction queries cannot supply a `customer_id`, conversation state cannot rebind identity, and the runtime store cannot contain authoritative banking tables;
- a provider-neutral Spanish/Portuguese interpretation boundary currently wired to **OpenAI GPT-6 Luna**, with strict typed extraction, true ES/PT turn-language detection, deterministic transaction-reference verification, and no model authority over identity, ownership, banking truth, policy, or behavioral evidence;
- a deterministic fallback interpreter behind the same provider protocol for fail-closed/local behavior;
- deterministic Spanish/Portuguese customer responses over verified facts, with cross-customer non-disclosure, verified escalation/support-ticket persistence, and an explicit customer-requested support-handoff endpoint;
- a frozen descriptive Behavioral Unusualness fallback after the supervised fraud-risk model failed its pre-registered usefulness gate;
- an RF5 replay guardrail that exercises the real interpreter -> verified interpretation -> authoritative `route_policy()` path over public/non-held-out replay cases.

## Data & evaluation

Proof of One is deliberately positioning **data engineering, statistical discipline, and evidence-based product decisions** as first-class parts of the submission.

The governing pattern is:

> **Evidence → decision → consequence**

Current verified examples include:

- a read-only source audit covering 13 logical tables, 7,671 CSV files, and 23,495,188 parsed rows with zero unreadable files or malformed rows;
- a deterministic full challenge-data artifact preserving all 13 supplied table families, with bounded canonical banking tables covering 150,000 customers, 400,000 products, and 4,425,008 transactions;
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
4. **AI interpretation** — OpenAI GPT-6 Luna performs bounded ES/PT interpretation behind the provider-neutral contract; deterministic identity, retrieval, routing, persistence, and verification controls remain authoritative.

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

The public Render deployment at
`https://proof-of-one-factored-2026.onrender.com` runs in `DATA_MODE=curated` against the
full organizer-provided challenge artifact and presents the full-data signal-box UI at `/`.
The challenge dataset is competition/synthetic data, not a live bank core.

Judge-facing full-data endpoints include:

- `GET /api/challenge/coverage` for non-sensitive table coverage/count evidence;
- `GET /api/challenge/customers` for bounded customer-ID search;
- `GET /api/challenge/customers/{customer_id}/messages` for provided customer-message retrieval;
- `POST /api/challenge/sessions` to establish the selected customer-scoped session;
- `POST /api/customer/turn` with the returned session header;
- `POST /api/customer/handoff` for an explicit support request;
- session revocation through the product's bounded session endpoint.

The current live interpreter is **OpenAI GPT-6 Luna** under interpretation contract
`r3c-v3-auto-language`. It detects Spanish/Portuguese turn language, but deterministic policy
sets the route and verified banking records remain the source of truth.

The local/default Docker Compose surface remains synthetic by design; it is separate from the
public full-challenge Render configuration. For the API boundary and isolation guarantees, see
[docs/R3D_API_WALKING_SKELETON.md](docs/R3D_API_WALKING_SKELETON.md). The bilingual
normal/clarify/handoff/escalation proof matrix is in
[docs/R3E_VERTICAL_SLICE_PROOF.md](docs/R3E_VERTICAL_SLICE_PROOF.md).

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
built curated `bank.duckdb`, and a separate curated runtime SQLite path outside the default
local Compose surface.

For the freeze/deployment contract and public-verification checklist, see
[docs/FINAL_DEMO_DEPLOYMENT.md](docs/FINAL_DEMO_DEPLOYMENT.md).

## Curated data build

The deployed full challenge artifact is built deterministically from the read-only organizer data
with `scripts/build_full_challenge_data.py`. It preserves all 13 supplied table families in the
DuckDB artifact while also materializing the minimized canonical `customers`, `products`, and
`transactions` tables used by the bounded banking runtime.

```powershell
python scripts/build_full_challenge_data.py `
  --data-root "$HOME\Documents\Factored-Hackathon-2026\data" `
  --output "data\curated\full-challenge.duckdb" `
  --manifest "data\curated\full_challenge_manifest.json" `
  --overwrite
```

The current deployed full challenge DuckDB SHA-256 is
`939ccd040ae1bc8015edc6a5c9f9b3ad90f5af7205f4fb90c35826a24b4e9372`; the corresponding
manifest SHA-256 is
`88e1bc9247fdb23e55126179823eb38dc67e8b42504465f289273d755fb81d35`.

The builder remains fail-closed on required source/table completeness and the canonical banking
integrity checks, and generated artifacts are not committed to Git. The original minimized
`scripts/build_curated_bank.py` path remains useful for bounded local/analytical workflows, but
it is not the artifact currently mounted by the public full-data deployment.

## Data policy

Raw organizer data is not committed to this public repository.

The raw organizer files remain local and read-only. Reproducible build steps create derived curated DuckDB artifacts; the public deployment currently mounts the full challenge artifact described above. Generated database files and runtime state are git-ignored.

The operational store deliberately avoids raw conversation transcripts and unnecessary profile data. Conversation state is limited to structured interpretation state such as prior supported intent, bounded query parameters, candidate transaction references, clarification status, and language preference.

## Submission status

This repository is the canonical public implementation/submission surface for the Proof of One
entry. The technical runtime identity has been pinned and the public deployment is live on the
full organizer-provided challenge artifact with OpenAI GPT-6 Luna interpretation and deterministic
route authority.

The official submission still requires the final 4–6 slide presentation, <=3 minute video,
final claim/design assurance, exact final artifact/deployment identities, and explicit owner
approval before submission. The frozen held-out suite remains separately owner-gated and is not
represented as completed.

Judge-facing boundaries must remain explicit: this is a hackathon prototype over organizer-provided
synthetic challenge data, **not fraud detection**, not connected to a live bank core, and not a
production/pilot-readiness claim.
