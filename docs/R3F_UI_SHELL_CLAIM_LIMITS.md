# R3F UI shell claim limits

## Status

R3F adds a narrow judge-facing UI shell over the existing local FastAPI synthetic demo API.

## What changed

- Added a dependency-free HTML/CSS/JavaScript shell served by the FastAPI app.
- Exposed the shell at `/demo` and `/` with `include_in_schema=False`.
- Kept the OpenAPI/Swagger surface available for technical evidence while moving the judge-facing walkthrough to the product-shaped UI surface.
- Added tests that verify the UI shell loads, references only the existing public demo API paths, remains hidden from OpenAPI, and preserves the existing customer-turn flow.

## What did not change

- No backend policy logic changed.
- No retrieval logic changed.
- No session authority changed.
- No escalation persistence logic changed.
- No model provider was selected or wired.
- No held-out evaluation was run.
- No production, pilot, or final submission readiness is claimed.

## Permitted demo claim

The UI may be described as:

> A judge-facing local demo shell over the existing synthetic Proof of One API, showing server-issued sessions, deterministic route decisions, verified synthetic records, clarification handling, unauthorized-activity escalation, and explicit support handoff.

## Prohibited demo claims

The UI must not be described as:

- production-ready;
- pilot-ready;
- live-provider-ready;
- a deployed banking system;
- a fraud-detection model;
- an independent evaluation result;
- evidence of baseline-vs-LLM uplift;
- final submission approval.

## Next step

Run the application locally, capture the judge-facing UI screenshots or short demo video, and update the deck/script/audit packet around the actual UI-backed flow.
