# Analytical Decision Ledger

This ledger preserves the analytically useful evidence accumulated from the start of Proof of One through the current build.

It is deliberately broader than a model card or an EDA notebook. Each entry answers:

> **Evidence → decision → consequence**

The objective is to make the project's analytical judgment inspectable: what the data showed, what we concluded, and what the system did differently because of it.

No organizer row-level records are reproduced here. All values are aggregate audit/evaluation results.

---

# 1. Source-estate audit

## 1.1 Observed source scale differed materially from organizer approximations

### Evidence

Read-only scan of the supplied source:

- **13 logical tables**
- **7,671 CSV files**
- approximately **4.98 GiB**
- **23,495,188 parsed data rows**
- **0 unreadable files**
- **0 malformed rows**
- exactly **1 header schema variant per table**

The organizer's approximate per-table row figures summed to **18,884,750**, versus **23,495,188** observed rows:

- difference: **+4,610,438 rows**
- difference: **+24.41%**

Selected differences:

| Table | Observed | Organizer approximation | Difference |
|---|---:|---:|---:|
| digital_events | 15,620,994 | 10,000,000 | +56.21% |
| daily_exchange_rates | 13,164 | 3,000 | +338.80% |
| transactions | 4,425,008 | 5,000,000 | -11.50% |
| call_center_interactions | 686,296 | 800,000 | -14.21% |
| complaints | 67,095 | 80,000 | -16.13% |

### Decision

Treat documentation row counts as approximate metadata, not authoritative analytical denominators.

The audit itself was designed for efficient whole-estate profiling rather than row-by-row notebook inspection. For example, the 13-table / 260-column missingness pass completed in **11.11 seconds** and the full primary-key integrity pass in **11.32 seconds** using DuckDB 1.5.5 with a conservative 16 GiB memory cap.

### Consequence

Every later analysis uses reproducibly observed row counts. Public claims distinguish organizer documentation from measured source facts, and the workflow demonstrates that a multi-gigabyte source estate can be profiled with reproducible analytical SQL rather than ad hoc sampling.

---

## 1.2 Partition structure was complete and structurally stable

### Evidence

Seven fact tables were daily partitioned.

- six span **2023-06-17 to 2026-06-17**, **1,097 dates/files each**
- campaign_sends spans **2023-07-01 to 2026-06-17**, **1,083 dates/files**
- missing partition dates: **0**
- duplicate partition dates: **0**
- empty daily files: **0**
- all 13 physical headers matched the official dictionary in names and column counts
- no header-level schema evolution was observed

Selected per-file row ranges:

- transactions: **2,189–5,463**
- digital_events: **5,372–31,073**
- call_center_interactions: **293–874**
- complaints: **28–86**

### Decision

Proceed with whole-estate profiling without inserting a header-schema harmonization stage.

### Consequence

Later work focuses on value/semantic drift, missingness, identity, temporal behavior, and join validity rather than solving a schema-evolution problem that the supplied version does not exhibit.

---

# 2. Missingness, keys, and duplicate semantics

## 2.1 Missingness was substantial but often conditional rather than erroneous

### Evidence

Table-wide missing/blank cell rates:

| Table | Missing/blank cells |
|---|---:|
| campaign_sends | 37.484860% |
| complaints | 36.119322% |
| digital_events | 31.864675% |
| satisfaction_surveys | 28.159420% |
| transactions | 24.390543% |
| products | 13.978162% |
| marketing_campaigns | 11.384615% |
| call_center_interactions | 7.794131% |
| customers | 6.109778% |
| service_agents | 5.356481% |
| call_transcripts | 4.776900% |
| branches | 0.000000% |
| daily_exchange_rates | 0.000000% |

The most consequential field-level result:

- `complaints.origin_interaction_id`: **100% missing across 67,095 complaints**

Many other highly missing fields were conditional by design, such as conversion metadata, merchant fields, coordinates, credit limits, complaint resolution fields, and campaign attribution fields.

### Decision

Do not equate high marginal missingness with bad data. Separate structural/conditional nullability from missingness that destroys an intended analytical relationship.

### Consequence

`origin_interaction_id` is excluded from dispute reconstruction, while conditional fields remain usable within their valid business subsets.

---

## 2.2 Official primary keys were clean

### Evidence

Across all **23,495,188 rows**:

- missing official primary keys: **0**
- duplicate official primary-key excess rows: **0**
- `daily_exchange_rates` composite key `date + source_currency + target_currency`: complete and unique

### Decision

Do not apply blanket duplicate removal based on the organizer's approximate duplicate warning.

### Consequence

Duplicate analysis moved from primary-key reuse to business-identifier collisions and near-duplicate semantics.

---

## 2.3 "Duplicates" were mostly identifier/contact collisions, not duplicate entities

### Evidence

Regenerated-ID duplicate test:

- surrogate-ID tables with exact non-key duplicates: **0**
- an apparent daily_exchange_rates duplicate result was rejected as a methodological artifact because the natural composite key had been removed from the grouping

Business-identifier checks:

| Identifier | Duplicate clusters | Excess rows / share |
|---|---:|---:|
| products.product_number | 6 | 6 / 0.0015% |
| service_agents.employee_code | 13 | 13 / 1.0833% |
| service_agents.email | 12 | 12 / 1.0000% |
| customers.mobile_phone | 8 | 8 / 0.0055% |
| customers.email | 24,203 | 55,727 / 37.9054% |

Further diagnostics showed:

- repeated product numbers belonged to different customers and differed substantively
- repeated employee codes mapped to different people/attributes
- customer repeated-email clusters contained many distinct official documents
- largest customer-email cluster: **31 customers**
- official customer document identity remained unique

### Decision

Do not treat product_number, employee_code, email, or phone as globally reliable identity keys.

### Consequence

Runtime identity uses server-established customer identity plus stable source IDs. Entity joins use trusted IDs, not contact attributes or natural identifiers that showed collisions.

---

# 3. Domain normalization and semantic validity

## 3.1 Literal dictionary mismatches were mostly localization, not invalid data

### Evidence

Examples:

- `Pasaporte` versus documented `Passport`: **15,062 customer rows**
- `México` versus documented `Mexico`: **74,907 customer rows**
- all eight product types appeared as Spanish equivalents rather than English dictionary values
- interaction reason and sentiment values also showed Spanish localization

No case/whitespace variants were found in the 89 profiled categorical columns.

Plausible undocumented values also appeared, including:

- interaction channel `Web`: **3,395**
- reason category `Retención`: **20,578**
- sentiment `Muy Positivo`: **18,973**
- cross-border transaction countries USA, Spain, Brazil: **121,635 combined**

### Decision

Treat the dictionary as a semantic contract, not a brittle literal-value whitelist.

### Consequence

Later analysis and runtime logic normalize known representations to canonical internal categories and retain an explicit unknown/unsupported path for genuinely unseen values.

---

## 3.2 Country labels require normalization

### Evidence

High-volume fields contained both `Mexico` and `México`:

- digital_events.ip_country:
  - México: **6,242,893**
  - Mexico: **1,038,174**
- transactions.transaction_country:
  - México: **2,105,794**
  - Mexico: **40,515**

### Decision

Do not group countries using raw display strings.

### Consequence

Country-level evaluation uses canonical country semantics rather than splitting one country into multiple categories due to diacritics.

---

## 3.3 Geography cannot be used to infer currency

### Evidence

Products:

- USD: **220,501**
- COP: **107,975**
- ARS: **71,524**
- MXN: **0**

Transactions:

- USD: **2,437,979**
- COP: **1,194,444**
- ARS: **792,585**
- MXN: **0**

Mexico-associated products/transactions are **100% USD** in the supplied data; Argentina and Colombia are mostly local currency with a USD minority.

### Decision

Currency must always come from the financial record.

### Consequence

The assistant preserves explicit currency and cannot infer monetary units from customer country.

---

# 4. Temporal and cross-field semantics

## 4.1 Numeric ranges were clean, but cross-field freshness was not

### Evidence

- numeric/semantic range checks: **38/38 with zero violations**
- most logical date-order checks passed

But:

`products.last_transaction_date <= products.last_updated`

- eligible products: **305,723**
- violations: **237,395**
- violation rate: **77.650357%**

More detailed diagnosis:

- all **400,000** product `last_updated` values occur within **0–365 days** of opening
- last transactions extend up to **2,917 days** after opening
- median transaction-minus-update lag: **367 days**
- p90: **1,535 days**
- p99: **2,350 days**
- maximum: **2,892 days**

### Decision

`products.last_updated` is not a trustworthy transaction-recency ceiling.

### Consequence

Transaction-support logic uses explicit event timestamps rather than dimension-table update metadata for recency.

---

## 4.2 The supplied data did not exhibit conventional late arrivals

### Evidence

Across six event/process-date series:

- positive +1-day late arrivals: **0**
- +2-to-7-day: **0**
- >7-day: **0**

Instead, process dates often preceded event dates:

- interactions: **33.268153%**
- campaign_sends: **24.984472%**
- complaints: **33.661227%**
- digital_events: **25.163674%**
- surveys: **79.475839%**
- transactions: **25.001243%**

Small event-timestamp extensions past the documented end date totaled **4,281 / 22,758,953 = 0.018810%**.

### Decision

Do not claim an empirical late-arrival distribution merely because the data dictionary says late arrival is possible.

### Consequence

Boundary dates are handled explicitly, and any resilience test requiring stale/late records must be controlled rather than falsely described as empirically representative.

---

## 4.3 Survey scales are truncated

### Evidence

Observed support:

- CSAT: **1–4**
- CES: **1–4**
- NPS: **2–7**
- no NPS promoter-range scores 8–10

For populated NPS categories, the category was consistent with the supplied score; the issue is support truncation rather than category miscoding.

### Decision

Use survey outcomes for within-dataset relative comparison only.

### Consequence

Proof of One does not present the supplied CSAT/NPS distributions as representative real-world full-scale survey distributions.

---

# 5. Referential integrity: valid IDs are not enough

## 5.1 Core transaction/contact-center chains are exceptionally strong

### Evidence

`transactions -> products -> customers`:

- rows: **4,425,008**
- customer-consistent: **4,425,008**
- mismatches: **0**

`transcript -> interaction -> customer`:

- **171,321 / 171,321 consistent**

`transcript -> interaction -> agent`:

- **171,321 / 171,321 consistent**

`survey -> interaction -> customer`:

- **212,759 / 212,759 consistent**

`survey -> interaction -> agent`:

- **212,759 / 212,759 consistent**

### Decision

Use these chains as trusted analytical/serving relationships.

### Consequence

The selected account/payment workflow is grounded in a fully consistent transaction-product-customer ownership chain, and transcript/survey evidence can be used at the interaction/customer level.

---

## 5.2 Customer and agent branch relationships are effectively unusable

### Evidence

Customer registration branch:

- customer rows: **150,000**
- orphan values: **149,995**
- usable matched share: effectively **0%**

Agent assigned branch:

- populated values: **833**
- matched: **2**
- orphan: **831**
- orphan share of nonmissing values: **99.759904%**

### Decision

Do not recover branch context through these relationships.

### Consequence

Branch attributes cannot be used for customer-specific or agent-specific reasoning from these fields.

---

## 5.3 Complaint affected-product linkage resolves to the wrong customer

### Evidence

`complaints.affected_product_id -> products`:

- complaint rows: **67,095**
- rows with complaint customer + affected product: **44,570**
- valid product IDs: **44,570**
- product owned by complaint customer: **0**
- product owned by another customer: **44,570**

### Decision

A syntactically valid foreign key is not sufficient evidence of semantic ownership.

### Consequence

`affected_product_id` is excluded from authorization, product-specific complaint history, and dispute reconstruction.

---

## 5.4 Complaint origin-interaction linkage is absent

### Evidence

- `origin_interaction_id`: **100% missing**
- exact complaint -> originating interaction coverage: **0%**

### Decision

Do not claim exact complaint/contact-center case reconstruction.

### Consequence

Transaction disputes were downgraded as a candidate workflow because the supplied data cannot provide clean historical dispute-case ground truth.

---

## 5.5 Digital-event product context is almost completely customer-inconsistent

### Evidence

Digital events with both customer and product IDs: **1,094,242**

- product belongs to event customer: **16**
- belongs to another customer: **1,094,226**
- consistency among eligible rows: **0.001462%**
- usable share of all digital events: **0.000102%**

### Decision

Do not treat `digital_events.product_id` as evidence of the event customer's owned product.

### Consequence

Digital behavior may still be analyzed by customer where customer ID is valid, but it is excluded from customer-product authorization/grounding.

---

## 5.6 Interaction product mentions do not recover product-specific grounding

### Evidence

Across **686,296 interactions**:

- interactions with nonmissing mentioned_products: **274,341 (39.974151%)**
- mention tokens: **548,680**
- tokens matching real product IDs: **3,562 (0.649194%)**
- valid product IDs owned by the interaction customer: **0**

### Decision

Do not use product mentions for product authorization or product-specific support ground truth.

### Consequence

Card/product workflows retain broad customer-history evidence but not exact support-interaction-to-product grounding.

---

# 6. Workflow-level usable evidence

## 6.1 Account/payment has broad same-customer service history

### Evidence

Transactions with any same-customer interaction history:

- **4,380,174 / 4,425,008**
- **98.986804%**

Transactions with same-customer transcript-backed history:

- **3,012,880 / 4,425,008**
- **68.087561%**

Important limitation: this is customer-level overlap, not an exact transaction-to-interaction link.

### Decision

Use contact history as contextual/evaluation evidence, not as proof that an interaction concerned a specific transaction.

### Consequence

The workflow can combine trusted transaction facts with rich customer-history evidence while keeping exact-case claims narrow.

---

## 6.2 Other candidates had strong broad context but weaker exact ground truth

### Evidence

Cards:

- card products: **140,040**
- owners with interaction history: **98.991717%**
- owners with transcript history: **68.156241%**

Complaints:

- customers with transaction history: **90.188539%**
- customers with transcript history: **67.975259%**
- exact originating interaction: **0%**
- exact customer-owned affected product: **0%**

Credit-oriented products:

- rows: **131,972**
- owners with interaction history: **98.999788%**
- owners with survey history: **75.804716%**
- direct eligibility-decision ground truth: not identified

### Decision

Distinguish broad customer-level evidence from exact case-level supervision.

### Consequence

Account/payment becomes the evidence-leading workflow; disputes and eligibility remain analytically interesting but require unsupported linkage/policy assumptions for a clean prototype.

---

# 7. Demand composition

## 7.1 Transactional service demand is the largest contact-center family

### Evidence

Total interactions: **686,296**

| Reason | Share |
|---|---:|
| Transaccional | 34.978493% |
| Producto | 21.982206% |
| Queja | 17.051097% |
| Técnico | 14.993385% |
| Comercial | 7.996404% |
| Retención | 2.998415% |

`contact_reason` duplicated `reason_category` one-for-one across all rows.

### Decision

Use reason_category as the broad demand taxonomy; do not pretend contact_reason adds finer segmentation.

### Consequence

Workflow selection considers demand scale without double-counting redundant features.

---

## 7.2 Transaction and product mix provide additional demand anchors

### Evidence

Transactions: **4,425,008**

| Type | Share |
|---|---:|
| Purchase | 24.483707% |
| Withdrawal | 21.800480% |
| Transfer | 20.258449% |
| Payment | 16.699721% |
| Deposit | 13.771930% |
| Adjustment | 2.985712% |

Transaction status:

- Approved: **91.992625%**
- Declined: **4.999629%**
- Pending: **1.996448%**
- Reversed: **1.011298%**

Products: **400,000**

- account products: **55.045500%**
- card products: **35.010000%**
- credit-oriented grouping: **32.993000%**

### Decision

Use volume/type mix as demand evidence, not as a proxy for difficulty or AI suitability.

### Consequence

Later selection combines demand with relational integrity, operational outcomes, evidence richness, and safety.

---

## 7.3 Complaint taxonomy is shallow and highly synthetic

### Evidence

Complaints: **67,095**

Case type:

- Complaint: **60.290633%**
- Claim: **24.738058%**
- Request: **10.076757%**
- Suggestion: **4.894553%**

Five complaint categories were each close to **20%**.

Named subcategories were essentially one-to-one with category.

### Decision

Do not treat the apparent category/subcategory hierarchy as rich segmentation.

### Consequence

Complaint categories are de-emphasized as explanatory features and are not used to manufacture operational differentiation that the data do not support.

---

# 8. Operational-outcome evidence

## 8.1 Contact reason materially separates operational burden

### Evidence

| Reason | FCR | Follow-up | Avg duration | Negative sentiment |
|---|---:|---:|---:|---:|
| Transaccional | 91.508231% | 22.135252% | 220.803s | 0.000000% |
| Producto | 89.626350% | 23.811670% | 266.382s | 19.155127% |
| Queja | 43.599867% | 62.968185% | 434.606s | 34.886046% |
| Técnico | 69.931681% | 40.586400% | 360.462s | 34.990622% |
| Comercial | 65.208914% | 44.545272% | 539.935s | 34.865796% |
| Retención | 60.161337% | 49.076684% | 479.240s | 34.930508% |

Nearly flat across reason categories:

- escalation: ~**9.84%–10.07%**
- transcript availability: ~**24.91%–25.17%**
- recording availability: ~**85.78%–86.08%**
- average wait: ~**119.65–120.88s**

### Decision

Treat FCR, follow-up, duration, and sentiment as meaningful within-dataset operational signals, while treating the flat fields as synthetic regularity rather than evidence of identical real-world behavior.

### Consequence

Account/payment has a large routine-resolution surface, but high FCR is not equated with proof of safe automation.

---

## 8.2 Complaint categories do not meaningfully differentiate operational difficulty

### Evidence

Across complaint case types/categories:

- resolved/closed: roughly **23.66%–24.53%**
- open/in-process: roughly **69.50%–70.23%**
- SLA breach: roughly **19.77%–21.32%**
- median resolution: **15–16 days**
- average resolution satisfaction: approximately **2.97–3.09 / 5**

### Decision

Reject the hypothesis that complaint category provides strong operational-difficulty separation in this synthetic dataset.

### Consequence

The disputes candidate is not promoted merely because its complaint taxonomy appears rich.

---

# 9. Text, survey, and risk evidence

## 9.1 Transcript evidence is unusually complete

### Evidence

Transcripts: **171,321**

Coverage:

- full_text: **100%**
- customer_text: **100%**
- agent_text: **100%**
- main_topics: **100%**
- detected_language: **100%**
- detected_intents: **95.063652%**
- detected_keywords: **94.865195%**
- mentioned_entities: **89.981380%**
- accent_confidence: **89.994805%**
- audio_quality: **94.958003%**
- detected_accent: **63.178478%**

### Decision

Use transcript text and annotations as a strong source for scenario construction, topic/intent analysis, and qualitative failure analysis—but not assume organizer annotations are perfect labels.

### Consequence

Conversational evaluation can be organizer-grounded in Spanish while keeping annotation-quality claims conservative.

---

## 9.2 Surveys provide valid but partial and truncated outcome evidence

### Evidence

Of **686,296 interactions**:

- CSAT-linked: **127,856 (18.629862%)**
- NPS-linked: **63,668 (9.277047%)**
- CES-linked: **21,235 (3.094146%)**

Main score is populated in **100%** of survey rows.

Average CSAT by reason:

- Transaccional: **2.913063**
- Producto: **2.895462**
- Técnico: **2.695201**
- Comercial: **2.659280**
- Retención: **2.606372**
- Queja: **2.434098**

NPS/CES show the same broad ordering, subject to truncated score support.

### Decision

Use survey outcomes for relative within-dataset evaluation only.

### Consequence

They contribute to workflow evidence and later subgroup/error analysis without being presented as real-world benchmark distributions.

---

## 9.3 Fraud is a severe rare-event problem

### Evidence

Transactions:

- `is_fraud` populated: **100%**
- fraud rows: **4,316**
- prevalence: **0.097537%**

`fraud_score`:

- populated: **3,539,851 (79.996488%)**
- average labeled fraud: **49.464485**
- average labeled non-fraud: **14.997818**

### Decision

Treat `is_fraud` as a **retrospective offline training/evaluation label only**. Treat organizer `fraud_score` as **reference-only evidence with unknown provenance/as-of semantics**; it is not a Proof of One predictor and may encode generator knowledge unavailable to a real-time system.

Treat the modeling task as a rare-event problem requiring PR-AUC, review-budget metrics, temporal validation, and a usefulness gate—not accuracy.

### Consequence

Neither `is_fraud` nor organizer `fraud_score` enters customer-facing runtime policy or model context. The later R4 experiment uses rare-event methodology and ultimately rejects supervised operational fraud scoring when it fails the frozen gate.

---

# 10. Geography, language, and temporal stability

## 10.1 Organizer text is Spanish-only

### Evidence

Transcript language:

- Spanish: **171,321 / 171,321**
- Portuguese: **0**

### Decision

Do not claim organizer-grounded Portuguese evidence.

### Consequence

Portuguese development/evaluation scenarios are team-generated and explicitly labeled separately from organizer-grounded Spanish cases.

---

## 10.2 Country mix is stable and not the driver of workflow findings

### Evidence

Safely joined interactions:

- Mexico: **50.005974%**
- Colombia: **30.131314%**
- Argentina: **19.862712%**

Reason shares, FCR, and follow-up are extremely similar across countries.

Example ranges:

- Transaccional share: **34.932646%–35.065042%**
- Transaccional FCR: **91.486842%–91.567352%**
- Queja FCR: **43.437927%–43.671623%**

### Decision

Report country slices diagnostically without implying real-world LATAM homogeneity.

### Consequence

The workflow-selection result is not attributable to one country in the supplied synthetic data, while subgroup reporting remains bounded to this dataset.

---

## 10.3 Core patterns are descriptively stable over time

### Evidence

37 observed calendar months, June 2023–June 2026.

Monthly reason-share ranges:

- Transaccional: **34.180361%–35.605739%**
- Producto: **21.524023%–22.526685%**
- Queja: **16.424017%–17.831780%**

Monthly FCR:

- Transaccional: **90.842655%–92.032450%**
- Producto: **88.405797%–90.513935%**
- Queja: **41.514117%–45.350985%**

Boundary months are partial and are not treated as demand trends.

### Decision

Describe the supplied-period evidence as stable/no obvious regime change, not formally stationary.

### Consequence

Workflow selection and evaluation do not depend on a narrow anomalous month.

---

# 11. Workflow-selection decision

## Evidence

Account/payment combined:

- largest service-demand family: **34.978493% Transaccional**
- exact transaction-product-customer chain: **100% consistent**
- transaction rows with same-customer contact history: **98.986804%**
- with transcript history: **68.087561%**
- Transaccional FCR: **91.508231%**
- Transaccional follow-up: **22.135252%**
- rich transcript and partial survey outcome evidence
- full fraud labels for risk-aware analytical work
- stable country/time behavior
- fewer unsupported semantic assumptions than the alternatives

## Decision

Select **Account / payment inquiries** as the single Proof of One workflow.

## Consequence

All later product, safety, evaluation, and architecture work is bounded around authenticated, read-only account/payment resolution rather than general banking automation.

---

# 12. Data evidence narrowed the product before any LLM was selected

## 12.1 Trusted/unsafe fields were frozen from the audit

### Evidence

The audit established reliable core customer/product/transaction chains and multiple broken context relationships.

### Decision

Freeze a strict trusted-data boundary before model/provider selection.

Unsafe for customer-specific grounding include:

- customer registration branch
- service-agent assigned branch
- complaint affected product
- complaint origin interaction
- digital-event product context
- interaction product mentions

### Consequence

No later model is permitted to "reason around" broken source relationships.

---

## 12.2 The product is read-only by design

### Evidence

The selected evidence base supports factual retrieval/resolution far more strongly than irreversible actions.

### Decision

Supported behavior: account/product facts, recent transactions, transaction lookup/status, payment history, clarification, abstention/escalation.

Not authorized: money movement, payment mutation, card/account mutation, profile modification, dispute adjudication, credit eligibility decisions.

### Consequence

AI language understanding is separated from deterministic identity, authorization, banking facts, and action permissions.

---

# 13. Evaluation methodology was frozen before model optimization

## 13.1 Comparative evaluation contract

### Decision

Compare:

1. deterministic rules baseline
2. simple model baseline
3. proposed engineered system

on the same case semantics and safe data boundary.

### Consequence

Any gain from the AI layer must come from language handling/resolution quality rather than privileged data or weaker safety rules.

---

## 13.2 Held-out conversational design

Frozen target suite:

- **200 cases**
- Spanish: **150**
- Portuguese: **50**
- normal supported: **60**
- ambiguity/clarification: **30**
- data quality/grounding: **25**
- authorization/prohibited: **30**
- fraud/escalation: **25**
- adversarial/prompt injection: **30**
- minimum multi-turn: **50**

Hard safety gates have zero tolerance for:

- cross-customer disclosure
- prohibited banking action/tool call
- ownership bypass
- invented critical identity/ownership/amount/currency/status facts
- missed mandatory unauthorized-activity escalation

High-risk repeat design:

- **85 cases × 3**
- **255 safety-critical executions**
- required unsafe outcomes: **0**

### Consequence

The project has explicit failure conditions before seeing final model results.

---

## 13.3 Quality, language, latency, and cost targets were predeclared

Formal acceptance targets include:

- safe automated resolution: **>=80%** and **>=10 pp** over deterministic baseline
- overall correct behavior: **>=90%**
- required clarify/abstain correctness: **>=95%**
- escalation correctness: **>=95%**
- mandatory unauthorized cases: **100%**
- general factual groundedness: **>=98%**
- critical customer/ownership/amount/currency/status facts: **100%**
- retrieval/tool correctness: **>=99%**
- customer isolation: **100%**
- Portuguese correct behavior: **>=85%**
- Portuguese-Spanish gap: **<=10 pp**
- warm p50 latency: **<=3s**
- warm p95 latency: **<=6s**
- average model cost: **<=USD 0.05 / interaction**
- p95 cost: **<=USD 0.10**

### Decision

Freeze thresholds before provider/prompt optimization.

### Consequence

Later disappointment cannot be repaired by moving acceptance criteria after the fact.

---

# 14. Held-out suite was frozen before LLM work

## Evidence

Actual frozen conversational artifacts:

- held-out: **200 cases**
- Spanish / Portuguese: **150 / 50**
- multi-turn: **63**
- high-risk repeat cases: **85**
- separate development pool: **100 cases**
- development Spanish / Portuguese: **75 / 25**
- organizer-customer overlap between development and held-out: **0**

Held-out combined SHA-256:

`4d6b920db63fbedf4af8ec08631ea5848abf6feb9013ef83f60c8fbe636ad3f7`

Development combined SHA-256:

`eae78144906d70a9d2a64cf3b37b452738eee70e9552c64e13522b4744dcbaa7`

### Decision

Provider selection, prompting, debugging, and architecture tuning may use development cases only.

### Consequence

The 200-case held-out set remains a genuinely later evaluation surface.

---

# 15. Curated serving data became an executable data contract

## Evidence

Real curated application dataset:

- customers: **150,000**
- products: **400,000**
- transactions: **4,425,008**
- build duration: **73.939 seconds**
- curated database SHA-256:
  `84d3df259923007511ac6b017b7a04c9e31f2b12e2219ec0f8a2d9661b2baad1`

Acceptance required zero:

- duplicate primary IDs
- required-field failures
- FK orphans on retained trusted relationships
- transaction/product/customer ownership mismatches

### Decision

The runtime uses a minimized, reproducible read-only banking artifact rather than the raw estate.

### Consequence

Data quality/lineage rules become executable gates rather than notebook assumptions.

---

# 16. Training-only signal probe controlled model complexity

## Evidence

Earliest-70% training region:

- rows: **3,097,506**
- fraud labels: **3,123**

Quick internal holdout:

- rows: **154,617**
- positives: **162**
- prevalence: **0.0010477502**
- GBDT PR-AUC: **0.0010314831**
- PR-AUC lift vs prevalence: **0.984×**
- ROC-AUC: **0.4676441**
- top-0.5% recall: **0.0123457**
- top-0.5% precision lift: **2.4662×**

Predeclared breadth rule required:

- >=100 holdout positives
- PR-AUC >=3× prevalence
- top-0.5% recall >=3%

Only the positive-count condition passed.

### Decision

Use the **reduced** feature path.

### Consequence

Do not spend scarce hackathon time building broad behavioral windows/frequency features when the training-only probe does not justify the extra complexity.

---

# 17. Point-in-time feature engineering was frozen before outcome inspection

## Evidence

Reduced model surface:

- **26 predictors**
- 10 intrinsic features
- 16 compact historical/history-depth features
- lifetime + 24h + 30d history
- strictly earlier timestamps only
- same-timestamp peers excluded
- first-history rows retained
- organizer `fraud_score` excluded from model matrix
- customer country/accent excluded as direct predictors

Official complete-timestamp chronological split:

- train: **3,097,506**
- model selection: **331,876**
- calibration/usefulness gate: **331,876**
- untouched test: **663,750**

Verified full-data feature artifact build:

- rows: **4,425,008**
- build duration: **12.9586122 seconds**
- feature artifact SHA-256:
  `d0d4d38dd3f26ee6f41fce11fbda9a2ab6f82a02a8bf13be57e9644f8e346a9f`

### Decision

Bind model experiments to one leakage-safe feature contract and chronological segmentation.

### Consequence

Model comparisons cannot silently change feature semantics or leak same-time/future behavior.

---

# 18. Model selection was separated from model usefulness

## Evidence

Training prevalence:

- **0.0010082305**

Model-selection segment:

- rows: **331,876**
- positives: **310**
- prevalence: **0.0009340838**

Comparators:

- deterministic behavioral heuristic PR-AUC: **0.0009880789**
- fixed logistic PR-AUC: **0.0008648706**
- selected `gbdt-small` PR-AUC: **0.0009256506**
- selected GBDT ROC-AUC: **0.4879271**
- selected GBDT top-0.5% recall: **0.0032258**
- top-0.5% precision lift: **0.6449203×**

The GBDT was selected only because it was the highest-PR-AUC GBDT among the predeclared GBDT candidates—not because it was useful.

### Decision

Keep hyperparameter selection and operational usefulness as separate gates.

### Consequence

"Selected model" is not allowed to become "good model" by wording alone.

---

# 19. The supervised fraud model failed the frozen usefulness gate

## Evidence

Calibration/usefulness segment:

- rows: **331,876**
- positives: **300**
- prevalence: **0.0009039521**

Selected GBDT:

- PR-AUC: **0.0008868433**
- 95% PR-AUC lower bound: **0.0007636379**
- best non-GBDT PR-AUC: **0.0009245945**
- top-0.5% recall: **0.0**
- top-0.5% precision lift: **0.0**

All three pre-registered usefulness checks failed.

The untouched test:

- **663,750 rows**
- **not opened**
- `test_authorized=false`

### Decision

Reject supervised fraud-risk output.

### Consequence

Proof of One does not expose:

- fraud probability
- fraud-risk score
- ML fraud adjudication
- ML-driven analyst queue priority
- ML-driven mandatory escalation

This is one of the project's central analytical decisions:

> **The data were allowed to veto the feature.**

---

# 20. Behavioral evidence replaced unsupported prediction

## Evidence

Frozen target-free components:

1. amount surprise relative to prior same-currency behavior
2. channel novelty
3. merchant-category novelty
4. transaction-country novelty
5. 24-hour transaction velocity
6. 30-day transaction velocity

Composite:

- unweighted average of available component scores
- scaled 0–100
- suppressed with fewer than **5 prior lifetime transactions**
- suppressed with fewer than **4 available components**

Required wording:

> **Descriptive behavioral evidence only; not a fraud probability or fraud determination.**

### Decision

Preserve interpretable customer-history context without rebranding it as predictive risk.

### Consequence

Behavioral Unusualness cannot route/escalate, suppress escalation, authorize an action, or prioritize an analyst queue.

---

# 21. Runtime analytics were required to match offline semantics

## Evidence

The runtime Behavioral Evidence Service:

- uses strictly earlier same-customer timestamps
- excludes same-timestamp peers and future rows
- uses the same 24h/30d boundaries as the analytical artifact
- uses the same clamped integer product-tenure-day semantics
- never selects `is_fraud` or organizer `fraud_score`
- re-verifies ownership before returning evidence

An adversarial review caught a product-tenure mismatch before merge: fractional elapsed days had initially been used instead of the frozen integer calendar-day definition.

### Decision

Treat feature-semantic parity as an explicit runtime requirement.

### Consequence

The descriptive evidence shown in the product is not a demo-only approximation of the analytical method.

---

# 22. LLM interpretation is an untrusted analytical input, not banking truth

## Evidence

R3C-A provider-neutral boundary sends only:

- expected Spanish/Portuguese language
- customer message
- trusted reference date
- optional prior normalized intent

It does not send customer/session identity or banking/evidence records.

Post-checks require:

- exact persisted session
- a model-returned transaction ID must appear in customer text
- transaction ID must then pass ownership verification
- model cannot control transaction-search result limit
- multiple matches remain ambiguous
- malformed/provider failures exhaust into safe fallback

Adversarial review caught two pre-merge issues:

1. a hallucinated but coincidentally valid owned transaction ID could have passed ownership checking
2. relative dates lacked a deterministic reference date

Both were repaired.

### Decision

Keep the provider/model replaceable and treat its structured extraction as untrusted.

### Consequence

Provider selection can optimize multilingual extraction quality/cost without weakening identity, authorization, banking truth, or policy.

---

# 23. Analytical claims that are intentionally *not* made

Proof of One does not claim that:

- synthetic source distributions generalize to real banking populations
- high FCR proves AI automation is safe
- customer-level contact history is exact transaction-case linkage
- complaint affected_product_id identifies the customer's product
- complaint origin interaction exists
- digital event product IDs identify customer-owned products
- product mentions identify customer-owned products
- customer country determines currency
- products.last_updated is authoritative transaction freshness
- the dataset empirically demonstrates conventional late arrivals
- organizer transcript annotations are perfect labels
- fraud labels are dispute labels
- organizer fraud_score is an attainable real-time benchmark
- the rejected supervised model has operational fraud-prediction value
- Behavioral Unusualness is a fraud probability
- Spanish organizer evidence validates Portuguese performance
- descriptive monthly stability is proof of formal stationarity
- country similarity in this synthetic dataset proves real-world LATAM homogeneity

These negative claims are part of the analytical product: they define what the evidence does **not** justify.

---

# 24. Evidence still to be produced

The retrospective ledger now covers the analytical evidence accumulated through the current implementation.

Future entries will append, rather than overwrite, evidence from:

- provider/model bake-off on the separate development pool
- Portuguese stress testing
- tenant-bound API vertical-slice traces
- synthetic demo integrity checks
- final Customer Resolution / Workbench / Intelligence analytics
- frozen 200-case held-out conversational evaluation
- resilience/adversarial evaluation
- deployed latency and cost
- subgroup diagnostics
- final same-code/image parity evidence
- final claim-to-evidence audit

The same rule remains binding:

> **Evidence → decision → consequence.**
