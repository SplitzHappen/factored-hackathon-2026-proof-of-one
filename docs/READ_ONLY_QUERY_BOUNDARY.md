# Read-only banking query boundary

The application never exposes arbitrary SQL to the model or user.

Operational banking access is limited to predefined repository methods:

- authenticated customer status;
- authenticated customer's products;
- authenticated customer's recent transactions;
- bounded transaction search by date, amount, type, and recorded status;
- single-transaction retrieval after ownership verification.

Every product/transaction operation receives the authenticated customer ID from trusted server context. The public transaction-search contract deliberately has no `customer_id` field.

Transaction reads verify both:

1. the transaction's `customer_id`; and
2. ownership of its linked product by the same authenticated customer.

All user/model-controlled search values are passed as query parameters. SQL structure is fixed by application code.

The operational repository opens `bank.duckdb` in read-only mode and disables DuckDB external access. It also rejects curated databases whose schema version does not match the runtime contract.

Country and accent remain present in the curated artifact only for later aggregate subgroup evaluation. They are not returned by the operational customer-summary function and must not be used for authorization, risk decisions, routing, eligibility, or currency inference.


## Runtime fraud-label boundary

The curated local database may retain retrospective `is_fraud` and organizer `fraud_score` fields for offline ML/evaluation work. Operational repository methods do not select or return either field.

The runtime `TransactionRecord` therefore contains no retrospective fraud label or reference score. Those fields cannot enter customer responses, LLM context, or deterministic policy inputs through the banking repository.
