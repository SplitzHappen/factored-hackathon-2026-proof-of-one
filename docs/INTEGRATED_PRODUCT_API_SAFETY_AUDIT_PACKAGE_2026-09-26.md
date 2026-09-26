# Integrated Product / API / Safety Audit Package — 2026-09-26

Audit gate: `ACT-R3E-INTEGRATED-CLAUDE-GATE`

This document is an audit reading map. It is not implementation evidence by itself.

## Frozen substantive candidate

The R3E implementation candidate to audit is public commit:

`780e6892a53233e7cd73034ec272ed9f216e9a19`

That commit is the squash merge of public PR #31:

`Add R3E bilingual vertical-slice proof`

Its CI evidence recorded at merge time:

- 203 tests passed;
- production Docker build passed;
- one unchanged non-blocking `TestStatus` PytestCollectionWarning.

Do not substitute a later implementation commit.

If this audit-package document is merged after the substantive candidate, the later package-only merge may be read for instructions, but implementation conclusions must be anchored to the substantive candidate above unless the audit request explicitly supersedes it.

## What changed in R3D/R3E

The current customer-resolution path is:

`public synthetic persona
-> server-issued tenant/role/customer session
-> provider-neutral deterministic interpretation stub
-> deterministic post-check
-> ownership-scoped read-only BankRepository
-> deterministic policy
-> deterministic ES/PT response
-> optional verified human handoff`

R3E adds proof of:

- verified normal answer in ES and PT;
- genuine same-customer ambiguity in ES and PT;
- second-turn explicit candidate selection;
- prohibited banking action -> safe abstention + handoff availability;
- explicit unauthorized/non-recognition -> verified escalation;
- cross-customer reference -> no transaction/candidate disclosure;
- bounded owned candidate IDs for ambiguity;
- persisted clarification state transition.

## Required implementation reading surface

Read the complete files, not excerpts:

### HTTP/runtime/bootstrap
- `app/main.py`
- `app/bootstrap.py`
- `app/settings.py`
- `app/schemas.py`
- `app/runtime.py`

### Banking / authorization / resolution
- `app/bank.py`
- `app/policy.py`
- `app/customer_service.py`
- `app/interpretation.py`
- `app/deterministic_provider.py`
- `app/demo_data.py`
- `app/evidence_service.py`

### Deployment / hygiene
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`
- `.dockerignore`
- `.github/workflows/ci.yml`

### Product/safety docs
- `README.md`
- `docs/R3D_API_WALKING_SKELETON.md`
- `docs/R3E_VERTICAL_SLICE_PROOF.md`
- `docs/LLM_INTERPRETATION_BOUNDARY.md`
- `docs/CURATED_DATA.md`
- `docs/BEHAVIORAL_UNUSUALNESS.md` only to confirm it is not currently exposed by this product surface
- `docs/PROVIDER_BAKEOFF.md` only where provider-neutral/runtime assumptions intersect the current API

### Required tests
- `tests/test_r3d_api.py`
- `tests/test_r3e_vertical_slice.py`
- `tests/test_runtime_store.py`
- `tests/test_bank_repository.py`
- `tests/test_interpretation.py`
- `tests/test_policy.py`
- `tests/test_contracts.py`
- `tests/test_evidence_service.py`
- `tests/test_health.py`
- `tests/test_repository_hygiene.py`

Also inspect any additional tests/code you judge relevant.

## Known current boundaries — do not assume completed

The following are intentionally **not yet complete** and must be evaluated as gaps, not silently credited:

- session TTL/expiry;
- per-session/IP abuse controls;
- final request-rate limits;
- final LLM cost cap enforcement;
- live LLM provider integration/selection;
- frontend UI;
- analyst Workbench/Intelligence;
- repaired held-out observation/scoring boundary;
- held-out execution;
- repaired Behavioral Unusualness parity/composite;
- public hosting/deployed smoke evidence.

The audit should decide which of these must be repaired **before further product work**, which may safely remain later roadmap work, and which are submission blockers.

## Critical audit questions

### 1. Identity, tenant, role, session
Adversarially test whether a caller can:
- choose or alter `customer_id`;
- choose or alter tenant;
- choose or alter role;
- rebind an existing session;
- use an analyst session on customer endpoints;
- use a foreign tenant session;
- exploit malformed/unknown UUIDs;
- exploit persisted state to cross customer/session boundaries;
- obtain useful access from a guessed/stolen session ID;
- exploit the lack of expiry.

Assess whether `X-Demo-Session` is an acceptable hackathon demo boundary and what must change before public deployment.

### 2. Synthetic / curated separation
Verify:
- public demo issuance is synthetic-mode only;
- organizer-backed curated mode cannot be mislabeled `synthetic_data=true`;
- public endpoints cannot accidentally expose organizer rows;
- Docker defaults cannot mount/expose organizer data unexpectedly;
- synthetic bank construction cannot overwrite a curated artifact under a plausible misconfiguration;
- build/bootstrap behavior is safe enough under repeated startup/concurrency.

### 3. Read-only banking / ownership
Actively search for:
- arbitrary SQL;
- client/model-controlled customer identity;
- cross-customer transaction access;
- product/customer mismatch paths;
- candidate-ID disclosure across customers;
- query breadth controlled by untrusted text/model;
- retrospective `is_fraud` / `fraud_score` reaching runtime outputs or policy.

### 4. Interpretation authority / prompt injection
Verify:
- provider/interpreter sees no banking records or identity;
- explicit transaction IDs must be present in customer text;
- amount/status/type/date filters are provenance checked;
- model/provider output cannot decide ownership, policy, escalation, or banking truth;
- fallback is fail-safe;
- prior intent/state cannot become an authority bypass;
- deterministic demo interpreter does not accidentally create a broader unsafe contract than live provider adapters.

### 5. Multi-turn clarification
Challenge the R3E ambiguity flow:
- are candidate IDs guaranteed to be owned?
- can more than ten hidden candidates create misleading clarification?
- can stale candidate state cause unsafe answers?
- can a second turn select an unrelated owned transaction and still be presented as ambiguity resolution?
- does the system need candidate-membership enforcement, or is explicit ownership re-verification sufficient for the current product contract?
- do missing-parameter, missing-record, and true-ambiguity paths remain distinguishable?
- can clarification state be poisoned across turns?

### 6. Routing / escalation / handoff
Verify precedence and semantics for:
- unauthorized assertion;
- missing/unowned record;
- prohibited mutation;
- decline-cause request;
- unknown intent;
- trusted-data conflict;
- excluded relationships;
- ambiguity;
- required parameters missing.

Specifically verify that benign missing/unowned records are not converted into fraud escalation and that only explicit customer unauthorized assertions are the fraud-specific mandatory-escalation trigger.

### 7. Escalation persistence
Challenge whether a successful escalation claim is justified:
- insert -> readback -> verify flag -> readback;
- session binding;
- transaction binding;
- forged ticket possibilities;
- ticket/context reuse;
- behavior when persistence verification fails.

### 8. Deterministic ES/PT response grounding
Verify that customer-facing facts come only from verified records and deterministic templates.

Check:
- localized status rendering;
- amounts/currency;
- transaction IDs;
- ambiguity options;
- prohibited-action copy;
- decline-cause abstention;
- unauthorized escalation wording.

Flag any wording that implies stronger certainty, fraud determination, action execution, or human handling than the implementation guarantees.

### 9. Tests
Do not treat green CI as sufficient.

Look for:
- tests that merely restate implementation;
- unrealistic fixtures;
- missing adversarial tests;
- missing concurrency/startup tests;
- missing session-theft/expiry tests;
- same-bug tests;
- gaps in HTTP error handling;
- tests that do not prove claimed cross-customer safety;
- missing failure-path tests around SQLite/DuckDB/bootstrap.

### 10. Public deployment readiness
Assess:
- Docker behavior;
- writable runtime path;
- synthetic artifact startup;
- repeat startup;
- concurrent workers;
- secrets/config;
- CORS/default docs exposure if relevant;
- health semantics;
- absence of rate/abuse/session-expiry controls;
- whether the current API is safe enough for a judge-accessible demo.

## Known prior audit decisions that should be re-challenged where relevant

Do not presume these remain true merely because they were previously accepted:

- deterministic policy remains authoritative;
- customer assertion is the fraud-specific mandatory-escalation trigger;
- model cannot control identity/ownership;
- cross-customer transaction references fail closed;
- runtime excludes fraud target/reference fields;
- ticket persistence verification is meaningful;
- synthetic/public and organizer-backed/private modes are cleanly separated;
- R3C post-check hardening survives R3D/R3E integration.

## Forbidden audit inputs

Do not inspect:
- raw organizer row-level data;
- private development prompt contents;
- private development answer keys;
- private held-out prompt contents;
- private held-out answer keys;
- provider credentials.

Aggregate counts, hashes, recorded metrics, public synthetic cases, code, tests, manifests, and public docs are allowed.

## Audit standard

Prefer direct code/test evidence over README or audit-package prose.

If documentation and implementation differ, treat implementation as authoritative evidence and report the documentation mismatch.

Run tests/static checks/adversarial probes where feasible. You may create temporary local test code for investigation, but do not modify the implementation candidate.

## Expected outcome

The auditor should decide whether the integrated R3D/R3E product/API/safety surface is:

- safe to continue building on;
- repairable before further product work;
- or fundamentally unsafe/mis-scoped.

The detailed report format and write authorization are defined in the matching Continuity audit request.
