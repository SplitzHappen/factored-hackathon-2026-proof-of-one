# R3C-B Provider Bake-off

Status: **v3 repaired harness; live execution still blocked pending realistic-language slice, terms clearance, and bounded Claude repair confirmation**  
Evidence date: 2026-09-26  
Evaluation surface: **private 100-case development pool + public/team-generated stress evidence after synthetic provider preflight**

The frozen 200-case held-out suite is not used for provider selection, prompt tuning,
debugging, or bake-off repair.

## Candidate snapshot

The starting candidate set is frozen before development-pool execution.

| Candidate ID | API model | Structured-output mode | Pricing snapshot |
|---|---|---|---|
| `openai-gpt-6-luna` | `gpt-6-luna` | strict JSON Schema via Responses API | USD 0.10/M input, USD 0.50/M output |
| `qwen3.7-flash` | `qwen3.7-flash` | strict JSON Schema via OpenAI-compatible Chat Completions | Singapore international, <=32K: USD 0.030/M input, USD 0.130/M output |
| `deepseek-v4.1-flash` | `deepseek-flash` | JSON Object (schema validated by Proof of One after return) | off-peak USD 0.15/M input + 0.60/M output; peak USD 0.30/M input + 1.20/M output |

Important comparison rule: every provider receives the **same textual canonical JSON
schema, enum values, and valid example** in its prompt context. OpenAI and Qwen also
receive API-native strict JSON Schema enforcement. DeepSeek keeps its genuine JSON-object
disadvantage: invalid/empty/mis-shaped first-pass output still counts against reliability.
This repairs the v2 harness defect where DeepSeek was asked to satisfy a schema it never
received.

The benchmark uses non-thinking / minimum-reasoning behavior for this narrow extraction
task where the API exposes such a control. Sampling temperature is fixed to 0 and output
is bounded to 800 tokens for comparability. Transport/HTTP failures are recorded separately
from schema/model failures using safe aggregate telemetry.

## Why these candidates

- GPT-6 Luna is the current low-cost OpenAI tier, released September 22, 2026, and supports multilingual input, strict Structured Outputs, and `reasoning.effort=none`.
- Qwen3.7-Flash is a low-cost current Qwen Flash model, supports strict JSON Schema, and
  Alibaba documents Portuguese among Qwen's supported languages.
- DeepSeek V4.1 Flash is the current `deepseek-flash` endpoint and is inexpensive, but
  its documented JSON mode guarantees valid JSON rather than the same schema-level
  contract.

This is a task-specific comparison, not a general model benchmark.

## Private inputs

The runner reads only:

- `evaluation/private/frozen/factored-heldout-v1/development_cases.jsonl`
- `evaluation/private/frozen/factored-heldout-v1/development_answer_keys.jsonl`
- the read-only curated `bank.duckdb`

It verifies the canonical development combined SHA-256:

`eae78144906d70a9d2a64cf3b37b452738eee70e9552c64e13522b4744dcbaa7`

The runner refuses paths whose filename contains `heldout`.

The current development pool contains 100 cases:
- 75 Spanish;
- 25 Portuguese;
- no organizer-customer overlap with the held-out pool.

A separate public **16-case Portuguese stress set** is also run. It is entirely
team-generated and contains no organizer IDs or banking values. It covers informal
Brazilian phrasing, abbreviations/typos, non-recognition assertions, transaction lookup,
status, decline-cause, money movement, card blocking, disputes, profile changes, and
credit eligibility.

## What is measured

Each candidate receives the same R3C interpreter prompt/schema and the same development
steps.

The runner records only aggregate metrics:

- first-pass verified structured-output rate;
- provider failure rate plus aggregate transport/HTTP failure classes;
- invalid structured-output rate;
- scored intent accuracy;
- answer-key-backed route-proxy accuracy where the interpretation contract can derive the route;
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

The runner does **not** persist:
- prompts;
- customer IDs;
- transaction IDs;
- banking values;
- raw model outputs;
- answer-key contents.

Aggregate outputs are written under git-ignored
`evaluation/results/private/r3c_b/`.

## Safety architecture during the bake-off

Provider output remains untrusted.

Every call still passes through the R3C deterministic post-check:
- exact persisted session required;
- transaction IDs must appear in customer text;
- owned transaction references are checked against DuckDB;
- cross-customer references cannot become verified IDs;
- model search breadth remains server-controlled;
- invalid output safely falls back.

The bake-off therefore compares language interpretation quality without granting any
provider additional banking authority.

## Predeclared provider-selection rule

A candidate is **ineligible** for selection if any of the following occur:

1. `unsafe_cross_customer_bindings > 0`;
2. first-pass `verified_step_rate < 0.98`;
3. `unauthorized_positive_recall < 1.00`;
4. `explicit_transaction_id_accuracy < 0.95`;
5. `portuguese_core_accuracy < 0.85`;
6. `portuguese_stress_accuracy < 0.85`;
7. `bilingual_unauthorized_stress_recall < 1.00`.

Unauthorized detection is therefore a safety-recall gate, not an overall-accuracy gate.
A model that misses any mandatory unauthorized-positive development case is ineligible.
Specificity is reported separately.

Among eligible candidates:

1. rank by the language-balanced mean of Spanish and Portuguese core accuracy;
2. if candidates are within **1.0 percentage point**, prefer the lower combined
   provider-failure + invalid-structured-output rate;
3. if still tied within **0.5 percentage points**, prefer lower p95 latency;
4. cost is the final tie-breaker after quality/reliability/latency. All three current pricing snapshots are recorded in USD, so the benchmark may compare the measured aggregate USD estimates directly.

No result from the frozen held-out suite may be used to reverse the development-pool
provider choice. The frozen v1 suite is a template-controlled conformance/safety surface,
not broad novel-language generalization evidence.

The intended live comparison is **two providers**, not automatically all three. The exact
pair is frozen only after all candidates pass the public synthetic preflight and the
project considers schema/API viability, regional endpoint constraints, and data-processing
terms. A third live candidate is retained only if preflight evidence makes it worth the
remaining schedule cost.

If no candidate passes the eligibility gate, R3C-B does not select a provider. The
interpreter contract/prompt may be revised using development evidence and the bake-off
rerun, with the revision recorded before any held-out access.

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

Before any private development case is sent to a provider, run the provider's
**public synthetic-only preflight**:

`python -m evaluation.provider_bakeoff --candidate <candidate-id> --preflight-only`

The preflight:
- uses four team-generated ES/PT messages only;
- opens no private development or held-out files;
- opens no banking database;
- validates the current structured-output/API path;
- captures safe aggregate HTTP/provider-failure metadata;
- checks the served model identifier when the provider reports one.

This is especially important for Qwen because current Alibaba documentation is not fully
internally consistent about Singapore structured-output availability. A provider that
cannot pass preflight is not permitted to receive private development cases.

DeepSeek JSON mode follows the current official requirement to include JSON instructions
and an example of the desired format and to bound max output tokens.

## Commands

Run one candidate at a time:

`python -m evaluation.provider_bakeoff --candidate openai-gpt-6-luna`

`python -m evaluation.provider_bakeoff --candidate qwen3.7-flash`

`python -m evaluation.provider_bakeoff --candidate deepseek-v4.1-flash`

The runner uses one provider attempt per development step so first-pass schema/API
reliability remains observable. The production interpretation service retains its bounded
retry/fallback behavior.

## Data Excellence capture

The eventual R3C-B result should publish only a safe aggregate comparison table containing:

- exact candidate/model identifiers;
- frozen development SHA;
- ES/PT quality;
- schema/provider failure rates;
- latency;
- token/cost aggregates;
- predeclared eligibility result;
- selected provider or explicit no-selection result.

This becomes another **Evidence → decision → consequence** item:

> development-pool multilingual extraction evidence → provider choice → frozen runtime
> adapter/configuration before held-out evaluation.


## Pre-run refresh and v3 repair — 2026-09-26

Before any paid development-pool execution, official provider documentation was rechecked.
GPT-6 Luna replaces the earlier GPT-5.6 Luna candidate for the low-cost OpenAI slot and
the Qwen3.7-Flash Singapore international price units/rates were corrected.

The independent full-project Claude audit then found that v2 was not fit to execute:
DeepSeek did not receive the schema, unauthorized safety was gated on overall accuracy,
and several target labels could penalize correct answers. Those defects were repaired
**before any live provider or private development-pool execution**.

The current benchmark version is `r3c-provider-bakeoff-v3`; the interpretation contract
is `r3c-v2`. V3 also adds whole-token transaction-ID provenance, canonical
transaction-type/status enums, message-provenance checks for query filters, cross-language
unauthorized lexical backstop coverage, answer-key-backed route checks, synthetic
provider preflight, and richer safe aggregate provenance.
