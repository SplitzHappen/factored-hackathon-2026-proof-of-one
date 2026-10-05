# Final Demo Deployment and Verification Contract

**Status:** judge-facing deployment reconciliation candidate for the Factored AI & Data Hackathon 2026 submission.

This document defines the narrow deployment contract for the current hosted full-data prototype demo.
It is operational guidance for the hackathon submission, not a production-readiness or pilot-readiness claim.

The official Factored submission materials require a public GitHub repository and a working deployed
solution. The organizer's supplied Dataset Summary states that the challenge dataset is completely
synthetic and contains no real customer information. The hosted application therefore serves bounded,
customer-scoped application views over the organizer-provided synthetic challenge data; it does not
publish the raw source files, dataset-access credentials, or claim a general right to redistribute the
dataset outside the hackathon use case.

## 1. Frozen judge-facing runtime

The current judge-facing candidate is the hosted full-data signal-box surface:

- signal-box web UI at `/` and `/demo` when the curated full challenge artifact is mounted;
- organizer-provided synthetic challenge data in `DATA_MODE=curated`;
- OpenAI GPT-6 Luna behind the provider-neutral interpretation boundary;
- automatic Spanish/Portuguese turn-language interpretation;
- deterministic policy/router authority for `ANSWER`, `CLARIFY`, `ABSTAIN`, and `ESCALATE`;
- customer-scoped, read-only banking records;
- provided challenge transcripts plus bounded custom ES/PT requests;
- persisted/read-back-verified support and escalation tickets;
- first-class Decision Evidence / ACT -> VERIFY output.

The LLM does not control authenticated identity, transaction ownership, banking truth, route
disposition, arbitrary SQL/database authority, or operational-action success claims.

The runtime must not be described as fraud detection, a live-bank integration, a production banking
system, a pilot-ready system, or evidence of real-world customer performance.

## 2. Runtime configuration

The public judge-facing deployment uses the curated full challenge artifact and the qualified live
interpretation provider:

```text
DATA_MODE=curated
BANK_DB_PATH=<mounted full challenge DuckDB artifact>
RUNTIME_DB_PATH=<writable curated runtime SQLite path>
INTERPRETATION_PROVIDER=openai-gpt-6-luna
OPENAI_API_KEY=<deployment secret>
PORT=<host assigned port>
```

The generated challenge artifact is derived deterministically from the read-only organizer source.
Raw organizer files and source-access credentials are not committed to Git and are not served by the
application.

The local/default Docker Compose surface remains intentionally synthetic and deterministic. That local
default is a development/smoke-test convenience and must not be confused with the hosted judge-facing
Render configuration.

## 3. Data-publication boundary

The organizer materials establish two relevant facts:

1. the challenge expects a deployed working solution and a public repository; and
2. the supplied banking dataset is completely synthetic, created for the 2026 challenge, and contains
   no real customer information.

The current deployment relies on those facts to expose bounded application-level views needed to
demonstrate customer-scoped operation. It deliberately does **not**:

- expose the raw CSV corpus or generated DuckDB artifact for bulk download;
- expose AWS/dataset-access credentials;
- claim that the dataset has a general-purpose public redistribution license;
- expose retrospective fraud labels/reference scores through normal operational transaction records;
- expose arbitrary customer enumeration or arbitrary SQL access.

If the organizers issue a narrower data-publication instruction, that instruction supersedes this
bounded hackathon deployment assumption and the public surface must be reduced accordingly.

## 4. Container and dependency contract

The repository container:

- installs only runtime dependencies;
- starts the FastAPI application with Uvicorn;
- accepts the host-assigned `PORT`;
- checks dependency-aware readiness through `/ready`.

Local smoke remains:

```powershell
docker compose up --build
```

Expected local endpoints:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/demo
http://127.0.0.1:8000/health
http://127.0.0.1:8000/ready
```

The local Compose data/provider defaults are intentionally not the public Render deployment identity.

## 5. Public verification checklist

Verify the exact hosted URL from a clean browser session after every deployment that is eligible for
the final recording.

### Infrastructure

- `GET /health` returns HTTP 200 with `status=ok`.
- `GET /ready` returns HTTP 200 with:
  - `status=ready`;
  - `data_mode=curated`;
  - `synthetic_data=false` for the application mode flag;
  - `bank_ready=true`;
  - `runtime_ready=true`;
  - `llm_connected=true`.
- Root `/` renders the full challenge-data signal-box UI.
- `/demo` resolves to the same judge-facing full-data shell under curated mode.
- The UI visibly identifies the live interpreter while retaining deterministic route authority.
- The UI does not offer bulk raw-data download or arbitrary customer enumeration.

### Judge-visible product checks

1. Search for one specific challenge customer and start a fresh customer-scoped session.
2. Replay one provided challenge message and confirm the visible route, response, and Decision Evidence
   reconcile.
3. Send one custom Spanish request through the live interpreter.
4. Send one custom Portuguese request through the live interpreter.
5. Verify at least one safe `ANSWER` path over trusted customer-scoped records.
6. Verify one `CLARIFY`, `ABSTAIN`, or `ESCALATE` path where deterministic authority prevents
   an unsafe or unsupported completion.
7. Trigger explicit human review and confirm persisted/read-back-verified ticket evidence.
8. Revoke the session and confirm it no longer authenticates.

### Boundary/claims surface

The public package must remain consistent that this is:

- a hosted full-data **hackathon prototype demo**;
- operating over organizer-provided **synthetic challenge data**;
- using live LLM interpretation with deterministic policy authority;
- not fraud detection;
- not connected to a live bank core;
- not a production- or pilot-readiness claim.

### Browser and host checks

- Open the deployment in a second private/incognito browser and confirm state is not reused from the
  first visitor.
- Verify session creation and rate-limit behavior through the actual Render proxy path rather than
  assuming origin-IP semantics from local execution.
- At 100%, 125%, 150%, and 200% browser zoom, confirm the route, customer response, four macro stages,
  and evidence remain readable without overlap.
- If the host restarts, confirm `/ready` returns to healthy state before recording or submission.

## 6. Freeze rule

After the final public verification and independent human break-it pass, do not expand the product.

Permitted after freeze:

- reproducible defect fixes;
- deployment configuration required by the selected host;
- factual documentation/claim corrections;
- accessibility or layout corrections that do not change product semantics;
- deck/script/video packaging.

Not permitted without a new explicit owner-authorized engineering cycle:

- route-policy changes;
- interpreter/prompt/model/provider changes;
- new intents or workflows;
- new analytical or ML experiments;
- weakening identity, ownership, data, action, or verification controls;
- opening or modifying sealed held-out evaluation material outside its governed execution path.

## 7. Remaining submission sequence

1. Complete the independent human break-it pass against the exact hosted URL.
2. Fix only reproducible serious defects or factual claim inconsistencies.
3. Run the authorized final evaluation under the frozen identities and governance controls.
4. Lock exact product commit, deployment identity, provider/model/prompt identity, and claims.
5. Finalize the 4–6 slide deck and <=3 minute video against that frozen candidate.
6. Perform one final claim-to-evidence and visual-compression review.
7. Record the video against the frozen deployed product.
8. Submit only after explicit owner approval.
