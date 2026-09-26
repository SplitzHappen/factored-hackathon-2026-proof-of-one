from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from app.schemas import SupportedLanguage


DEMO_TENANT_ID = "proof-of-one-demo"


@dataclass(frozen=True, slots=True)
class DemoPersona:
    persona_id: str
    display_name: str
    customer_id: str
    default_language: SupportedLanguage
    timezone_name: str


DEMO_PERSONAS: dict[str, DemoPersona] = {
    "lucia": DemoPersona(
        persona_id="lucia",
        display_name="Lucía",
        customer_id="DEMO-CUST-ES-001",
        default_language=SupportedLanguage.ES,
        timezone_name="America/Bogota",
    ),
    "rafael": DemoPersona(
        persona_id="rafael",
        display_name="Rafael",
        customer_id="DEMO-CUST-PT-001",
        default_language=SupportedLanguage.PT,
        timezone_name="America/Sao_Paulo",
    ),
}


def build_synthetic_demo_bank(path: Path) -> Path:
    """Create the public synthetic banking artifact used by the walking skeleton.

    This artifact contains no organizer rows or identifiers. It intentionally mirrors
    the curated runtime schema consumed by BankRepository so the same repository and
    policy path are exercised in demo mode.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    con = duckdb.connect(str(target))
    try:
        con.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        con.execute(
            "INSERT INTO build_metadata VALUES (1, 'synthetic-demo-v1')"
        )
        con.execute(
            """
            CREATE TABLE customers (
                customer_id VARCHAR,
                country VARCHAR,
                detected_accent VARCHAR,
                customer_status VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO customers VALUES
            ('DEMO-CUST-ES-001', 'Colombia', 'synthetic', 'Active'),
            ('DEMO-CUST-PT-001', 'Brazil', 'synthetic', 'Active')
            """
        )
        con.execute(
            """
            CREATE TABLE products (
                product_id VARCHAR,
                customer_id VARCHAR,
                product_type VARCHAR,
                currency VARCHAR,
                current_balance DECIMAL(15,2),
                opening_date DATE,
                expiration_date DATE,
                product_status VARCHAR,
                last_transaction_date TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO products VALUES
            ('DEMO-PROD-ES-001', 'DEMO-CUST-ES-001', 'Checking Account',
             'COP', 3250000.00, DATE '2025-01-10', NULL, 'Active',
             TIMESTAMP '2026-09-25 18:30:00'),
            ('DEMO-PROD-PT-001', 'DEMO-CUST-PT-001', 'Checking Account',
             'BRL', 8450.00, DATE '2025-02-14', NULL, 'Active',
             TIMESTAMP '2026-09-25 17:15:00')
            """
        )
        con.execute(
            """
            CREATE TABLE transactions (
                transaction_id VARCHAR,
                transaction_date TIMESTAMP,
                product_id VARCHAR,
                customer_id VARCHAR,
                transaction_type VARCHAR,
                transaction_category VARCHAR,
                amount DECIMAL(15,2),
                currency VARCHAR,
                channel VARCHAR,
                merchant_name VARCHAR,
                merchant_category VARCHAR,
                transaction_country VARCHAR,
                transaction_city VARCHAR,
                transaction_status VARCHAR,
                is_fraud BOOLEAN,
                fraud_score DECIMAL(5,2)
            )
            """
        )
        con.execute(
            """
            INSERT INTO transactions VALUES
            ('DEMO-ES-1001', TIMESTAMP '2026-09-25 18:30:00',
             'DEMO-PROD-ES-001', 'DEMO-CUST-ES-001',
             'Payment', 'Retail', 125000.00, 'COP', 'App',
             'Mercado Central', 'Retail', 'Colombia', 'Bogota',
             'Approved', NULL, NULL),
            ('DEMO-ES-1002', TIMESTAMP '2026-09-24 09:10:00',
             'DEMO-PROD-ES-001', 'DEMO-CUST-ES-001',
             'Transfer', NULL, 83000.00, 'COP', 'Web',
             NULL, NULL, 'Colombia', 'Bogota',
             'Pending', NULL, NULL),
            ('DEMO-ES-1003', TIMESTAMP '2026-09-21 12:05:00',
             'DEMO-PROD-ES-001', 'DEMO-CUST-ES-001',
             'Payment', 'Utilities', 54000.00, 'COP', 'App',
             'Energia Hogar', 'Utilities', 'Colombia', 'Bogota',
             'Declined', NULL, NULL),
            ('DEMO-ES-1004', TIMESTAMP '2026-09-19 16:40:00',
             'DEMO-PROD-ES-001', 'DEMO-CUST-ES-001',
             'Payment', 'Retail', 54000.00, 'COP', 'Web',
             'Comercio Norte', 'Retail', 'Colombia', 'Bogota',
             'Approved', NULL, NULL),
            ('DEMO-PT-2001', TIMESTAMP '2026-09-25 17:15:00',
             'DEMO-PROD-PT-001', 'DEMO-CUST-PT-001',
             'Payment', 'Retail', 219.90, 'BRL', 'App',
             'Mercado Bairro', 'Retail', 'Brazil', 'Sao Paulo',
             'Approved', NULL, NULL),
            ('DEMO-PT-2002', TIMESTAMP '2026-09-23 08:45:00',
             'DEMO-PROD-PT-001', 'DEMO-CUST-PT-001',
             'Transfer', NULL, 83.40, 'BRL', 'Web',
             NULL, NULL, 'Brazil', 'Sao Paulo',
             'Pending', NULL, NULL),
            ('DEMO-PT-2003', TIMESTAMP '2026-09-20 14:25:00',
             'DEMO-PROD-PT-001', 'DEMO-CUST-PT-001',
             'Payment', 'Utilities', 142.75, 'BRL', 'App',
             'Servico Casa', 'Utilities', 'Brazil', 'Sao Paulo',
             'Declined', NULL, NULL),
            ('DEMO-PT-2004', TIMESTAMP '2026-09-18 10:15:00',
             'DEMO-PROD-PT-001', 'DEMO-CUST-PT-001',
             'Payment', 'Retail', 142.75, 'BRL', 'Web',
             'Loja Bairro', 'Retail', 'Brazil', 'Sao Paulo',
             'Approved', NULL, NULL)
            """
        )
    finally:
        con.close()

    return target
