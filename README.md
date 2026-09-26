# Proof of One — Factored AI & Data Hackathon 2026

Proof of One is a bounded account/payment customer-support prototype for the Factored AI & Data Hackathon 2026.

## Current implementation stage

R3E bilingual vertical-slice proof.

The application currently contains:
- a judge-visible FastAPI walking skeleton with public synthetic demo personas and server-issued tenant/role-bound sessions;
- strict Pydantic boundary contracts;
- Docker packaging;
- a deterministic curated-data builder for minimized trusted banking data;
- a bounded read-only DuckDB query layer with customer-isolation checks and an operational transaction projection that excludes retrospective fraud labels/reference scores;
- a separate writable SQLite operational store for tenant/role-bound authenticated demo sessions, bounded conversation state, and structured support/escalation tickets;
- a deterministic policy/router with fixed `ANSWER`, `CLARIFY`, `ABSTAIN`, and `ESCALATE` outcomes and hard safety precedence;
- persistence verification that re-reads an escalation ticket before the runtime may report success;
- tests proving that model-facing transaction queries cannot supply a `customer_id`, conversation state cannot rebind identity, and the runtime store cannot contain authoritative banking tables;
- a provider-neutral Spanish/Portuguese interpretation boundary with strict typed extraction, bounded retries/fallback, deterministic transaction-reference verification, and no model authority over identity, ownership, banking truth, policy, or behavioral evidence;
- a deterministic stub interpreter behind that same provider protocol so end-to-end product integration does not wait for live provider selection;
- deterministic Spanish/Portuguese customer responses over verified facts, with cross-customer non-disclosure and verified human handoff for unauthorized-activity reports;
- a frozen descriptive Behavioral Unusualness fallback after the supervised fraud-risk model failed its pre-registered usefulness gate.

No production LLM provider/model is frozen yet.

## Data & evaluation

Proof of One is deliberately positioning **data engineering, statistical discipline, and evidence-based product decisions** as first-class parts of the submission.

The governing pattern is:

> **Evidence → decision → consequence**

Current verified examples include:

- a read-only source audit covering 13 logical tables, 7,671 CSV files, and 23,495,188 parsed rows with zero unreadable files or malformed rows;
- a deterministic curated serving layer over 150,000 customers, 400,000 products, and 4,425,008 transactions;
- a private 200-case template-controlled conformance/safety suite frozen before provider/prompt optimization, plus a disjoint 100-case development pool;
- a separate frozen 32-case synthetic ES/PT phrasing-distinct language slice for provider generalization evidence, with explicit non-organizer/non-native-review provenance;
- a 26-feature point-in-time analytical surface with chronological splits and strict same-timestamp leakage prevention;
- a supervised fraud-risk model that **failed** its pre-registered usefulness gate and was therefore **not deployed**;
- a transparent descriptive behavioral-evidence fallback whose output is explicitly not a fraud probability or fraud determination.

The concise public narrative is in [docs/DATA_EVIDENCE_SPINE.md](docs/DATA_EVIDENCE_SPINE.md). The detailed retrospective evidence → decision → consequence record is in [docs/ANALYTICAL_DECISION_LEDGER.md](docs/ANALYTICAL_DECISION_LEDGER.md). The supplementary language-evaluation boundary is documented in [docs/REALISTIC_LANGUAGE_SLICE.md](docs/REALISTIC_LANGUAGE_SLICE.md).

## Safety architecture

The selected design intentionally separates:

1. **Authoritative banking data** — curated into `bank.duckdb` and opened read-only.
2. **Application-generated operational state** — persisted separately in `runtime.sqlite`.
3. **Deterministic policy and authorization** — implemented in Python outside model discretion.
4. **AI interpretation** — added only after deterministic identity, retrieval, routing, persistence, and evaluation controls pass tests.

The model will never receive arbitrary SQL access and will never control the authenticated customer identity. Retrospective `is_fraud` labels and organizer `fraud_score` values are also excluded from runtime transaction records and policy inputs; fraud-specific mandatory escalation is driven by the customer's reported non-recognition/unauthorized activity, not by a score.

The writable SQLite store contains only operational metadata: server-established session identity references, bounded multi-turn state, and structured escalation handoffs. It contains no customer/product/transaction banking tables and rejects unexpected tables on initialization.

Escalation is a controlled Act -> Verify path: a support ticket is inserted, committed, re-read and compared with the intended handoff, marked verified, and read back again before success is returned. Persistence or verification failure is a hard failure and is never represented as a successful escalation.

## R3D walking-skeleton API

The public/default runtime uses fully synthetic demo data (`DATA_MODE=synthetic`). Start the service and open `/docs`, or use:

- `GET /api/demo/personas`
- `POST /api/demo/sessions`
- `POST /api/customer/turn` with the returned `X-Demo-Session` header

The client never supplies a `customer_id`, tenant, or role. Those are server-issued and persisted. Every demo response is marked `synthetic_data=true`.

For the exact API boundary, example requests, isolation guarantees, and curated-mode distinction, see [docs/R3D_API_WALKING_SKELETON.md](docs/R3D_API_WALKING_SKELETON.md). The bilingual normal/clarify/handoff/escalation proof matrix is in [docs/R3E_VERTICAL_SLICE_PROOF.md](docs/R3E_VERTICAL_SLICE_PROOF.md).

## Local setup

Python 3.14 is the development baseline.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --reload
```

The health endpoint is available at:

```text
http://127.0.0.1:8000/health
```

## Docker

```powershell
docker compose up --build
```

The service is exposed on port 8000. Docker Compose defaults to the public synthetic artifact and keeps generated demo banking data plus `runtime.sqlite` on the writable runtime volume. Organizer-backed local runs may set `DATA_MODE=curated` and point `BANK_DB_PATH` at the read-only curated artifact.

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

This repository is the canonical public implementation/submission surface for the Proof of One entry. Architecture, evaluation evidence, deployment documentation, limitations, and final submission artifacts will accumulate here as implementation proceeds.
