# Policy Precedence, Decision Evidence, and Pre-LLM Freeze

**Status:** pre-LLM architecture freeze record for the Factored AI & Data Hackathon 2026 candidate.

This document explains the authority order behind the eight judge-facing checks, what the
Decision Evidence contract proves, how dependency failures differ from policy routes, and what is
frozen before live-provider/model selection.

## 1. Core authority rule

Proof of One separates language interpretation from system authority.

The interpretation layer may describe a bounded customer request. It cannot grant itself authority
over customer identity, banking truth, transaction ownership, policy, ticket persistence, or a
banking action.

The deterministic policy router remains authoritative after post-checked interpretation and trusted
retrieval facts are available.

In concise form:

> Interpretation proposes meaning. Deterministic controls decide authority. Operational evidence
> records what actually happened.

## 2. Why the eight checks are ordered

The signal-box checks are ordered by authority, not conversational convenience.

The effective precedence is:

1. **Customer-reported unauthorized activity**  
   An explicit customer report of non-recognition/unauthorized activity routes to human review.

2. **Possible unauthorized activity**  
   The server-side RF4 fail-safe floor may raise a conservative human-review signal when the
   stronger explicit report is absent.

3. **Interpreter unavailable**  
   Exhausted interpretation failure cannot be converted into an automated banking answer.

4. **Record conflict / excluded relationship / unsafe record**  
   Trusted-data or relationship constraints resolve before ordinary customer-service completion.

5. **Decline-cause request**  
   Unsupported causal explanation abstains rather than inventing why a payment was declined.

6. **Prohibited banking action**  
   Requests for mutations or other prohibited authority abstain. The system does not clarify an
   impermissible operation into something more actionable.

7. **Unsupported intent**  
   Requests outside the bounded account/payment inquiry surface abstain.

8. **Multiple verified matches / remaining clarification conditions**  
   Clarification is permitted only after all higher-priority safety and authority constraints clear.

If none fires, the bounded supported request may reach `ANSWER`.

This ordering prevents a lower-priority conversational condition from masking a higher-priority
safety or authority condition. For example, an ambiguous request that also contains a customer
report of unauthorized activity routes to `ESCALATE`; the system does not ask a clarifying
question that would delay the controlling human-review disposition.

## 3. Policy route is not execution status

The four policy routes remain:

- `ANSWER`
- `CLARIFY`
- `ABSTAIN`
- `ESCALATE`

They describe the permitted workflow disposition once the system has enough trusted state to make
that decision.

Execution status is a different axis. The application separately records whether the permitted
operational action completed.

Current successful-turn execution states include:

- `completed`
- `not_invoked`

Trusted-bank dependency failure is represented separately as:

- `dependency_unavailable`

A banking dependency outage is not a fifth policy route and is not silently reclassified as
`ESCALATE` or `ABSTAIN`. If trusted banking data becomes unavailable before a successful
customer-turn response can be completed, the API fails closed with HTTP 503, claims no route in the
failure payload, releases no banking fact, and reports:

- `action_completed=false`
- `banking_fact_released=false`

## 4. Decision Evidence / ACT -> VERIFY

Every successful customer turn now carries a strict server-generated `DecisionEvidence` envelope.

It records only observable operational facts:

- language;
- interpretation status;
- transaction-reference status;
- controlling check;
- controlling reason;
- operational action;
- execution status;
- verification codes.

It is **not model chain-of-thought** and it does not expose private model reasoning.

Representative evidence:

### ANSWER

- action: `read_verified_bank_records`
- execution: `completed`
- verification: `customer_scope_enforced`, `records_verified`

### CLARIFY

- action: `none`
- execution: `not_invoked`
- verification may include `ambiguity_preserved` and/or `reference_withheld`

### ABSTAIN

- action: `none`
- execution: `not_invoked`
- verification includes `no_banking_action`

### ESCALATE

- action: `create_escalation_ticket`
- execution: `completed`
- verification includes `escalation_persisted` and
  `escalation_readback_verified`

The judge-facing Decision Evidence panel renders this envelope as a compact operational flight
recorder. It should not be described as a durable audit-event ledger: ordinary turn evidence is
returned to the client but is not currently persisted as a separate immutable per-turn audit log.

## 5. ACT -> VERIFY meaning

The phrase **ACT -> VERIFY** means that the application does not infer success from intent or
policy alone.

Where an operational action exists, success depends on an observable post-condition.

The clearest example is escalation:

1. policy permits/requires human review;
2. the application creates the escalation ticket;
3. persisted identity and reason data are re-read;
4. verification state is persisted;
5. the record is read back again;
6. only then may the API report verified escalation evidence.

For no-action routes, verification records the safety post-condition instead—for example,
`no_banking_action` or `ambiguity_preserved`.

## 6. Pre-LLM architecture freeze

As of this freeze record, the following architecture is treated as fixed unless testing exposes a
concrete defect:

- server-issued session identity and tenant boundary;
- read-only trusted banking repository;
- separate writable operational store;
- provider-facing data-minimization contract;
- deterministic interpretation post-checks;
- unauthorized-activity deterministic backstops;
- eight-check policy precedence;
- four-route policy surface;
- Decision Evidence contract;
- escalation persistence/read-back verification;
- bank-dependency fail-closed contract;
- public synthetic signal-box demo.

The next engineering phase may add a live provider adapter **behind the existing interpretation
boundary**. It may not broaden model authority.

## 7. Live-provider development discipline

Provider/model/prompt work must use development material only.

Sequence:

1. implement provider adapter(s) behind `StructuredInterpretationProvider`;
2. evaluate candidates on the development pool and permitted language-stress surfaces;
3. select provider/model;
4. select prompt/configuration;
5. freeze provider/model/prompt;
6. run integration/regression tests;
7. only then execute the frozen held-out suite.

The frozen held-out material must not be used iteratively while tuning the provider or prompt.

## 8. Claims boundary

This freeze supports claims about:

- deterministic authority separation;
- bounded operational evidence;
- customer-scope enforcement;
- safe non-action on clarification/abstention;
- verified escalation persistence;
- fail-closed trusted-bank dependency behavior;
- synthetic bilingual demo behavior.

It does **not** establish:

- production or pilot readiness;
- live-bank integration;
- fraud detection;
- live-LLM quality;
- held-out uplift;
- general Spanish/Portuguese language robustness;
- final submission readiness.

Those claims require their own evidence gates.
