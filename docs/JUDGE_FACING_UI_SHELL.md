# Judge-facing UI shell

This document records the narrow demo UI shell added for the Factored hackathon judge-facing walkthrough.

## Purpose

The shell gives reviewers a product-shaped surface over the existing local FastAPI demo API. It is intended to replace Swagger-heavy screenshots in the judge deck while preserving the same backend claim limits.

## Local use

Start the existing service normally:

```powershell
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

The root path also serves the same shell for local convenience:

```text
http://127.0.0.1:8000/
```

## API surface used

The UI calls only the already-existing local demo endpoints:

- `GET /ready`
- `GET /api/demo/personas`
- `POST /api/demo/sessions`
- `POST /api/customer/turn`
- `POST /api/customer/handoff`
- `DELETE /api/demo/session`

The browser receives the server-issued `session_id` and sends it back only through the `X-Demo-Session` header. The UI does not ask for, store, or submit a `customer_id`.

## Judge-visible flows

The shell includes preset messages for the current deck/script flow:

1. `ANSWER` — supported recent-transaction request over verified synthetic records.
2. `CLARIFY` — ambiguous transaction reference requiring customer clarification.
3. `ESCALATE` — customer-reported unauthorized activity routed to human review.
4. Explicit support handoff — direct customer support request producing persisted ticket evidence.

## Claim limits

This UI shell demonstrates the existing local synthetic API flow only. It does not claim:

- live-provider/model readiness;
- production or pilot readiness;
- held-out evaluation completion;
- final judge submission approval;
- fraud detection authority;
- customer identity control by the browser or model;
- any change to the backend policy, retrieval, session, or escalation authority.

Swagger/API screenshots may still be used as technical appendix evidence, but the judge-facing visual flow should use this shell after local screenshot or short-video recapture.

## Next audit step

After screenshot or video capture, refresh the deck captions and speaker script around the actual UI-backed flow, then run the final demo-claims audit before external use.
