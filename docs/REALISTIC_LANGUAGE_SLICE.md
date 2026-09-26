# Supplementary Realistic-Language Slice

Status: **frozen before live provider execution**  
Suite: `factored-realistic-language-v1`  
Cases SHA-256: `e04071c19ae5ab239ba1fac8725eb35d1e5c262b45f3cd29ec5af84711eef459`

## Why this exists

The original development and held-out suites share public generator template families.
They remain useful for deterministic policy conformance, safety regression, ownership
isolation, and unseen-record testing, but they are not strong evidence that the language
interpreter generalizes to substantially different phrasing.

This supplementary slice adds a second language surface before any provider results are
observed.

It does **not** replace or modify `factored-heldout-v1`.

## Composition

The freeze contains:

- 32 public synthetic cases;
- 16 Spanish;
- 16 Portuguese;
- 16 paired semantic scenarios;
- 8 explicit unauthorized/non-recognition positives, four per language;
- indirect requests;
- colloquial wording;
- abbreviations/typos;
- code-switching;
- ambiguous references;
- relative-date wording;
- transaction status/lookup/history;
- amount/currency phrasing;
- prohibited banking actions;
- decline-cause requests.

Synthetic transaction references use only `RLX-ES-...` / `RLX-PT-...` identifiers.

No organizer customer, product, transaction, or banking value appears in the slice.

## Provenance boundary

The public repository contained no organizer transcript corpus or legally cleared
conversational-text artifact from which to derive new wording.

Therefore this freeze deliberately makes **no organizer-grounded language claim**:

- `organizer_data_used=false`;
- Spanish wording is team-generated;
- Portuguese wording is team-generated;
- `portuguese_native_reviewed=false`.

The Portuguese cases must not be described as native-reviewed until a real independent
native-language review occurs and a new version is frozen before consequential results.

This limitation is intentional and preferable to inventing provenance.

## Separation from the legacy generator

The slice was frozen against an explicit inventory of the public template surfaces used
by the original generator.

Before IDs, countries, and numbers are compared, both surfaces are normalized by:

- Unicode/case normalization;
- accent removal;
- synthetic ID/value abstraction;
- punctuation removal.

The highest SequenceMatcher surface similarity between any v1 message and any legacy
template is:

`0.657143`

The freeze requires a maximum below `0.70`.

This is not a semantic-independence theorem. It is a reproducible guard against simply
copying or lightly editing the old literal template surfaces.

## Provider-bake-off role

The v3 provider benchmark loads the frozen slice by its canonical SHA.

For each candidate it reports:

- overall realistic-language accuracy;
- Spanish realistic-language accuracy;
- Portuguese realistic-language accuracy;
- ES/PT gap;
- realistic-language unauthorized-positive recall;
- provider/schema failures on this slice.

A provider is ineligible if realistic-language unauthorized recall is below 100%.

Among otherwise eligible candidates, the provider-selection narrative should prioritize
language performance on this slice before using template-controlled development accuracy,
reliability, latency, and cost as later discriminators.

No provider output has been observed before this freeze.

## What this slice may support

After execution, it may support bounded statements about performance on:

> a frozen, synthetic, phrasing-distinct ES/PT stress slice.

It may **not** support claims that:

- the system has been validated on naturally occurring customer conversations;
- the Spanish cases came from organizer transcripts;
- the Portuguese cases were native-reviewed;
- the slice represents production language frequencies;
- it proves broad real-world multilingual generalization.

## Frozen files

- `evaluation/frozen/factored-realistic-language-v1/cases.jsonl`
- `evaluation/frozen/factored-realistic-language-v1/manifest.json`
- loader/integrity checks: `evaluation/realistic_language.py`
- regression tests: `tests/test_realistic_language.py`

Once live provider results exist, v1 is immutable. Any material wording/target correction
requires a new suite version rather than editing v1 in place.
