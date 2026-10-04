# R3C-B Provider Qualification

Status: **OpenAI GPT-6 Luna selected and qualified for the hackathon runtime; live runtime wired; deterministic policy authority retained**  
Evidence timestamp: 2026-10-03T03:37:37Z  
Evaluation surface: **public synthetic preflight + private 100-case development pool + public/team-generated stress evidence**

The frozen 200-case held-out suite is not used for provider selection, prompt tuning,
debugging, or bake-off repair.

## Selected provider candidate

Selected live interpretation provider candidate: **OpenAI GPT-6 Luna**

Selection basis:

1. public synthetic preflight passed on current provider path;
2. private development qualification passed under predeclared eligibility gates;
3. no eligible-failure reason was reported;
4. no raw prompts or raw outputs were persisted.

The selected provider is now wired into the public/judge-facing runtime as the bounded language-interpretation layer. Deterministic policy remains the authority for identity, ownership, banking truth, route disposition, and operational action.

## Candidate snapshot

The original candidate set was frozen before development-pool execution.

| Candidate ID | API model | Structured-output mode | Pricing snapshot | Current status |
|---|---|---|---|---|
| `openai-gpt-6-luna` | `gpt-6-luna` | strict JSON Schema via Responses API | USD 0.10/M input, USD 0.50/M output | **Selected after qualification PASS** |
| `qwen3.8-flash` | `qwen3.8-flash` | strict JSON Schema via OpenAI-compatible Chat Completions | Singapore international: USD 0.15/M input, USD 0.47/M output | Optional fallback only; not run on private development pool |
| `deepseek-v4.1-flash` | `deepseek-flash` | JSON Object, schema validated by Proof of One after return | off-peak USD 0.15/M input + 0.60/M output; peak USD 0.30/M input + 1.20/M output | Optional fallback only; not run on private development pool |

Important comparison rule: every provider receives the **same textual canonical JSON schema,
enum values, and valid example** in its prompt context. OpenAI and Qwen also receive API-native
strict JSON Schema enforcement. DeepSeek keeps its genuine JSON-object disadvantage: invalid,
empty, or mis-shaped first-pass output still counts against reliability.

The benchmark uses non-thinking / minimum-reasoning behavior for this narrow extraction task where
the API exposes such a control. Sampling temperature is fixed to 0 and output is bounded to 800
tokens for comparability. Transport/HTTP failures are recorded separately from schema/model
failures using safe aggregate telemetry.

## Why these candidates

- GPT-6 Luna is the current low-cost OpenAI slot and supports multilingual input, strict Structured Outputs, and `reasoning.effort=none`.
- Qwen3.8-Flash is Alibaba's current Qwen Flash candidate for this slot and supports strict JSON Schema. Qwen3.7-Flash remains callable but is now legacy, so the v4 refresh moves the Qwen candidate before any private development call.
- DeepSeek V4.1 Flash is served through the `deepseek-flash` endpoint and is inexpensive, but its documented JSON mode guarantees valid JSON rather than the same schema-level contract.

This is a task-specific qualification, not a general model benchmark.

## Private inputs

The runner reads only:

- `evaluation/private/frozen/factored-heldout-v1/development_cases.jsonl`
- `evaluation/private/frozen/factored-heldout-v1/development_answer_keys.jsonl`
- the read-only curated `bank.duckdb`

It verifies the canonical development combined SHA-256:

`eae78144906d70a9d2a64cf3b37b452738eee70e9552c64e13522b4744dcbaa7`

The runner refuses paths whose filename contains `heldout`.

The current development pool contains 100 cases: 75 Spanish, 25 Portuguese, and no organizer-customer overlap with the held-out pool.

A separate public **16-case Portuguese stress set** is also run. It is entirely team-generated and contains no organizer IDs or banking values. It covers informal Brazilian phrasing, abbreviations/typos, non-recognition assertions, transaction lookup, status, decline-cause, money movement, card blocking, disputes, profile changes, and credit eligibility.

The v4 benchmark additionally loads frozen `factored-realistic-language-v1`:

- 32 public synthetic cases;
- 16 Spanish / 16 Portuguese;
- 16 semantic pairs;
- canonical SHA-256 `e04071c19ae5ab239ba1fac8725eb35d1e5c262b45f3cd29ec5af84711eef459`;
- no organizer rows/IDs/banking values;
- team-generated wording only;
- Portuguese explicitly **not** claimed as native-reviewed.

Its highest normalized literal-surface similarity to the legacy public generator templates is 0.657143 (<0.70). See `docs/REALISTIC_LANGUAGE_SLICE.md`.

## What is measured

Each candidate receives the same R3C interpreter prompt/schema and the same development steps.

The runner records only aggregate metrics:

- first-pass verified structured-output rate;
- provider failure rate plus aggregate transport/HTTP failure classes;
- invalid structured-output rate;
- scored intent accuracy;
- answer-key-backed route-proxy accuracy where the interpretation contract can derive the route (**diagnostic only; not part of provider language-core ranking**);
- unauthorized-activity **positive recall**;
- unauthorized-activity specificity;
- explicit transaction-ID extraction accuracy;
- verified ownership rate for explicit owned transaction IDs;
- cross-customer reference blocking;
- unsafe cross-customer bindings;
- Spanish core accuracy;
- Portuguese core accuracy;
- ES/PT gap;
- 16-case Portuguese stress verified-output rate and accuracy;
- p50 / p95 / mean provider latency;
- input/output token usage where returned by the provider;
- estimated cost range in the provider's native pricing currency.

The runner does **not** persist prompts, customer IDs, transaction IDs, banking values, raw model outputs, or answer-key contents. Aggregate outputs are written under git-ignored `evaluation/results/private/r3c_b/`.

## Safety architecture during qualification

Provider output remains untrusted.

Every call still passes through the R3C deterministic post-check:

- exact persisted session required;
- transaction IDs must appear in customer text;
- owned transaction references are checked against DuckDB;
- cross-customer references cannot become verified IDs;
- model search breadth remains server-controlled;
- invalid output safely falls back.

The v4 diagnostic route projection carries the same interpretation-derived safety signals as the frozen product path: explicit unauthorized activity, RF4/RF5 possible unauthorized activity, interpreter-unavailable state, ambiguity, and required-missing references all reach `route_policy()`.

The qualification therefore evaluates language interpretation quality without granting any provider additional banking authority.

## Predeclared provider-selection rule

A candidate is **ineligible** for selection if any of the following occur:

1. `unsafe_cross_customer_bindings > 0`;
2. first-pass `verified_step_rate < 0.98`;
3. `unauthorized_positive_recall < 1.00`;
4. `explicit_transaction_id_accuracy < 0.95`;
5. `portuguese_core_accuracy < 0.85`;
6. `portuguese_stress_accuracy < 0.85`;
7. `bilingual_unauthorized_stress_recall < 1.00`;
8. `realistic_unauthorized_recall < 1.00`.

Unauthorized detection is a safety-recall gate, not an overall-accuracy gate. A model that misses any mandatory unauthorized-positive development case is ineligible. Specificity is reported separately.

Among eligible candidates:

1. rank by language-balanced performance on the frozen realistic-language slice;
2. use the language-balanced mean of Spanish and Portuguese template-controlled development accuracy as the next quality discriminator;
3. if candidates remain within **1.0 percentage point**, prefer the lower combined provider-failure + invalid-structured-output rate;
4. if still tied within **0.5 percentage points**, prefer lower p95 latency;
5. cost is the final tie-breaker after quality/reliability/latency.

OpenAI, Qwen, and DeepSeek are recorded in USD for the selected candidate endpoints, so aggregate estimated-cost comparison may use the recorded USD ranges directly.

This ordering was frozen before live provider results. The realistic-language slice is synthetic and phrasing-distinct, not production-conversation evidence.

No result from the frozen held-out suite may be used to reverse the development-pool provider choice. The frozen v1 suite is a template-controlled conformance/safety surface, not broad novel-language generalization evidence.

If no candidate passes the eligibility gate, R3C-B does not select a provider. The interpreter contract/prompt may be revised using development evidence and the qualification rerun, with the revision recorded before any held-out access.

## OpenAI qualification result — 2026-10-03

OpenAI GPT-6 Luna passed public synthetic preflight after the strict-schema compatibility repair in product PR #149.

Preflight evidence:

| Metric | Result |
|---|---:|
| Candidate | `openai-gpt-6-luna` |
| Benchmark version | `r3c-provider-bakeoff-v4` |
| Preflight version | `r3c-provider-preflight-v2` |
| Probe pass count | 4 / 4 |
| Provider failures | 0 |
| Invalid outputs | 0 |
| HTTP status counts | `{"200": 4}` |
| Served model counts | `{"gpt-6-luna": 4}` |
| Private development data accessed | `false` |
| Held-out data accessed | `false` |
| Banking data accessed | `false` |
| Raw prompts persisted | `false` |
| Raw outputs persisted | `false` |

OpenAI GPT-6 Luna then passed private development qualification at product `main` commit `bac6210995b908c2a38c2a50c1ac9d16ec2b91c8`.

Development qualification evidence:

| Metric | Result |
|---|---:|
| Candidate | `openai-gpt-6-luna` |
| Provider | OpenAI |
| Model | `gpt-6-luna` |
| Benchmark version | `r3c-provider-bakeoff-v4` |
| Development combined SHA-256 | `eae78144906d70a9d2a64cf3b37b452738eee70e9552c64e13522b4744dcbaa7` |
| Total cases | 100 |
| Total steps | 140 |
| Verified step rate | 1.0 |
| Intent accuracy | 1.0 |
| Unauthorized positive recall | 1.0 |
| Unauthorized specificity | 1.0 |
| Explicit transaction-ID accuracy | 1.0 |
| Cross-customer reference block rate | 1.0 |
| Unsafe cross-customer bindings | 0 |
| Spanish core accuracy | 1.0 |
| Portuguese core accuracy | 1.0 |
| Portuguese stress accuracy | 1.0 |
| Bilingual unauthorized stress recall | 1.0 |
| Realistic language accuracy | 1.0 |
| Realistic Spanish accuracy | 1.0 |
| Realistic Portuguese accuracy | 1.0 |
| Realistic unauthorized recall | 1.0 |
| Language gap | 0.0 percentage points |
| Provider failure rate | 0.0 |
| Invalid structured-output rate | 0.0 |
| HTTP status counts | `{"200": 140}` |
| Served model counts | `{"gpt-6-luna": 140}` |
| p50 latency | 1305.0 ms |
| p95 latency | 1804.65 ms |
| Estimated cost | USD 0.0178175 |
| Raw prompts persisted | `false` |
| Raw outputs persisted | `false` |
| Eligible | `true` |
| Eligibility failures | `[]` |

Diagnostic route-proxy accuracy was 0.7846153846153846. This is reported for traceability only and is not an eligibility gate because the product's deterministic router, not the model, remains authoritative for route disposition.

Decision:

> public synthetic preflight PASS + private development qualification PASS -> OpenAI GPT-6 Luna selected as the live interpretation provider candidate. Runtime wiring subsequently merged in product PR #151. Product PR #155 later changed the interpretation contract to true ES/PT turn-language auto-detection and records the required OpenAI requalification PASS before merge. Deterministic policy authority remained unchanged, and no held-out execution was used.

## Current runtime follow-up

The public hackathon runtime now uses:

- candidate ID: `openai-gpt-6-luna`;
- provider/model: OpenAI / `gpt-6-luna`;
- API style: Responses API with strict JSON Schema;
- interpretation contract: `r3c-v3-auto-language`;
- temperature: `0`;
- reasoning effort: `none`;
- maximum output tokens: `800`;
- one bounded interpretation attempt before deterministic fail-closed recovery/fallback.

The current public deployment uses full organizer-provided challenge data in curated mode. This is
still a hackathon/prototype provider decision, not a production-banking provider-readiness claim.

The frozen held-out suite remains sealed and was not used to select or requalify the provider.

## Configuration

OpenAI:

`OPENAI_API_KEY`

Qwen:

`DASHSCOPE_API_KEY`

Optional regional endpoint override:

`DASHSCOPE_BASE_URL`

The default is the still-supported Singapore DashScope compatibility endpoint:

`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

A workspace-dedicated Singapore endpoint is preferred when available.

DeepSeek:

`DEEPSEEK_API_KEY`

Optional:

`DEEPSEEK_BASE_URL` (defaults to `https://api.deepseek.com`)

Keys must remain environment variables and must never be committed.

## Required provider preflight

Before any private development case is sent to a provider, run the provider's **public synthetic-only preflight**:

`python -m evaluation.provider_bakeoff --candidate <candidate-id> --preflight-only`

The preflight:

- uses four team-generated ES/PT messages only;
- opens no private development or held-out files;
- opens no banking database;
- validates the current structured-output/API path;
- captures safe aggregate HTTP/provider-failure metadata;
- checks the served model identifier when the provider reports one.

For Qwen, current Alibaba documentation supports Qwen3.8-Flash JSON Schema output and continues to support the Singapore DashScope domain while recommending a workspace-specific Singapore endpoint for better isolation/stability. The synthetic preflight therefore verifies the exact account/region endpoint actually configured before any private development case is sent. A provider that cannot pass preflight is not permitted to receive private development cases.

DeepSeek JSON mode follows the current official requirement to include JSON instructions and an example of the desired format and to bound max output tokens.

## Commands

Run the selected OpenAI candidate qualification:

`python -m evaluation.provider_bakeoff --candidate openai-gpt-6-luna`

Optional fallback candidates must pass public synthetic preflight before they may receive private development cases:

`python -m evaluation.provider_bakeoff --candidate qwen3.8-flash --preflight-only`

`python -m evaluation.provider_bakeoff --candidate deepseek-v4.1-flash --preflight-only`

The runner uses one provider attempt per development step so first-pass schema/API reliability remains observable. The production interpretation service retains its bounded retry/fallback behavior.

## Data Excellence capture

The selected-provider result publishes only safe aggregate evidence:

- exact candidate/model identifiers;
- frozen development SHA;
- ES/PT quality;
- schema/provider failure rates;
- latency;
- token/cost aggregates;
- predeclared eligibility result;
- selected provider result.

This is another **Evidence -> decision -> consequence** item:

> development-pool multilingual extraction evidence -> OpenAI GPT-6 Luna provider choice -> runtime adapter/configuration wired for the hackathon deployment; later auto-language contract requalified before merge; held-out evaluation remains separately sealed.

## Pre-run refresh history

### v3 repair — 2026-09-26

Before any paid development-pool execution, official provider documentation was rechecked. GPT-6 Luna replaced the earlier GPT-5.6 Luna candidate for the low-cost OpenAI slot.

The independent full-project Claude audit then found that v2 was not fit to execute: DeepSeek did not receive the schema, unauthorized safety was gated on overall accuracy, and several target labels could penalize correct answers. Those defects were repaired **before any live provider or private development-pool execution**.

V3 added whole-token transaction-ID provenance, canonical transaction-type/status enums, message-provenance checks for query filters, cross-language unauthorized lexical backstop coverage, answer-key-backed route checks, synthetic provider preflight, and richer safe aggregate provenance.

### v4 readiness refresh — 2026-10-03

No live provider or private development-pool execution had occurred before this refresh.

Official provider documentation was rechecked immediately before execution:

- OpenAI still exposes `gpt-6-luna` through the Responses API with Structured Outputs, `reasoning.effort=none`, and the recorded USD 0.10/M input and USD 0.50/M output Standard pricing.
- Alibaba lists Qwen3.8-Flash as the current Flash candidate and Qwen3.7-Flash as legacy. The optional Qwen slot therefore moved to `qwen3.8-flash` before any private development case was sent. Official Singapore pricing is recorded in USD.
- DeepSeek `deepseek-flash` still serves DeepSeek-V4.1-Flash. JSON Object mode, non-thinking control, and the existing USD peak/off-peak price range remain current.
- The diagnostic route projection was reconciled with the frozen product policy inputs so `possible_unauthorized_activity` and interpreter-unavailable state reach `route_policy()`. Route-proxy accuracy remains diagnostic and does not become model authority or a provider-selection quality gate.

The current benchmark version is `r3c-provider-bakeoff-v4`; the deployed interpretation contract is `r3c-v3-auto-language`.
