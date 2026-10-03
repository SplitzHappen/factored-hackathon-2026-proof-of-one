# Verified Delivery — Factored public repository

This directory documents the public-repository enforcement half of Factored's high-assurance delivery protocol.

The canonical governance/evidence record remains in the private Continuity project. This public repository adds a fail-closed PR preflight so implementation work cannot quietly drift away from its frozen contract.

## What the PR gate enforces

For every governed PR:

- a frozen JSON delivery contract exists;
- its baseline equals the exact PR base SHA;
- the PR body pins the exact current head SHA;
- changed files remain inside allowed write surfaces and outside forbidden surfaces;
- acceptance requirements have stable IDs and required evidence;
- builder and independent auditor are separately declared;
- protected verifier changes are explicit and require a governed disposition;
- ready-for-review PRs require evidence complete, independent audit complete (or an explicit not-required rationale), and owner acceptance.

Draft PRs may carry pending audit/evidence/acceptance while work is genuinely in progress.

## What this gate does not prove

Passing this workflow does **not** by itself prove:

- the independent audit actually occurred;
- the auditor was substantively independent;
- held-out data were uncontaminated;
- security/isolation properties are correct;
- owner identity/acceptance is authentic;
- the candidate is submission/pilot/production ready.

Those claims require the canonical Continuity evidence and, where applicable, deterministic tests and human/domain review.

## Protected-exam rule

After contract freeze, changes to tests, scorers, thresholds, required CI, security policy, held-out material, audit semantics, or release criteria are treated as changes to the exam itself.

They are not prohibited, because verifiers can contain defects. They **are** required to be explicit, justified, revision-bound, and reverified.

## Repeat-failure rule

The same material failure class receives at most three ordinary implementation attempts:

1. diagnose/repair;
2. inspect specification, verifier, environment, dependencies/tools and architecture;
3. stop and open a root-cause gate.

A fourth blind retry is not a valid continuation.

## Starting a new governed PR

1. Copy `contract.example.json` into `.github/verified-delivery/contracts/<task>.json`.
2. Replace all placeholders and set the baseline to the exact intended PR base SHA.
3. Freeze acceptance criteria before implementation.
4. Open the PR as a draft and complete the PR metadata.
5. After every new commit, refresh `Candidate-Head-SHA` in the PR body.
6. Do not mark ready until canonical evidence, audit disposition and owner acceptance satisfy the contract.
