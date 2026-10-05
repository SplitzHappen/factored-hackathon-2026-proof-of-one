# Final Demo Deployment and Verification Contract

**Status:** final full-data public demo contract for the Factored AI & Data Hackathon 2026 submission.

This document supersedes the earlier synthetic-only/no-live-LLM deployment-preparation contract. The final judge-facing deployment is a hackathon prototype over the organizer-provided synthetic challenge dataset, not a production banking system, not a pilot-ready system, and not a fraud-detection product.

The public deployment is intended to make the core Proof of One architecture visible: LLM interpretation, server-controlled customer scope, deterministic route authority, bounded operational action, and observable verification.

## 1. Judge-facing runtime

The deployed judge-facing runtime is the full-data product surface:

- signal-box web UI at `/` and `/demo`;
- full challenge-data mode through the derived read-only DuckDB artifact;
- live Spanish/Portuguese interpretation through the governed provider contract;
- deterministic policy/router with fixed `ANSWER`, `CLARIFY`, `ABSTAIN`, and `ESCALATE` outcomes;
- server-issued customer-scoped sessions;
- customer-owned record retrieval only through backend repositories;
- persisted/read-back-verified support and escalation tickets;
- visible Decision Evidence / ACT -> VERIFY signals;
- no model authority over authenticated identity, ownership, banking truth, route disposition, execution, or verification.

The runtime must not be described as fraud detection, production readiness, pilot readiness, live-bank integration, or evidence of real-world banking performance.

## 2. Required public runtime configuration

Use curated full-data mode for the public demo.

```text
DATA_MODE=curated
BANK_DB_PATH=/var/data/full-challenge.duckdb
RUNTIME_DB_PATH=/var/data/curated-runtime.sqlite
INTERPRETATION_PROVIDER=openai-gpt-6-luna
PORT=<host assigned port>
```

The Render persistent disk must contain the derived full challenge DuckDB artifact at the configured `BANK_DB_PATH`. Raw organizer files, storage credentials, local data folders, and provider credentials must not be committed to Git.

The operational runtime SQLite database is separate from the banking artifact and contains only bounded operational state: server-established session identity references, bounded structured conversation state, rate-limit events, and support/escalation tickets. It must not contain authoritative banking tables.

## 3. Data-boundary contract

The public demo uses the organizer-provided synthetic challenge dataset through a derived read-only artifact. The public repository does not commit raw organizer data or generated database artifacts.

The final deployment exposes row-level synthetic challenge records through the controlled product workflow because that visibility is central to the judge-facing demonstration of customer scope, ownership, routing, and verification. The claim boundary remains explicit:

- the dataset is challenge/synthetic data, not real customer banking data;
- the application is a hackathon prototype;
- the app is not connected to a live bank core;
- the app is not production- or pilot-ready;
- model output is not an authority layer;
- deterministic backend controls remain authoritative.

Retrospective fraud labels and organizer risk scores are not exposed as customer-facing fraud determinations. Customer-reported non-recognition/unauthorized activity drives safety escalation; the failed supervised fraud-risk model remains not deployed.

## 4. Container and host contract

The repository Dockerfile:

- installs only runtime dependencies;
- starts the FastAPI application with Uvicorn;
- accepts the host-assigned `PORT`;
- checks dependency-aware readiness through `/ready`.

The public Render service is the canonical submitted deployment unless explicitly replaced by a later owner-approved deployment identity:

```text
https://proof-of-one-factored-2026.onrender.com
```

Render service configuration must preserve:

- one public web service;
- full-data `DATA_MODE=curated`;
- mounted persistent disk for the derived DuckDB artifact and operational runtime store;
- health check path `/ready`;
- no committed secrets.

## 5. Public verification checklist

After deployment, verify the exact public URL from a clean browser session.

### Infrastructure

- `GET /health` returns HTTP 200 with `status=ok`.
- `GET /ready` returns HTTP 200 with:
  - `status=ready`;
  - `data_mode=curated`;
  - `synthetic_data=false`;
  - `bank_ready=true`;
  - `runtime_ready=true`;
  - `llm_connected=true`.
- Root `/` renders the full-data signal-box UI.
- `/demo` renders the same full-data UI.
- The UI displays the full-data/live-LLM badge.
- The UI preserves the four judge-facing stages: `INTERPRET`, `SCOPE`, `ROUTE`, and `VERIFY`.

### Judge-visible scenarios

Start fresh scoped sessions and verify:

1. `ANSWER` — a Spanish account/transaction query returns a scoped, record-backed answer.
2. `CLARIFY` — ambiguous supported references ask for clarification rather than guessing.
3. `ESCALATE` — a customer-reported unauthorized/non-recognized payment routes to human review.
4. `ABSTAIN` — prohibited or unsupported banking actions remain outside the bounded workflow.
5. Portuguese path — a Portuguese customer message is interpreted as Portuguese without granting model authority.
6. HANDOFF — the explicit support endpoint creates a ticket and shows persisted/read-back-verified evidence.

### Boundary/claims surface

The public UI and submission materials must retain these boundaries:

- full-data challenge demo, not live-bank deployment;
- synthetic challenge data, not real customer data;
- live LLM interpretation, not LLM authority;
- deterministic policy route authority;
- no fraud-detection claim;
- no production/pilot-readiness claim;
- human review for safety escalations.

### Isolation / restart checks

- Open the deployment in a second private/incognito browser and confirm a fresh server-issued session rather than reuse of the first visitor's state.
- Revoke one session and confirm it no longer authenticates.
- Confirm customer-scoped sessions do not allow cross-customer record disclosure.
- Confirm dependency failure, if encountered, fails closed with HTTP 503 and no banking fact release rather than inventing a normal route.

## 6. Freeze rule

After public verification passes, do not change application behavior before recording the final video unless verification exposes a concrete blocker.

Permitted after freeze:

- deployment configuration required by the selected host;
- factual README/deployment documentation corrections;
- claim/copy corrections that do not alter routing or evidence semantics;
- deck/script/video packaging.

Not permitted without a new owner-authorized engineering cycle:

- route-policy changes;
- interpreter behavior changes;
- new intents/workflows;
- data-artifact changes;
- held-out evaluation;
- architecture expansion.

## 7. Final submission package

The Factored submission package is submitted by email to `hackathon.admin@factored.ai` and consists of:

1. the public GitHub repository;
2. the deployed solution link: `https://proof-of-one-factored-2026.onrender.com`;
3. the final 4–6 slide presentation;
4. the final video pitch no longer than 3 minutes.

The repository and deployment remain the technical implementation surfaces. The final slide deck and video are packaging artifacts submitted separately by email with the repository and deployment links.

Final submission-facing boundaries remain unchanged:

- no held-out PASS claim;
- no fraud-detection claim;
- no production-readiness claim;
- no pilot-readiness claim;
- no live-bank-core integration claim;
- no real-customer-data claim.

After this package is assembled, only factual documentation corrections and owner-approved claim-safety corrections should be made. Application behavior, route policy, interpreter behavior, data artifacts, evaluation logic, and deployment configuration remain frozen unless a concrete blocker is identified and explicitly authorized.
