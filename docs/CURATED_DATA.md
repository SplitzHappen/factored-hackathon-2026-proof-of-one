# Curated banking data boundary

Proof of One does **not** run directly against the complete organizer dataset.

The R3B build step reads the organizer files without modifying them and creates a smaller `bank.duckdb` containing only the trusted relational core required by the approved Account / payment inquiries workflow.

## Included tables and fields

### customers

- `customer_id`
- `country`
- `detected_accent` — retained only for later diagnostic subgroup evaluation
- `customer_status`

### products

- `product_id`
- `customer_id`
- `product_type`
- `currency`
- `current_balance`
- `opening_date`
- `expiration_date`
- `product_status`
- `last_transaction_date`

### transactions

- `transaction_id`
- `transaction_date`
- `product_id`
- `customer_id`
- `transaction_type`
- `transaction_category`
- `amount`
- `currency`
- `channel`
- `merchant_name`
- `merchant_category`
- `transaction_country`
- `transaction_city`
- `transaction_status`
- `is_fraud`
- `fraud_score`

`is_fraud` and `fraud_score` remain in the local curated artifact only for offline analytical/evaluation work. They are deliberately excluded from the operational `TransactionRecord`, customer-facing query results, LLM context, and deterministic policy inputs.

## Deliberately excluded

The curated artifact does not include customer names, document numbers, email addresses, phone numbers, street addresses, product/account/card numbers, latitude/longitude, branch joins, free-text transcripts, complaints, digital-event product context, or other fields that are unnecessary for the selected workflow.

It also excludes relationships the R0 audit found unsafe for customer-specific grounding, including customer registration branch, service-agent assigned branch, complaint affected-product ownership, complaint origin-interaction linkage, digital-event product ownership, and interaction `mentioned_products`.

## Deterministic integrity gate

A build fails rather than producing an artifact if any of the following are detected:

- missing required fields;
- duplicate primary IDs;
- product-to-customer orphan records;
- transaction-to-customer orphan records;
- transaction-to-product orphan records;
- transaction/product customer-ownership mismatches.

The output database therefore preserves the audited transaction → product → customer ownership chain.

## Reproducibility

Each successful build creates a local `build_manifest.json` with:

- builder and schema versions;
- source file counts and byte totals;
- per-table source inventory fingerprints;
- curated column lists;
- row counts;
- integrity-check results;
- output database size;
- SHA-256 checksum of the generated DuckDB artifact;
- build duration.

Generated database and manifest artifacts stay outside Git history.

## Local build

From the repository root:

```powershell
python scripts/build_curated_bank.py `
  --data-root "$HOME\Documents\Factored-Hackathon-2026\data" `
  --output "data\curated\bank.duckdb" `
  --manifest "data\curated\build_manifest.json" `
  --overwrite
```

The organizer source folder is read only by the builder. The script refuses to place its output inside that source folder.
