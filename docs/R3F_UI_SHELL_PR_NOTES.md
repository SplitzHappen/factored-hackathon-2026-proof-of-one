# R3F UI shell PR notes

## PR intent

Create a narrow judge-facing UI shell over the existing local synthetic API so final demo materials can use product-shaped screenshots rather than Swagger/API screenshots.

## Review focus

Review should stay limited to:

- the served `/demo` and `/` local shell;
- the thin route hook in `app/main.py`;
- endpoint-reference and API-flow preservation tests;
- documentation of claim limits and next screenshot/video capture steps.

## Out of scope

The PR does not authorize or include:

- backend architecture changes;
- policy or retrieval changes;
- live-provider wiring;
- held-out evaluation;
- final submission;
- judge go-live;
- production or pilot readiness claims.
