from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, time
from pathlib import Path
from typing import Iterator

import duckdb

from app.behavioral_evidence import BehavioralEvidenceInput
from app.schemas import (
    ChallengeCustomerSummary,
    ChallengeMessageSummary,
    CustomerSummary,
    ProductRecord,
    SupportedLanguage,
    TransactionQuery,
    TransactionRecord,
)


EXPECTED_CURATED_SCHEMA_VERSION = 1

FULL_CHALLENGE_TABLES: dict[str, str] = {
    "customers": "challenge_customers",
    "products": "challenge_products",
    "transactions": "challenge_transactions",
    "call_center_interactions": "call_center_interactions",
    "call_transcripts": "call_transcripts",
    "campaign_sends": "campaign_sends",
    "complaints": "complaints",
    "digital_events": "digital_events",
    "satisfaction_surveys": "satisfaction_surveys",
    "branches": "branches",
    "daily_exchange_rates": "daily_exchange_rates",
    "marketing_campaigns": "marketing_campaigns",
    "service_agents": "service_agents",
}


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

    def check_ready(self) -> None:
        """Revalidate the live read-only banking schema used by request paths."""

        self._validate_schema_version()
        required_tables = {"build_metadata", "customers", "products", "transactions"}
        try:
            with self._connect() as con:
                rows = con.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'main'
                    """
                ).fetchall()
        except duckdb.Error as exc:
            raise IncompatibleBankDatabaseError(
                "Banking database could not be read for readiness."
            ) from exc
        tables = {str(row[0]) for row in rows}
        missing = required_tables - tables
        if missing:
            raise IncompatibleBankDatabaseError(
                "Banking database is missing required tables: "
                + ", ".join(sorted(missing))
            )

    def has_full_challenge_data(self) -> bool:
        """Return whether the full challenge source layer is present."""

        with self._connect() as con:
            rows = con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                """
            ).fetchall()
        available = {str(row[0]) for row in rows}
        return set(FULL_CHALLENGE_TABLES.values()).issubset(available)

    def challenge_table_counts(self) -> dict[str, int]:
        """Return non-sensitive row counts for the full challenge source layer."""

        if not self.has_full_challenge_data():
            raise IncompatibleBankDatabaseError(
                "Full challenge data tables are not available in this artifact."
            )

        counts: dict[str, int] = {}
        with self._connect() as con:
            for source_name, table_name in FULL_CHALLENGE_TABLES.items():
                row = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                assert row is not None
                counts[source_name] = int(row[0])
        return counts

    @staticmethod
    def _challenge_language(
        country: str | None,
        detected_language: str | None,
    ) -> SupportedLanguage:
        label = (detected_language or "").strip().casefold()
        if label.startswith("pt") or "portugu" in label:
            return SupportedLanguage.PT
        if label.startswith("es") or "span" in label or "espa" in label:
            return SupportedLanguage.ES
        if (country or "").strip().casefold() in {"brazil", "brasil"}:
            return SupportedLanguage.PT
        return SupportedLanguage.ES

    def get_challenge_customer(
        self,
        customer_id: str,
    ) -> ChallengeCustomerSummary | None:
        """Resolve one challenge customer without exposing direct identifiers/PII."""

        if not self.has_full_challenge_data():
            raise IncompatibleBankDatabaseError(
                "Full challenge data tables are not available in this artifact."
            )

        with self._connect() as con:
            row = con.execute(
                """
                SELECT
                    c.customer_id,
                    c.country,
                    c.detected_accent,
                    c.customer_status,
                    (
                        SELECT ct.detected_language
                        FROM call_transcripts ct
                        WHERE ct.customer_id = c.customer_id
                          AND NULLIF(TRIM(ct.detected_language), '') IS NOT NULL
                        ORDER BY ct.process_date DESC, ct.transcript_id DESC
                        LIMIT 1
                    ) AS detected_language,
                    (
                        SELECT COUNT(*)
                        FROM call_transcripts ct
                        WHERE ct.customer_id = c.customer_id
                          AND NULLIF(TRIM(ct.customer_text), '') IS NOT NULL
                    ) AS transcript_count
                FROM customers c
                WHERE c.customer_id = ?
                LIMIT 1
                """,
                [customer_id],
            ).fetchone()

        if row is None:
            return None
        return ChallengeCustomerSummary(
            customer_id=str(row[0]),
            country=None if row[1] is None else str(row[1]),
            detected_accent=None if row[2] is None else str(row[2]),
            customer_status=None if row[3] is None else str(row[3]),
            default_language=self._challenge_language(
                None if row[1] is None else str(row[1]),
                None if row[4] is None else str(row[4]),
            ),
            transcript_count=int(row[5]),
        )

    def search_challenge_customers(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[ChallengeCustomerSummary]:
        """Search challenge customers by a strict non-sensitive whitelist.

        Blank and overly broad queries intentionally return no customers. The
        whitelisted fields are customer_id, country, detected accent,
        customer_status, latest transcript language, and derived ES/PT locale.
        Names, contact details, documents, account values, transaction values,
        and raw customer messages are never searched here.
        """

        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        if not self.has_full_challenge_data():
            raise IncompatibleBankDatabaseError(
                "Full challenge data tables are not available in this artifact."
            )

        normalized = " ".join(query.strip().split())
        if not normalized:
            return []

        tokens = normalized.split()
        # A lone two-character language/status fragment such as "es" or "pt"
        # would enumerate too many customers. Allow short tokens only when they
        # are paired with at least one specific token such as a customer prefix
        # or country/status term.
        if not any(len(token) >= 3 for token in tokens):
            return []

        clauses: list[str] = []
        params: list[object] = []
        for token in tokens:
            if len(token) < 3 and len(tokens) == 1:
                return []
            like = f"%{token}%"
            clauses.append(
                "(" 
                "LOWER(customer_id) LIKE LOWER(?) OR "
                "LOWER(COALESCE(country, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(detected_accent, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(customer_status, '')) LIKE LOWER(?) OR "
                "LOWER(COALESCE(detected_language, '')) LIKE LOWER(?) OR "
                "default_language = LOWER(?)"
                ")"
            )
            params.extend([like, like, like, like, like, token])
        params.append(limit)

        with self._connect() as con:
            rows = con.execute(
                f"""
                WITH customer_candidates AS (
                    SELECT
                        c.customer_id,
                        c.country,
                        c.detected_accent,
                        c.customer_status,
                        (
                            SELECT ct.detected_language
                            FROM call_transcripts ct
                            WHERE ct.customer_id = c.customer_id
                              AND NULLIF(TRIM(ct.detected_language), '') IS NOT NULL
                            ORDER BY ct.process_date DESC, ct.transcript_id DESC
                            LIMIT 1
                        ) AS detected_language,
                        (
                            SELECT COUNT(*)
                            FROM call_transcripts ct
                            WHERE ct.customer_id = c.customer_id
                              AND NULLIF(TRIM(ct.customer_text), '') IS NOT NULL
                        ) AS transcript_count,
                        CASE
                            WHEN LOWER(COALESCE(
                                (
                                    SELECT ct.detected_language
                                    FROM call_transcripts ct
                                    WHERE ct.customer_id = c.customer_id
                                      AND NULLIF(TRIM(ct.detected_language), '') IS NOT NULL
                                    ORDER BY ct.process_date DESC, ct.transcript_id DESC
                                    LIMIT 1
                                ), ''
                            )) LIKE 'pt%'
                              OR LOWER(COALESCE(
                                (
                                    SELECT ct.detected_language
                                    FROM call_transcripts ct
                                    WHERE ct.customer_id = c.customer_id
                                      AND NULLIF(TRIM(ct.detected_language), '') IS NOT NULL
                                    ORDER BY ct.process_date DESC, ct.transcript_id DESC
                                    LIMIT 1
                                ), ''
                            )) LIKE '%portugu%'
                              OR LOWER(COALESCE(c.country, '')) IN ('brazil', 'brasil')
                            THEN 'pt'
                            ELSE 'es'
                        END AS default_language
                    FROM customers c
                )
                SELECT
                    customer_id,
                    country,
                    detected_accent,
                    customer_status,
                    detected_language,
                    transcript_count
                FROM customer_candidates
                WHERE {' AND '.join(clauses)}
                ORDER BY transcript_count DESC, customer_id
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [
            ChallengeCustomerSummary(
                customer_id=str(row[0]),
                country=None if row[1] is None else str(row[1]),
                detected_accent=None if row[2] is None else str(row[2]),
                customer_status=None if row[3] is None else str(row[3]),
                default_language=self._challenge_language(
                    None if row[1] is None else str(row[1]),
                    None if row[4] is None else str(row[4]),
                ),
                transcript_count=int(row[5]),
            )
            for row in rows
        ]

    def list_challenge_customer_messages(
        self,
        customer_id: str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ChallengeMessageSummary]:
        """Page through every provided customer message for one challenge customer."""

        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if not self.has_full_challenge_data():
            raise IncompatibleBankDatabaseError(
                "Full challenge data tables are not available in this artifact."
            )

        with self._connect() as con:
            rows = con.execute(
                """
                SELECT
                    transcript_id,
                    interaction_id,
                    process_date,
                    customer_text,
                    detected_language,
                    main_topics
                FROM call_transcripts
                WHERE customer_id = ?
                  AND NULLIF(TRIM(customer_text), '') IS NOT NULL
                ORDER BY process_date DESC, transcript_id DESC
                LIMIT ? OFFSET ?
                """,
                [customer_id, limit, offset],
            ).fetchall()

        return [
            ChallengeMessageSummary(
                transcript_id=str(row[0]),
                interaction_id=None if row[1] is None else str(row[1]),
                process_date=None if row[2] is None else str(row[2]),
                customer_text=str(row[3]),
                detected_language=None if row[4] is None else str(row[4]),
                main_topics=None if row[5] is None else str(row[5]),
            )
            for row in rows
        ]

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
