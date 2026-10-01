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

## 12. Denial-safety layer covers structural silence only

Fresh independent probes found natural, explicit first-person denials ("se hizo un retiro que yo no solicité", "não é verdade que eu tenha feito…") that the structural grammar resolves to no proposition at all, so the turn could be answered as an ordinary transaction request. `app/denial_safety.py` is a bounded safety net for that silence:

- the structural resolver stays authoritative; the layer runs only when it produced no assertive proposition, and any resolved non-assertive mode other than a question vetoes it;
- a cue must be a first-person denial of performing, authorizing, soliciting, recognizing, or owning account activity, anchored to an activity noun, charge/debit verb, or use of the customer's card/account;
- interrogative scope, conditional protasis, prior belief/retraction, reported speech, double negation, uncertainty hedges, "not yet"/causal non-performance, and descriptor clarification ("no reconozco el nombre del comercio") block the cue;
- RF1M adds four bounded families: clause-initial "no fui yo"/"não fui eu" measured by its own clause, first-person money-movement denials that point back at an existing movement ("yo no la envié", "eu não mexi nesse dinheiro"), elliptical ownership denial over listed items ("ninguno es mío", "nenhuma é minha"), and emphatic/elliptical agency denial ("yo seguro que no", "eu é que não fui"), plus a closed set of misspellings of "reconozco";
- RF1M also blocks a cue when the message grants permission to the actor ("con mi permiso", "eu autorizei") or explains a movement that did not happen (forgetting, app failure);
- a short follow-up may borrow the activity anchor of the immediately preceding sentence, or of the sentence before it only when that intervening sentence asks who did it ("no sé quién lo hizo"); a reported balance drop counts as an anchor unless the same sentence explains it;
- RF1O adds six report families, each bound to an existing referent rather than to topical wording:
  - set-up / initiation / enrollment denial over an item that already exists: a relative clause on a payee, debit, or transfer ("... un destinatario que yo nunca agregué", "... um Pix que eu nunca iniciei"), a demonstrative object ("nunca me suscribí a eso"), or an object clitic with an explicit "yo" ("yo no lo programé"); "no programé el pago" and "nunca me suscribí a nada" stay unlicensed;
  - observed activity located where the customer has never been ("vi retiros en una ciudad donde nunca he estado"); planned travel, self-performed activity, and activity attributed to a named relative are blocked, and card possession alone is not a report;
  - household-wide denial of an existing item ("un cobro que nadie en mi familia reconoce", "nem eu nem meu marido fizemos"), never of a new indefinite activity ("nadie hizo compras este mes");
  - intrusion into the customer's own account or app by an unnamed party ("creo que se metieron a mi cuenta", "acessaram minha conta"); a named or negated subject, an uncertainty hedge, a permission grant, or a non-bank account ("mi cuenta de Netflix") blocks it;
  - account-provenance denial of an alert or item ("pero no es de mi cuenta"); a corrective re-attribution ("..., es de la tarjeta de mi esposo") blocks it;
  - a named relative's denial relayed by the customer ("mi mamá no reconoce un cargo", "ele não sacou"); this is the product-contract decision for third-party reports: mandatory escalation with a ticket bound to the reporting session only, with no third-party account lookup or disclosure;
- RF1O families read conditional scope over the whole sentence, and Portuguese "se um dia / se por acaso / se aparecer / se houver ..." now counts as a protasis for the whole layer, so hypothetical advice questions built on any family are not licensed;
- it never consults the retired whole-message regex inventory.

Consequences:

- a licensed denial routes to verified escalation (`unauthorized_activity_reported`), attaching only an owned transaction and never disclosing a foreign one;
- recall is still bounded: inferential denials ("no puede ser mía") and induced-scam payments are not covered; third-party reports are covered only when a named relative ("mi papá", "minha mãe") denies the activity; money-movement and set-up denials without a back-reference to an existing item ("no envié el pago", "no programé el pago") are deliberately not licensed because they usually describe a failure to act;
- where the structural resolver resolves a hypothetical or other non-assertive reading, the layer defers even if a denial is present;
- the structural resolver itself escalates some hedged, "not yet", or retracted statements conservatively, and asserts some embedded advice-question hypotheticals ("¿Qué debo hacer si algún día veo un cargo que no reconozco?"); the layer does not change that.

## 13. Remaining validation before final submission

Judge-facing evidence still depends on later gates including final RF1H-B2 closure under the narrowed contract, B3 resolution/integration, RF1J fresh/generalization evaluation, live/provider evaluation where applicable, final deployment/judge-facing UX, and final limitations/evaluation reconciliation.

This file should be updated whenever a material limitation is removed, narrowed, newly discovered, or converted into an explicit product-scope decision.