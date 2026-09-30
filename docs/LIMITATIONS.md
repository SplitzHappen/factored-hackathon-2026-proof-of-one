# Known Limitations and Product Boundaries

**Status:** active public disclosure for the Factored AI & Data Hackathon 2026 candidate.

Proof of One is intentionally bounded. This document records limitations that materially affect how the system should be interpreted, demonstrated, evaluated, or extended. A limitation listed here is not silently treated as solved.

## 1. Product scope is narrow by design

The current product is a prototype for **account / payment inquiry resolution**, not a general-purpose banking assistant.

The public demo uses synthetic/demo identity and banking data. It does not connect to a live bank core, move money, reverse transactions, change account ownership, or perform other live financial mutations. The controlled action surface centers on support/escalation workflow state.

## 2. Language coverage is bounded

The interpretation and safety work is focused on Spanish and Brazilian Portuguese. The deterministic grammar is not a general natural-language parser. Unsupported constructions may be clarified, suppressed, abstained from, or escalated rather than guessed.

## 3. Copular fraud statements do not retain SELF evidence

`self_performed` and `self_authorized` indicate that the customer says they themselves performed or authorized a transaction. Incorrectly attaching this evidence can make a disputed transaction look customer-authorized and can contribute to a missed fraud escalation.

The final independent RF1H-B2R-T audit challenged the positive-licensing design on 44 adversarial Spanish / Brazilian-Portuguese complaint rows. **25 / 44 produced wrong-referent SELF** on the pre-scope-reduction candidate: 21 `self_performed` and 4 `self_authorized`.

The test was adversarial and code-informed, so **25 / 44 is not a population error rate**. It establishes that the unsafe mechanism is reproducible across every claimed positive-license category.

### Shipped safety contract

For **copular P6 fraud-characterization statements**, if SELF evidence would be attached, the system suppresses the **entire P6-copular fraud proposition**.

It does not merely delete the SELF atom. Keeping the fraud proposition without SELF could still preserve a wrong transaction referent.

Consequences:

- some genuine scam-victim statements lose this fraud-characterization proposition;
- recall is intentionally lower;
- other evidence, clarification, abstention, escalation, or human review must carry the case;
- the system does not guess which transaction the fraud characterization refers to.

P6-attributive SELF was not implicated by the final audit and is not disabled by this specific scope reduction.

## 4. Fraud-referent resolution remains heuristic

Copular P6 referent selection uses bounded deterministic transaction-language evidence rather than full coreference resolution.

When a customer names a legitimate transaction and then refers to the disputed item indirectly—for example with a headless/pronominal expression or an amount without a recognized transaction noun—the grammar can still select the earlier recognized transaction as the fraud proposition's activity referent.

Disabling copular SELF removes the dangerous customer-performed/customer-authorized attribution from this surface, but it does **not** make the underlying referent selection authoritative.

Therefore:

- a P6 activity span is an **interpretation candidate**, not verified transaction identity;
- downstream resolution logic must not treat a P6 activity span alone as conclusive transaction resolution;
- ambiguous/headless references should be clarified, abstained from, or escalated rather than converted into a definitive transaction attribution.

## 5. No unrestricted coreference or dependency parser

The grammar intentionally avoids a general dependency, coordination, or coreference parser during the hackathon. This constrains recall and the range of structures that can be safely interpreted.

## 6. Production LLM/provider selection is not yet frozen

The public runtime has a provider-neutral interpretation boundary and deterministic fallback/stub behavior. A production LLM provider/model is not yet frozen. Model output never has authority over authenticated identity, banking truth, transaction ownership, policy, or action authorization.

## 7. Public demo data is synthetic

The public/default runtime uses synthetic demo personas and synthetic/demo banking data. Public-demo results should not be interpreted as production performance on a real institution's customers, transaction distributions, operational systems, fraud typologies, or compliance environment.

## 8. The supervised fraud-risk model was not deployed

The supervised fraud-risk model failed its pre-registered usefulness gate and was not deployed. The retained behavioral-unusualness evidence is descriptive only; it is not a fraud probability, fraud determination, or authorization to block or reverse a transaction.

See [ML_NULL_RESULT.md](ML_NULL_RESULT.md) and [BEHAVIORAL_UNUSUALNESS.md](BEHAVIORAL_UNUSUALNESS.md).

## 9. Realistic-language evaluation is still bounded

The existing realistic-language v1 slice is synthetic and is used for language-stress/provider-selection diagnostics. It is not admissible for a baseline-vs-LLM uplift claim. A separate blind-authored / sealed realistic-language v2 process is required before making that claim.

See [REALISTIC_LANGUAGE_SLICE.md](REALISTIC_LANGUAGE_SLICE.md) and [REALISTIC_LANGUAGE_V2_FREEZE_PROTOCOL.md](REALISTIC_LANGUAGE_V2_FREEZE_PROTOCOL.md).

## 10. Independent adversarial sets prove existence, not prevalence

The RF1H audit surfaces are deliberately adversarial. They establish whether a safety failure exists and whether a proposed invariant generalizes beyond development-known wording. They are not representative samples of customer language and should not be reported as real-world incidence estimates.

## 11. Human escalation remains part of the safety architecture

Clarification, abstention, and verified support escalation are intended outcomes when evidence is insufficient or ambiguous. The system is designed around **Understand → Decide → Act → Verify → Escalate**, with evidence controlling what the system is allowed to believe and do.

## 12. Remaining validation before final submission

Judge-facing evidence still depends on later gates including final RF1H-B2 closure under the narrowed contract, B3 resolution/integration, RF1J fresh/generalization evaluation, live/provider evaluation where applicable, final deployment/judge-facing UX, and final limitations/evaluation reconciliation.

This file should be updated whenever a material limitation is removed, narrowed, newly discovered, or converted into an explicit product-scope decision.