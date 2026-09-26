# Proof of One — Factored AI & Data Hackathon 2026

Proof of One is a bounded account/payment customer-support prototype for the Factored AI & Data Hackathon 2026.

## Current implementation stage

R3B deterministic foundation.

The application currently contains:
- a FastAPI service shell;
- strict Pydantic boundary contracts;
- Docker packaging;
- a read-only banking-data path reserved for curated DuckDB;
- a separate writable path reserved for SQLite operational state;
- initial tests proving that transaction query contracts do not accept a model-controlled `customer_id`.

No LLM is connected yet.

## Safety architecture

The selected design intentionally separates:

1. **Authoritative banking data** — curated into `bank.duckdb` and opened read-only.
2. **Application-generated operational state** — persisted separately in `runtime.sqlite`.
3. **Deterministic policy and authorization** — implemented in Python outside model discretion.
4. **AI interpretation** — added only after deterministic identity, retrieval, routing, persistence, and evaluation controls pass tests.

The model will never receive arbitrary SQL access and will never control the authenticated customer identity.

## Local setup

Python 3.14 is the development baseline.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --reload
```

The health endpoint is available at:

```text
http://127.0.0.1:8000/health
```

## Docker

```powershell
docker compose up --build
```

The service is exposed on port 8000.

## Curated data build

The application does not query the complete organizer dataset directly. The deterministic R3B builder creates the minimized trusted `bank.duckdb` used by the service:

```powershell
python scripts/build_curated_bank.py `
  --data-root "$HOME\Documents\Factored-Hackathon-2026\data" `
  --output "data\curated\bank.duckdb" `
  --manifest "data\curated\build_manifest.json" `
  --overwrite
```

The builder is fail-closed on primary-key, foreign-key, and transaction/product/customer ownership violations and refuses to write any generated artifact into the raw organizer-data root. See `docs/CURATED_DATA.md` for the exact retained/excluded fields and reproducibility contract.

## Data policy

Raw organizer data is not committed to this public repository.

The raw dataset remains local and read-only. A later reproducible build step will create the minimal curated DuckDB artifact required by the application. Generated database files and runtime state are git-ignored.

## Submission status

This repository is the canonical public implementation/submission surface for the Proof of One entry. Architecture, evaluation evidence, deployment documentation, limitations, and final submission artifacts will accumulate here as implementation proceeds.
