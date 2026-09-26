# Proof of One — Data Evidence Spine

Proof of One is intentionally designed so that the data work is visible as part of the product argument rather than hidden behind the application.

The governing pattern is:

> **Evidence → decision → consequence**

For every consequential analytical choice, the repository should make it possible to answer:

1. What did the data actually show?
2. What decision followed from that evidence?
3. What changed in the product, evaluation, or claim boundary because of it?

This document is the public narrative layer. The underlying contracts, manifests, tests, model artifacts, and decision records remain the source of truth.

---

## 1. Data landscape and trusted serving layer

The original read-only source audit covered:

- **13 logical tables**
- **7,671 CSV files**
- approximately **4.98 GiB**
- **23,495,188 parsed rows**
- **0 unreadable files**
- **0 malformed rows**
- exactly **1 header schema variant per table**

The observed row total was **24.41% higher** than the sum of the organizer's approximate per-table counts, largely because `digital_events` was substantially larger than documented. Proof of One therefore uses measured, reproducible denominators rather than documentation approximations.

The judge-facing application does not query the complete organizer dataset directly.

The current verified curated banking layer contains:

- **150,000 customers**
- **400,000 products**
- **4,425,008 transactions**

The curated database is produced deterministically from the organizer source, opened read-only at runtime, and physically separated from writable operational state.

The real curated build is bound to:

- curated database SHA-256: `84d3df259923007511ac6b017b7a04c9e31f2b12e2219ec0f8a2d9661b2baad1`
- curated manifest SHA-256: `bc9b583d75c1140e737dcefdc088ef7fbb98ba916fc2281aae1177c1ac2448b1`

### Evidence → decision → consequence

**Evidence:** the application needs only a bounded subset of the supplied relational data for account/payment resolution.

**Decision:** build a minimized, reproducible serving artifact instead of giving the application unrestricted access to the raw data estate.

**Consequence:** runtime banking reads are limited to approved customer/product/transaction fields and ownership-verified relationships. Raw organizer data remain outside the public repository and are not writable by the application.

---

## 2. Data quality, relational integrity, and lineage

The curated builder fails closed on structural problems rather than silently accepting them.

Verified gates include:

- duplicate primary IDs;
- required-field failures;
- foreign-key orphans;
- transaction/product/customer ownership mismatches;
- incompatible curated-schema versions;
- attempts to write generated artifacts into the raw organizer-data root.

The runtime repository independently rechecks ownership when serving a transaction. Writable session/ticket state lives in a separate SQLite database that is forbidden from containing authoritative banking tables.

### Evidence → decision → consequence

**Evidence:** analytical and conversational correctness depend on relational integrity and clear separation between source-of-truth data and application-generated state.

**Decision:** treat data contracts and lineage as executable constraints, not documentation-only assumptions.

**Consequence:** cross-customer access, schema drift, unexpected tables, and broken ownership chains fail closed.

The retrospective audit evidence has now been recovered and consolidated. High-consequence findings include: clean official primary keys across all 23.5M rows; 100% missing complaint origin-interaction linkage; effectively unusable customer/agent branch relationships; 0% customer-consistent complaint affected-product linkage; near-zero customer-consistent digital-event product context; strong transaction/product/customer and transcript/survey identity chains; explicit country/currency normalization requirements; and a material product-recency metadata inconsistency.

For the detailed retrospective record—including exact missingness, duplicate/identifier, joinability, workflow-demand, outcome, temporal, modeling, and governance findings—see [ANALYTICAL_DECISION_LEDGER.md](ANALYTICAL_DECISION_LEDGER.md).

---

## 3. Evaluation separation before model work

Conversational evaluation was frozen before LLM provider selection or prompt optimization.

The private evaluation design contains:

- **200 held-out cases**: 150 Spanish / 50 Portuguese;
- **63 multi-turn cases**;
- **85 high-risk cases** repeated for safety evaluation;
- a separate **100-case development pool**: 75 Spanish / 25 Portuguese;
- zero organizer-customer overlap between development and held-out pools.

Canonical held-out combined SHA-256:

`4d6b920db63fbedf4af8ec08631ea5848abf6feb9013ef83f60c8fbe636ad3f7`

### Evidence → decision → consequence

**Evidence:** provider choice, prompt changes, and debugging can overfit a conversational benchmark just as model tuning can overfit a statistical test set.

**Decision:** create and hash the held-out suite before LLM optimization.

**Consequence:** provider selection and prompt work are restricted to the development pool. The held-out prompts and answer keys remain private and untouched until final evaluation.

---

## 4. Leakage-safe analytical engineering

The full transaction population was used to construct a point-in-time feature artifact.

The frozen reduced feature surface contains **26 predictors**:

- 10 approved intrinsic transaction/product features;
- 16 historical/history-depth features;
- lifetime, 24-hour, and 30-day behavioral history;
- no organizer `fraud_score` as a predictor;
- no customer country or accent as direct predictors;
- no future information;
- no same-timestamp peer leakage.

Historical features use only records with:

`historical_timestamp < current_timestamp`

The verified chronological split contains:

- train: **3,097,506 rows**
- model selection: **331,876 rows**
- calibration/usefulness gate: **331,876 rows**
- untouched test: **663,750 rows**

Identical timestamp groups are never split across partitions.

### Evidence → decision → consequence

**Evidence:** random splits and ordinary rolling calculations can leak future or same-time information into a transaction-level fraud experiment.

**Decision:** use global chronological partitions and strict point-in-time history.

**Consequence:** the model experiment is evaluated under a closer approximation to prospective use, and the same timestamp semantics are reused by runtime behavioral evidence.

---

## 5. The negative model result is a product decision, not a hidden failure

The supervised fraud-risk experiment was required to pass a pre-registered usefulness gate before it could appear as an operational signal.

On the calibration/usefulness segment:

- fraud prevalence: **0.0009039521**
- selected GBDT PR-AUC: **0.0008868433**
- GBDT PR-AUC 95% lower bound: **0.0007636379**
- best non-GBDT comparator PR-AUC: **0.0009245945**
- top-0.5% review-budget recall: **0.0**
- top-0.5% precision lift: **0.0**

All three frozen usefulness checks failed.

The untouched **663,750-row test segment was not opened** for this supervised experiment because the gate did not authorize it.

### Evidence → decision → consequence

**Evidence:** the candidate classifier did not demonstrate useful rare-event signal on the frozen validation gate.

**Decision:** reject supervised fraud-risk output rather than change thresholds, cherry-pick another metric, or inspect the test set.

**Consequence:** Proof of One does **not** expose a fraud probability, fraud-risk score, ML fraud adjudication, ML-driven analyst priority, or ML-driven mandatory escalation.

This is a central project result:

> **The data were allowed to veto the feature.**

---

## 6. Transparent behavioral evidence instead of unsupported prediction

After the supervised model was rejected, the workbench fallback was frozen as descriptive behavioral evidence.

The optional **Behavioral Unusualness** composite uses exactly six target-free components:

1. amount surprise relative to prior same-currency behavior;
2. channel novelty;
3. merchant-category novelty;
4. transaction-country novelty;
5. 24-hour transaction velocity;
6. 30-day transaction velocity.

The composite is the unweighted mean of available component scores, scaled to 0–100.

It is suppressed unless:

- at least 5 prior lifetime transactions exist; and
- at least 4 of the 6 components are available.

Required interpretation:

> **Descriptive behavioral evidence only; not a fraud probability or fraud determination.**

### Evidence → decision → consequence

**Evidence:** the supervised target did not support a useful predictive model, but the transaction history still supports transparent within-customer descriptive comparisons.

**Decision:** preserve useful analytical context without rebranding it as prediction.

**Consequence:** analysts may inspect behavioral deviation while routing, escalation, and banking actions remain deterministic and independent of the unusualness score.

---

## 7. AI interpretation remains subordinate to verified data

The language-model boundary is provider-neutral and currently unfrozen.

The model may interpret Spanish/Portuguese customer language into a strict schema, but it does not receive authority over:

- authenticated customer identity;
- transaction ownership;
- banking truth;
- policy outcomes;
- behavioral evidence;
- escalation persistence.

A model-returned transaction ID must appear in the customer's actual text and must then pass ownership verification. Model-extracted transaction searches use server-controlled result breadth so ambiguity cannot be hidden by returning only one match.

Provider/model selection will use the separate development pool. The held-out suite remains sealed.

### Evidence → decision → consequence

**Evidence:** language models are useful interpreters but are not reliable sources of identity, authorization, or banking facts.

**Decision:** constrain the model to language interpretation and post-check every consequential fact deterministically.

**Consequence:** model capability can be changed or improved without changing the trusted banking/safety boundary.

---

## 8. What the final analytical story should show

The final demo and submission should not become a large EDA gallery. The analytical narrative will use a small number of evidence-rich exhibits.

### Exhibit A — Data landscape

Show the supplied data estate, the relationships actually used, and the minimized serving layer.

Question answered:

> What is in the data, and what did we choose to trust?

### Exhibit B — Quality and lineage

Show a small number of consequential quality/joinability findings, integrity gates, and the reproducible raw → curated → analytical → serving path.

Question answered:

> What could these data validly support?

### Exhibit C — Point-in-time analytical design

Show chronological partitions, the 26-feature leakage-safe surface, and same-timestamp exclusion.

Question answered:

> How did we prevent analytical convenience from becoming leakage?

### Exhibit D — Model decision record

Show:

`hypothesis → baselines → temporal validation → usefulness gate failed → NOT DEPLOYED`

Question answered:

> Did we distinguish a model that ran from a model that was useful?

### Exhibit E — Product consequence

Show how the rejected predictive model changed the actual product contract: descriptive behavioral evidence only, explicit minimum-history behavior, and deterministic escalation.

Question answered:

> What did the product do differently because of the evidence?

---

## 9. Data Excellence completion standard

Before submission, this track is complete only when:

- every headline data/model claim links to a reproducible artifact or versioned result;
- public figures contain no organizer row-level data;
- data-quality examples are selected for decision relevance, not visual volume;
- the model null result is shown explicitly rather than buried;
- the README contains a concise Data & Evaluation entry point;
- the Intelligence surface distinguishes live operational telemetry from offline ground-truth evaluation;
- the deck/video contains the evidence → decision → consequence chain;
- the final claim-to-evidence review confirms that no stronger claim is made than the data support.

The objective is not to prove that Proof of One performed the most analysis.

It is to make **analytical judgment** inspectable.
