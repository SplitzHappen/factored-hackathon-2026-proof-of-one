from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, time
from pathlib import Path
from typing import Iterator

import duckdb

from app.behavioral_evidence import BehavioralEvidenceInput
from app.schemas import CustomerSummary, ProductRecord, TransactionQuery, TransactionRecord


EXPECTED_CURATED_SCHEMA_VERSION = 1


class IncompatibleBankDatabaseError(RuntimeError):
    """Raised when the curated store does not match the runtime contract."""


class BankRepository:
    """Bounded, read-only access to the curated banking store.

    Authenticated customer identity is supplied by trusted server context to each
    method. Query objects never contain customer identity.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Curated banking database does not exist: {self.database_path}"
            )
        self._validate_schema_version()

    @contextmanager
    def _connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        con = duckdb.connect(
            str(self.database_path),
            read_only=True,
            config={"enable_external_access": "false"},
        )
        try:
            yield con
        finally:
            con.close()

    def _validate_schema_version(self) -> None:
        try:
            with self._connect() as con:
                row = con.execute(
                    """
                    SELECT schema_version
                    FROM build_metadata
                    LIMIT 1
                    """
                ).fetchone()
        except duckdb.Error as exc:
            raise IncompatibleBankDatabaseError(
                "Curated banking database is missing compatible build metadata."
            ) from exc

        if row is None or int(row[0]) != EXPECTED_CURATED_SCHEMA_VERSION:
            found = None if row is None else row[0]
            raise IncompatibleBankDatabaseError(
                "Unsupported curated schema version: "
                f"{found!r}; expected {EXPECTED_CURATED_SCHEMA_VERSION}."
            )

    def get_customer_summary(
        self,
        authenticated_customer_id: str,
    ) -> CustomerSummary | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT customer_status
                FROM customers
                WHERE customer_id = ?
                LIMIT 1
                """,
                [authenticated_customer_id],
            ).fetchone()

        if row is None:
            return None
        return CustomerSummary(customer_status=row[0])

    def list_customer_products(
        self,
        authenticated_customer_id: str,
    ) -> list[ProductRecord]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT
                    product_id,
                    product_type,
                    currency,
                    current_balance,
                    opening_date,
                    expiration_date,
                    product_status,
                    last_transaction_date
                FROM products
                WHERE customer_id = ?
                ORDER BY opening_date DESC, product_id
                """,
                [authenticated_customer_id],
            ).fetchall()

        return [
            ProductRecord(
                product_id=row[0],
                product_type=row[1],
                currency=row[2],
                current_balance=row[3],
                opening_date=row[4],
                expiration_date=row[5],
                product_status=row[6],
                last_transaction_date=row[7],
            )
            for row in rows
        ]

    def list_recent_transactions(
        self,
        authenticated_customer_id: str,
        *,
        limit: int = 10,
    ) -> list[TransactionRecord]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")

        with self._connect() as con:
            rows = con.execute(
                """
                SELECT
                    t.transaction_id,
                    t.product_id,
                    t.transaction_date,
                    t.amount,
                    t.currency,
                    t.transaction_type,
                    t.transaction_category,
                    t.channel,
                    t.merchant_name,
                    t.merchant_category,
                    t.transaction_country,
                    t.transaction_city,
                    t.transaction_status
                FROM transactions t
                JOIN products p
                  ON p.product_id = t.product_id
                 AND p.customer_id = ?
                WHERE t.customer_id = ?
                ORDER BY t.transaction_date DESC, t.transaction_id DESC
                LIMIT ?
                """,
                [authenticated_customer_id, authenticated_customer_id, limit],
            ).fetchall()

        return [self._transaction_from_row(row) for row in rows]

    def find_transactions(
        self,
        authenticated_customer_id: str,
        query: TransactionQuery,
    ) -> list[TransactionRecord]:
        clauses = [
            "p.customer_id = ?",
            "t.customer_id = ?",
        ]
        params: list[object] = [
            authenticated_customer_id,
            authenticated_customer_id,
        ]

        if query.date_from is not None:
            clauses.append("t.transaction_date >= ?")
            params.append(datetime.combine(query.date_from, time.min))

        if query.date_to is not None:
            clauses.append("t.transaction_date <= ?")
            params.append(datetime.combine(query.date_to, time.max))

        if query.amount is not None:
            clauses.append("t.amount = ?")
            params.append(query.amount)

        if query.transaction_type is not None:
            clauses.append("LOWER(t.transaction_type) = LOWER(?)")
            params.append(query.transaction_type)

        if query.status is not None:
            clauses.append("LOWER(t.transaction_status) = LOWER(?)")
            params.append(query.status)

        params.append(query.limit)

        sql = f"""
            SELECT
                t.transaction_id,
                t.product_id,
                t.transaction_date,
                t.amount,
                t.currency,
                t.transaction_type,
                t.transaction_category,
                t.channel,
                t.merchant_name,
                t.merchant_category,
                t.transaction_country,
                t.transaction_city,
                t.transaction_status
            FROM transactions t
            JOIN products p
              ON p.product_id = t.product_id
            WHERE {' AND '.join(clauses)}
            ORDER BY t.transaction_date DESC, t.transaction_id DESC
            LIMIT ?
        """

        with self._connect() as con:
            rows = con.execute(sql, params).fetchall()

        return [self._transaction_from_row(row) for row in rows]

    def get_transaction(
        self,
        authenticated_customer_id: str,
        transaction_id: str,
    ) -> TransactionRecord | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT
                    t.transaction_id,
                    t.product_id,
                    t.transaction_date,
                    t.amount,
                    t.currency,
                    t.transaction_type,
                    t.transaction_category,
                    t.channel,
                    t.merchant_name,
                    t.merchant_category,
                    t.transaction_country,
                    t.transaction_city,
                    t.transaction_status
                FROM transactions t
                JOIN products p
                  ON p.product_id = t.product_id
                 AND p.customer_id = ?
                WHERE t.transaction_id = ?
                  AND t.customer_id = ?
                LIMIT 1
                """,
                [
                    authenticated_customer_id,
                    transaction_id,
                    authenticated_customer_id,
                ],
            ).fetchone()

        if row is None:
            return None
        return self._transaction_from_row(row)

    def get_behavioral_evidence_input(
        self,
        authenticated_customer_id: str,
        transaction_id: str,
    ) -> BehavioralEvidenceInput | None:
        """Build target-free evidence facts for one ownership-verified transaction.

        History is restricted to the same customer and timestamps strictly earlier
        than the target transaction. Same-timestamp peers and future records never
        contribute. Retrospective fraud labels/reference scores are never selected.
        """

        with self._connect() as con:
            row = con.execute(
                """
                WITH target AS (
                    SELECT
                        t.transaction_date,
                        CAST(t.amount AS DOUBLE) AS amount,
                        t.currency,
                        t.channel,
                        t.merchant_category,
                        t.transaction_country,
                        p.opening_date,
                        t.customer_id
                    FROM transactions t
                    JOIN products p
                      ON p.product_id = t.product_id
                     AND p.customer_id = ?
                    WHERE t.transaction_id = ?
                      AND t.customer_id = ?
                    LIMIT 1
                ),
                history AS (
                    SELECT
                        h.transaction_id,
                        h.transaction_date,
                        CAST(h.amount AS DOUBLE) AS amount,
                        h.currency,
                        h.channel,
                        h.merchant_category,
                        h.transaction_country
                    FROM transactions h
                    JOIN products hp
                      ON hp.product_id = h.product_id
                    JOIN target t
                      ON h.customer_id = t.customer_id
                     AND hp.customer_id = t.customer_id
                    WHERE h.transaction_date < t.transaction_date
                )
                SELECT
                    t.transaction_date,
                    t.amount,
                    t.currency,
                    t.channel,
                    t.merchant_category,
                    t.transaction_country,
                    t.opening_date,
                    COUNT(h.transaction_id) AS prior_tx_count_lifetime,
                    AVG(h.amount) FILTER (
                        WHERE h.currency = t.currency
                    ) AS prior_same_currency_mean,
                    COUNT(h.transaction_id) FILTER (
                        WHERE h.channel = t.channel
                    ) AS prior_same_channel_count,
                    COUNT(h.transaction_id) FILTER (
                        WHERE t.merchant_category IS NOT NULL
                          AND h.merchant_category = t.merchant_category
                    ) AS prior_same_merchant_category_count,
                    COUNT(h.transaction_id) FILTER (
                        WHERE h.transaction_country = t.transaction_country
                    ) AS prior_same_country_count,
                    COUNT(h.transaction_id) FILTER (
                        WHERE h.transaction_date
                              >= t.transaction_date - INTERVAL '24 hours'
                    ) AS prior_24h_tx_count,
                    COUNT(h.transaction_id) FILTER (
                        WHERE h.transaction_date
                              >= t.transaction_date - INTERVAL '30 days'
                    ) AS prior_30d_tx_count
                FROM target t
                LEFT JOIN history h ON TRUE
                GROUP BY
                    t.transaction_date,
                    t.amount,
                    t.currency,
                    t.channel,
                    t.merchant_category,
                    t.transaction_country,
                    t.opening_date
                """,
                [
                    authenticated_customer_id,
                    transaction_id,
                    authenticated_customer_id,
                ],
            ).fetchone()

        if row is None:
            return None

        occurred_at = row[0]
        opening_date = row[6]
        product_tenure_days = float(
            max((occurred_at.date() - opening_date).days, 0)
        )

        current_amount = float(row[1])
        prior_same_currency_mean = (
            None if row[8] is None else float(row[8])
        )
        has_positive_amount_baseline = (
            current_amount > 0.0
            and prior_same_currency_mean is not None
            and prior_same_currency_mean > 0.0
        )
        amount_ratio = (
            current_amount / prior_same_currency_mean
            if has_positive_amount_baseline
            else None
        )

        prior_lifetime = int(row[7])
        merchant_category_present = row[4] is not None

        return BehavioralEvidenceInput(
            prior_tx_count_lifetime=prior_lifetime,
            product_tenure_days=product_tenure_days,
            has_prior_currency_amount_history=has_positive_amount_baseline,
            amount_to_prior_currency_mean_ratio=amount_ratio,
            channel_novelty=int(row[9]) == 0,
            merchant_category_present=merchant_category_present,
            merchant_category_novelty=(
                merchant_category_present and int(row[10]) == 0
            ),
            transaction_country_novelty=int(row[11]) == 0,
            prior_24h_tx_count=int(row[12]),
            prior_30d_tx_count=int(row[13]),
        )

    @staticmethod
    def _transaction_from_row(row: tuple[object, ...]) -> TransactionRecord:
        return TransactionRecord(
            transaction_id=row[0],
            product_id=row[1],
            occurred_at=row[2],
            amount=row[3],
            currency=row[4],
            transaction_type=row[5],
            transaction_category=row[6],
            channel=row[7],
            merchant_name=row[8],
            merchant_category=row[9],
            transaction_country=row[10],
            transaction_city=row[11],
            status=row[12],
        )
