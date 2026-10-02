# R3F UI shell implementation summary

## Branch

`chatgpt/ui-shell-local-api-2026-10-02`

## Base

`main` at `849acc185594af7a47b805402848a9539ae6c6ab`.

## Implementation summary

The branch adds a narrow judge-facing UI shell over the existing local synthetic API.

Changed surface:

- `app/demo_ui.py` — dependency-free HTML/CSS/JavaScript shell.
- `app/main.py` — serves the shell at `/demo` and `/`, hidden from OpenAPI.
- `tests/test_demo_ui_shell.py` — focused route, OpenAPI, endpoint-reference, and API-flow regression tests.
- `docs/JUDGE_FACING_UI_SHELL.md` — local usage and boundary documentation.
- `docs/R3F_UI_SHELL_CLAIM_LIMITS.md` — permitted/prohibited demo claims.

## Validation status

Static connector-side inspection confirmed the branch is ahead of `main` and limited to the UI shell, route hook, docs, and focused tests. No hosted CI, workflow/job/status inspection, live-provider call, held-out evaluation, or external submission was performed in this implementation pass.

## Boundaries preserved

- No backend policy logic changed.
- No retrieval logic changed.
- No runtime/session authority changed.
- No escalation persistence logic changed.
- No live-provider/model wiring was added.
- No production, pilot, held-out evaluation, or judge-go-live claim is made.

## Next step

Run the app locally and execute:

```powershell
python -m pytest tests/test_demo_ui_shell.py -q
uvicorn app.main:app --reload
```

Then capture judge-facing screenshots or a short local demo video at:

```text
http://127.0.0.1:8000/demo
```
