## Change summary

Describe the bounded change and its relationship to the frozen delivery contract.

## Verified Delivery metadata

Verified-Delivery-Contract: <repository-relative path to frozen JSON contract>
Candidate-Head-SHA: <exact current 40-character PR head SHA>
Evidence-Status: pending
Independent-Audit: pending
Owner-Acceptance: pending
Verifier-Change-Disposition: none
Release-Intent: none

## Evidence

List deterministic checks, CI runs, exact-candidate artifacts, and the canonical Continuity evidence/audit locator. Do not treat an AI statement that the change is complete as evidence.

## Scope / negative assurance

- [ ] Changed paths are within the frozen contract's allowed write surfaces.
- [ ] Forbidden surfaces were not changed.
- [ ] Any test/scorer/threshold/CI/security/audit/release-criterion change is declared above and governed by a contract revision or audited repair.
- [ ] Protected held-out material was not accessed or modified outside its authorized gate.
- [ ] The Candidate-Head-SHA line was refreshed after the final commit.
- [ ] Feature completion is not being represented as submission/pilot/production readiness unless the separate release gate is satisfied.
