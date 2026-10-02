# R3F UI shell local capture guide

## Run

```powershell
uvicorn app.main:app --reload
```

## Open

```text
http://127.0.0.1:8000/demo
```

## Capture sequence

1. Runtime boundary panel showing `ready`, `synthetic`, and `llm_connected=false`.
2. Persona/session creation showing server-issued session and tenant.
3. ANSWER preset response with verified synthetic transaction cards.
4. CLARIFY preset response with candidate transaction identifiers.
5. ESCALATE preset response with escalation ticket evidence.
6. Explicit support handoff response with persisted/verified ticket evidence.

## Caption discipline

Each screenshot should state only what the UI/API directly supports. Keep the strongest claim to: local synthetic API flow, deterministic routing, server-issued sessions, and verified support handoff persistence where shown.
