# Known Limitations and Product Boundaries

**Status:** active public disclosure for the Factored AI & Data Hackathon 2026 candidate.

Proof of One is intentionally bounded. This document records limitations that materially affect how the system should be interpreted, demonstrated, evaluated, or extended. A limitation listed here is not silently treated as solved.

## 1. Product scope is narrow by design

The current product is a prototype for **account / payment inquiry resolution**, not a general-purpose banking assistant.

The public demo uses synthetic/demo identity and banking data. It does not connect to a live bank core, move money, reverse transactions, change account ownership, or perform other live financial mutations. The controlled action surface centers on support/escalation workflow state.

## 2. Language coverage is bounded

The interpretation and safety work is focused on Spanish and Brazilian Portuguese. The deterministic grammar is not a general natural-language parser. Unsupported constructions may be clarified, suppressed, abstained from, or escalated rather than guessed.

**English is formally out of scope.** Unauthorized-activity recognition is built for Spanish and Portuguese only, so an explicit English report of unauthorized activity is usually not recognized. RF1Q therefore adds a safe fallback (`app/language_scope.py`): a turn written predominantly in English never receives account data. The interpretation post-check maps it to an unsupported request, which abstains with a human-review offer instead of answering a transaction, balance, or product question. A recognized unauthorized-activity report still escalates first; this includes the two frozen English code-switch atoms.

The check counts closed sets of function words. Words that English shares with Spanish or Portuguese count for neither language. Identifiers such as `DEMO-ES-1001` are ignored, so the route never depends on the shape of a reference. A Spanish or Portuguese message with an English fragment stays in scope.

Consequences:

- English customers receive no automated answers;
- English unauthorized-activity reports are not escalated automatically. They receive the abstention and the human-review offer, never an ordinary status answer;
- very short English messages with fewer than two English function words fall through to the ordinary Spanish/Portuguese path.

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
- RF1Q adds four families for reports the resolver is silent on:
  - a product opened in the customer's name ("alguien abrió una tarjeta a mi nombre", "golpistas contrataram um empréstimo com meus dados"). The opener must be unnamed, or the message must say it happened without the customer's authorization. "Me abrieron una cuenta a mi nombre en la sucursal" describes a legitimate opening and is not a report;
  - denial of having opened or requested an existing product ("una tarjeta que yo nunca pedí", "nunca la abrí", "..., nunca abri"). It is blocked when the item does not exist yet, when the message says "not yet", and when the opening is attributed to a named relative ("la pidió mi esposa");
  - a product shown in the customer's records that they say is not theirs ("la cuenta que aparece en mi perfil no es mía"). A bare "esse cartão não é meu" about a physical card is still not a report, and a corrective re-attribution ("..., es la de mi hija") blocks it;
  - a relative's denial relayed through their own words ("mi esposo dice que no reconoce los cargos"). It follows the same third-party contract as above, and the relative list now includes partners and grandchildren;
- RF1Q blocks every family when the message says the item was already resolved, refunded, or no longer suspicious ("ya me lo devolvieron", "já foi estornado"). A later recall ("ya me acordé", "depois lembrei") blocks only a non-recognition told in the past or framed as initial ("no reconocí ... al principio"). It never blocks "no reconozco este cargo, pero ya me acordé de bloquear la tarjeta";
- Portuguese "caso apareça / caso haja ..." now counts as a protasis for the whole layer;
- RF1Q narrows structural authority for exactly two shapes the resolver asserts but which are not active reports:
  - an advice question with an indefinite-future protasis before the denial ("¿Qué debo hacer si algún día veo un cargo que no reconozco?");
  - a non-recognition resolved later in the same message.

  Such an assertion is demoted (`structural_assertion_demotion`), and the layer decides with all of its blockers. Every other structural assertion stays authoritative, including present-tense help questions ("¿Qué hago si tengo un cargo que no reconozco?");
- RF1S adds three families for active own-account compromise reports the resolver is silent on:
  - an unnamed party performed activity tied to the customer's account ("un tercero retiró dinero de mi cuenta", "alguém voltou a usar meu cartão"). The tie is the customer's account, card, or data as source, instrument, or location, or an observation of the customer's own records or a bank notice ("abrí la app y me di cuenta de que alguien ..."). A bare "alguien hizo una compra" stays outside, as the structural grammar decides. Incoming money ("alguien me transfirió ..."), delegation ("por mí", "como le pedí"), questions, conditionals, hedges, and resolutions block it;
  - impersonation or identity theft by an unnamed party ("se hizo pasar por mí", "me suplantaron", "usaron mis documentos", "roubaram minha identidade"), only when the conversation is about banking and not about a social-media profile;
  - a change to the customer's credentials or contact data (password, PIN, e-mail, phone) that is disowned: an unnamed actor, a first-person denial ("yo no la cambié"), "no fui yo", or an explicit lack of authorization. A change the customer requested ("como solicité") or simply reports without disowning is not licensed;
- RF1S widens existing families structurally rather than by wording:
  - a relative-clause set-up or origination denial may reach its head across a modifier chain of up to eight words when the customer is describing something observed ("veo un cobro mensual de una app de música que nunca agregué"), and an origination denial over any item located in the customer's financial records (statement, credit bureau, history) names an existing product;
  - product heads now include deposits, insurance, and credit lines (CDT/CDB, póliza/apólice, seguro, libranza, microcrédito, sobregiro, inversión), and accepting an item ("nunca acepté ese seguro") counts as origination. A declined offer with a reason ("..., porque era cara") or with no charged or recorded item is not a report;
  - a cash advance (`avance`) is account activity, and an amount taken from an account ("de su cuenta salieron 900 mil") is a money-flow anchor;
  - a relay may come from someone acting for the account holder (a caregiver, legal representative, or "en nombre de / de parte de" a named person), and the relayed elliptical agency denial "..., y no fue él / ela não foi" is a third-party cue. The same third-party contract applies, and a message that names the relative who did it ("la hizo mi esposa; no fue él") is not a report;
- RF1S over-escalation controls:
  - **own declined payment.** When the resolver asserts an adjectival "no autorizado / não autorizado" that is the system's label on the customer's own attempt (a possessed transaction or an attempt verb in the same sentence, no newly introduced item, and a decline outcome or a status frame such as "salió como"), the assertion is demoted. A decline next to a genuine report ("..., había compras no autorizadas que yo no hice", "no fue autorizado por mí") stays a report;
  - **resolved or recognized.** A resolution earlier in the same sentence ("ya se aclaró lo del débito que no reconocía") resolves the item unless a fresh event follows it ("pero", "hoy", "otra vez", "otro cargo"). A non-recognition told in the past or framed as initial is resolved by a later attribution to a known relative ("resultó ser de mi esposa"), unless the message says the use was unauthorized. Both shapes demote a structural assertion and block every layer family. A resolution in an earlier sentence does not cover a later report;
- RF1U adds five families for active own-account reports the resolver is silent on:
  - an activity item characterized as fraudulent ("es una compra fraudulenta", "me cargaron dos pagos fraudulentos") or as unknown or not recognized ("tengo un cargo desconocido", "apareceu uma transação desconhecida", "un pago no reconocido", "un cargo de origen desconocido"). The adjective must characterize the item itself, with at most two bare modifiers in between, so "una transferencia de un remitente desconocido" is not a report. The item must also be presented as the customer's own: a copula (including "creo que es ..."), its presence or observation ("tengo / hay / me salió / estou com"), a charge to the customer ("me hicieron un ..."), a report verb ("quiero reportar un ..."), a demonstrative, or the customer's own account as its location. Questions, conditionals, hedges ("puede ser un ..."), information and advice requests ("cómo identificar ...", "consejos para ..."), negated presence ("no tengo ningún ..."), a topic mention ("en general", "un protocolo para ..."), a quoted claim ("un SMS diciendo que ..."), a recognition or resolution, a relative's attribution, and incoming money ("me llegó una transferencia desconocida") block it. Gender/number agreement is not checked, so a misspelled agreement does not defeat a report;
  - third-party authorship with an explicit negated self: an unnamed party did it, "not me" ("fue hecha por otra persona, no por mí", "lo hizo un tercero, no yo", "foi outra pessoa, não eu"). A named actor is outside the family, and a permission grant or a delegation ("pero yo se lo pedí") blocks it;
  - the customer's personal, card, or account data used for financial activity: an impersonal or unnamed use with a financial purpose clause ("usaron mis datos para hacer una transferencia", "usaram os dados do meu cartão para fazer compras"), or impersonal activity done with the data ("hicieron una compra usando mis datos"). A non-financial purpose ("para criar um perfil"), a named or kin subject ("mis hijos usaron ..."), and a delegation are not reports;
  - a scam the customer fell for, licensed only by a later transaction in the customer's name, with their data, or from their account by an impersonal or unnamed party, in the same or the next sentence ("caí en una estafa e hicieron un pago a mi nombre"). A scam with no such transaction, a near miss ("casi caí ..."), and a negated transaction ("no hicieron ninguna compra") are not reports;
- RF1U widens the non-recognition families: the Brazilian account-movement noun "movimento(s)" is an activity anchor and relative head ("desconheço este movimento na minha conta");
- it never consults the retired whole-message regex inventory.

Consequences:

- a licensed denial routes to verified escalation (`unauthorized_activity_reported`), attaching only an owned transaction and never disclosing a foreign one;
- recall is still bounded: inferential denials ("no puede ser mía") and induced-scam payments the customer made themselves ("caí num golpe e eu mesmo fiz o pix") are not covered; third-party reports are covered only when a named relative ("mi papá", "minha mãe") or someone acting for the account holder relays a denial of the activity; money-movement and set-up denials without a back-reference to an existing item ("no envié el pago", "no programé el pago") are deliberately not licensed because they usually describe a failure to act;
- where the structural resolver resolves a hypothetical or other non-assertive reading, the layer defers even if a denial is present;
- the structural resolver itself still escalates some hedged or "not yet" statements conservatively, and a delegated use the customer asked for ("alguien ... pagó ... con mi tarjeta, como le pedí") when the resolver asserts it. Embedded advice-question hypotheticals, same-message resolutions, own declined payments, and relative attributions are demoted only in the RF1Q and RF1S shapes above;
- product and identity-misuse recall is bounded:
  - a stand-alone identity-theft statement ("me robaron la identidad") is covered by RF1S only in a banking context; a bare impersonation with no account, product, credential, or bank mention is not;
  - an opening by a named relative is covered only with an explicit lack of authorization;
  - "suspicious" or "strange" charges relayed for a relative are not a denial, so they are not covered;
- a resolution marker about a different item in the same message ("..., el anterior ya me lo devolvieron") can block a fresh report. RF1Q accepts this conservatively and records it as a residual. RF1S keeps the same posture for a resolution earlier in the same sentence, but only when no fresh-event marker follows it;
- RF1S windows are bounded on purpose: an observed relative head reaches at most eight words, an unnamed actor needs an account tie or an observation of the customer's records, and impersonation needs a banking context. Wording outside these bounds falls back to the earlier behavior.
- RF1U windows are bounded on purpose too: a characterization reaches its item across at most two bare modifiers, a presence verb reaches its item across at most six words that are not a topic noun or a non-locative preposition, the scam licence must follow in the same or the next sentence, and questions about the RF1U families stay unlicensed (a why-question presupposing an unknown charge, "¿por qué tengo un cargo desconocido?", is not covered).

## 13. Remaining validation before final submission

Judge-facing evidence still depends on later gates including final RF1H-B2 closure under the narrowed contract, B3 resolution/integration, RF1J fresh/generalization evaluation, live/provider evaluation where applicable, final deployment/judge-facing UX, and final limitations/evaluation reconciliation.

This file should be updated whenever a material limitation is removed, narrowed, newly discovered, or converted into an explicit product-scope decision.