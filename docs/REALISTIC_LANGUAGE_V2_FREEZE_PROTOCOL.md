# Realistic-Language v2 — Sealed Independent Freeze Protocol

Status: **protocol only — no v2 cases are present in the public repository**

Purpose: define the minimum evidence conditions required before Proof of One may make any
baseline-vs-LLM uplift claim on a realistic-language surface.

## Why v2 is required

`factored-realistic-language-v1` remains valid for provider-selection and language-stress
diagnostics, but it is not independent uplift evidence. The deterministic demo interpreter was
authored after the v1 freeze and later incorporated several v1-distinctive phrasings or
near-equivalents. V1 therefore cannot establish incremental LLM value over that baseline.

V2 must be a new sealed surface whose authoring process is isolated from the deterministic
interpreter/baseline implementation.

## Required separation

The v2 case author must not inspect, quote, search, or receive:

- `app/deterministic_provider.py`;
- the deterministic baseline implementation or baseline-specific prompt/rule inventory;
- `factored-realistic-language-v1/cases.jsonl`;
- provider outputs or provider-bake-off results;
- held-out case wording;
- any list of phrases added to product code after the v1 freeze.

The blind author may receive only:

- the supported and unsupported intent taxonomy;
- the high-level safety/authorization contract;
- the structured interpretation schema at the field/enum level;
- synthetic scenario facts needed to create answerable or deliberately unanswerable cases;
- this freeze protocol.

If the blind-author separation cannot be demonstrated, the resulting suite is development
material only and must not be called v2 uplift evidence.

## Composition floor

The sealed suite must contain at least:

- 48 total cases;
- 24 Spanish and 24 Portuguese;
- paired or scenario-balanced coverage across the two languages where feasible;
- at least 16 explicit unauthorized/non-recognition positives, with at least 8 per language;
- supported informational requests;
- ambiguity/clarification;
- prohibited banking actions;
- decline-cause/unsupported requests;
- cross-customer or ownership traps using synthetic identifiers only;
- relative-date and amount/currency phrasing;
- indirect, colloquial, typo/abbreviation, and code-switching surfaces.

No organizer customer identifier, product identifier, transaction identifier, amount, or other
row-level banking value may appear in the suite.

## Language provenance

Spanish should be derived from organizer-transcript linguistic phenomena when an authorized
private process can do so without copying identifiable or row-level content. If that provenance
cannot be established, the manifest must say so explicitly.

Portuguese must not be described as native-reviewed unless a real independent native Portuguese
reviewer reviews the final wording before freeze. The reviewer must not use the deterministic
stub or v1 wording as a rewrite template.

## Private freeze location

The cases remain private/sealed until consequential evaluation. They must not be committed to
the public repository before evaluation.

Recommended private layout:

`evaluation/private/frozen/factored-realistic-language-v2/`

The freeze record must include at minimum:

- suite version;
- case count and ES/PT counts;
- unauthorized-positive counts by language;
- exact SHA-256 of the case file;
- authoring timestamp;
- blind-author attestation;
- Spanish provenance statement;
- Portuguese native-review status;
- reviewer attestation when applicable;
- confirmation that no provider results were observed before freeze.

Only the manifest/hash and aggregate provenance claims may be surfaced publicly before unsealing.

## Ordering and contamination controls

The required order is:

1. blind authoring;
2. independent language/provenance review;
3. freeze the v2 bytes and record their SHA-256;
4. freeze the deterministic baseline **without showing v2 cases to the baseline author**;
5. run one evaluator-controlled baseline diagnostic on sealed v2;
6. record aggregate baseline metrics without exposing case text to the developer;
7. if v2 is not discriminating, retire it intact and author a new blind version rather than
   editing v2 after seeing baseline failures;
8. only after the final suite and system are frozen may baseline-vs-LLM evaluation be used for
   an uplift claim.

The v2 hash must therefore predate the final baseline freeze used for the uplift comparison.

## Non-ceiling diagnostic

The baseline diagnostic is not an optimization loop. It is a one-way validity check.

For v2 to remain eligible as an uplift surface:

- baseline safety behavior must remain acceptable;
- the baseline must not be at or effectively at ceiling on language-core correctness;
- no baseline wording or logic may be changed in response to v2 results.

A baseline result at or above 90% language-core correctness is treated as insufficiently
discriminating for the planned +10 percentage-point incremental-value claim. In that event,
v2 is retired intact and a new blind suite version is required.

## Claim boundary

Until a compliant v2 is frozen and evaluated, Proof of One must not claim that:

- the LLM beats the deterministic baseline on independent realistic language;
- v1 demonstrates incremental LLM value over the baseline;
- Portuguese realistic-language quality is native-reviewed;
- realistic-language results represent natural production frequencies.

V1 provider-selection metrics may still be reported, with its selection/development label and
provenance limitations intact.
