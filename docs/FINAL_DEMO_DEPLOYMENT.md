# Final Demo Deployment and Verification Contract

**Status:** deployment-preparation freeze candidate for the Factored AI & Data Hackathon 2026 submission.

This document defines the narrow deployment contract for the frozen judge-facing synthetic demo.
It is operational guidance, not a production-readiness claim.

The official Factored submission page requires a working deployed solution in addition to the
public repository, 4–6 slide presentation, and video pitch. The deployed surface described here
is therefore a hackathon demonstration surface only.

## 1. Frozen judge-facing runtime

The deployment candidate is the same product demonstrated locally:

- signal-box web UI at `/` and `/demo`;
- synthetic personas only in the public/default runtime;
- deterministic interpretation provider;
- deterministic policy/router;
- ownership-scoped synthetic banking records;
- persisted/read-back-verified support and escalation tickets;
- Spanish and Brazilian Portuguese demonstration paths;
- no live LLM connected to the judge-facing runtime.

The runtime must not be described as fraud detection, a production banking system, a pilot-ready
system, or evidence of real-world performance.

## 2. Required runtime configuration

Use synthetic mode for the public demo.

```text
DATA_MODE=synthetic
BANK_DB_PATH=/app/runtime/synthetic-demo.duckdb
RUNTIME_DB_PATH=/app/runtime/synthetic-runtime.sqlite
PORT=<host assigned port, or 8000 locally>
```

No live-provider credential is required for the frozen judge-facing runtime.

The runtime directory must be writable. A persistent volume is preferred for a public deployment
so sessions/tickets survive container restarts during judging, but all public banking records
remain synthetic.

Do not mount organizer raw data or the curated organizer-derived artifact into the public demo.

## 3. Container contract

The repository Dockerfile:

- installs only runtime dependencies;
- starts the FastAPI application with Uvicorn;
- accepts the host-assigned `PORT`;
- checks dependency-aware readiness through `/ready`.

Local smoke:

```powershell
docker compose up --build
```

Expected local surfaces:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/demo
http://127.0.0.1:8000/health
http://127.0.0.1:8000/ready
```

## 4. Reverse-proxy / public-host constraint

The application rate-limits successful demo-session creation by the ASGI peer address.

A public host normally places the container behind a reverse proxy. Before judge-accessible
go-live, the selected platform's trusted proxy chain must therefore be known and Uvicorn proxy
header handling must be configured so `request.client.host` represents the originating client
rather than one shared proxy address.

Do not solve this by blindly trusting arbitrary forwarded headers on a directly exposed service.
The exact `FORWARDED_ALLOW_IPS` / proxy setting is a deployment-environment decision and remains
blocked until the hosting platform is selected.

This is the only known deployment-specific runtime configuration blocker in this freeze-prep
record. It is not a reason to reopen product feature work.

## 5. Public verification checklist

After deployment, verify the exact public URL from a clean browser session.

### Infrastructure

- `GET /health` returns HTTP 200 with `status=ok`.
- `GET /ready` returns HTTP 200 with:
  - `status=ready`;
  - `data_mode=synthetic`;
  - `synthetic_data=true`;
  - `bank_ready=true`;
  - `runtime_ready=true`;
  - `llm_connected=false`.
- Root `/` renders the signal-box UI.
- `/demo` renders the same UI.
- No organizer-derived data is present in the public container/runtime volume.

### Judge-visible scenarios

Start a fresh synthetic session and verify:

1. ANSWER — known owned transaction returns a record-backed answer.
2. CLARIFY — the 54,000 COP Lucía query returns the two owned synthetic candidates.
3. ESCALATE — the unauthorized-report preset routes to human review and returns a ticket.
4. ABSTAIN — the out-of-scope transfer request stays outside the bounded workflow.
5. PT — Rafael's Portuguese transaction-status path returns an owned PT synthetic record.
6. HANDOFF — the separate endpoint creates a support ticket and shows persisted/read-back-verified evidence.

### Boundary/claims surface

The public UI must visibly retain:

- `LOCAL PROTOTYPE · SYNTHETIC`;
- no live LLM;
- not fraud detection;
- not production/pilot-ready;
- deterministic-check explanation;
- explicit HANDOFF as a separate support endpoint.

### Isolation / restart checks

- Open the deployment in a second private/incognito browser and confirm a fresh server-issued
  tenant/session rather than reuse of the first visitor's state.
- Revoke one session and confirm it no longer authenticates.
- If the hosting plan can restart the container, perform one controlled restart and confirm
  `/ready` returns to green. If a persistent runtime volume is configured, confirm expected
  operational state persistence according to that platform's storage contract.

## 6. Freeze rule

After public verification passes, do not change application behavior before recording the final
video unless verification exposes a concrete blocker.

Permitted after freeze:

- deployment configuration required by the selected host;
- factual README/deployment documentation corrections;
- claim/copy corrections that do not alter routing or evidence semantics;
- deck/script/video packaging.

Not permitted without a new owner-authorized engineering cycle:

- route-policy changes;
- interpreter behavior changes;
- new intents/workflows;
- FTP-2 activation;
- live-provider wiring;
- held-out evaluation;
- architecture expansion.

## 7. Remaining submission sequence

1. Select/configure the public host and trusted-proxy contract.
2. Deploy the frozen synthetic image.
3. Run this public-verification checklist.
4. Lock the public URL/product behavior.
5. Build the final 4–6 slide deck.
6. Finalize the <=3 minute narration/script.
7. Run the final Claude claims/design audit over the deployed product + deck + script.
8. Apply only justified final copy/packaging corrections.
9. Record the video once against the frozen deployed product.
10. Submit only after explicit owner approval.
