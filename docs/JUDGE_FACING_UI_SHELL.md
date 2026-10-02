# Judge-facing local UI shell

This document is the public, consolidated reference for the R3F judge-facing local UI shell.

The shell is a thin browser interface over the existing local synthetic FastAPI demo API. It is intended to support screenshot and short-video capture for the final demo package without requiring judges to interpret Swagger screens as the main product surface.

## What the shell does

- Serves a dependency-free HTML/CSS/JavaScript interface at `/demo` and `/`.
- Uses only existing local synthetic API endpoints:
  - `GET /ready`
  - `GET /api/demo/personas`
  - `POST /api/demo/sessions`
  - `POST /api/customer/turn`
  - `POST /api/customer/handoff`
  - `DELETE /api/demo/session`
- Presents four bounded judge flows:
  - `ANSWER` over verified synthetic transaction records;
  - `CLARIFY` when two synthetic transactions match the same customer request;
  - `ESCALATE` when the customer reports unauthorized activity;
  - support handoff through a stored ticket response.
- Shows the runtime boundary from `/ready`, including synthetic data mode and `llm_connected=false`.

## What the shell does not do

- It does not change backend policy logic.
- It does not change retrieval logic.
- It does not change session authority or customer identity controls.
- It does not change escalation persistence.
- It does not add live-provider wiring.
- It does not run held-out evaluation.
- It does not imply production, pilot, final submission, or judge go-live readiness.

## Claim limits

Permitted claims:

- The local UI shell demonstrates the existing synthetic API through a judge-facing browser surface.
- The browser does not choose or submit the authoritative customer identity; sessions are server-issued.
- Demo data is synthetic and fictional.
- The UI displays backend route decisions rather than inventing route labels.
- The demonstrated flows include supported answers, ambiguous-transaction clarification, customer-reported unauthorized-activity escalation, and explicit support handoff.
- Escalation and handoff create stored support-ticket records for follow-up.

Prohibited claims:

- Production readiness.
- Pilot readiness.
- Live language-model integration.
- Comprehensive Spanish/Portuguese natural-language coverage.
- Fraud detection.
- Human-agent staffing or live human review.
- Final public submission or judge go-live approval.
- Any baseline-vs-LLM uplift claim.

## Preset capture sequence

Use a local run of the product app:

```powershell
python -m pytest tests/test_demo_ui_shell.py -q
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

Capture sequence:

1. **Overview** — hero, claim-limit cards, and runtime boundary showing `ready`, synthetic mode, and `llm_connected=false`.
2. **ANSWER / Lucía** — `Muéstrame mis últimos movimientos.` returning `ANSWER` and transaction cards.
3. **CLARIFY / Lucía** — `Busca las transacciones de 54.000 COP.` returning `CLARIFY` with candidates `DEMO-ES-1003` and `DEMO-ES-1004`.
4. **ESCALATE / Lucía** — unauthorized-activity report returning `ESCALATE` and a support-ticket ID.
5. **HANDOFF / Lucía** — explicit support handoff showing the returned ticket plus API `persisted` and `verified` fields.
6. **Portuguese / Rafael** — select Rafael, click **Start new demo session**, then send `Quero ver meus pagamentos recentes.` to return a Portuguese answer over Rafael's synthetic records.

For main deck screenshots, crop or avoid overemphasizing session and tenant identifiers. Keep those details for appendix evidence only.

## Appendix-only evidence

Keep the following as technical backup rather than main judge-facing visuals:

- Swagger `/docs` screenshots.
- Raw JSON for `/ready`, session creation, customer turns, and handoff responses.
- Session/tenant IDs.
- Reason-code lists.
- OpenAPI-hidden route test evidence.
- Local test results.
- The identity-control explanation that the client never supplies `customer_id`.

## Review status

This shell remains a local synthetic demo surface until separately approved for any final deck/script/audit use. It should be locally validated and recaptured before the demo deck is refreshed.
