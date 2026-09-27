from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import duckdb

from app.artifact_identity import (
    SYNTHETIC_BUILDER_VERSION,
    SYNTHETIC_SCHEMA_VERSION,
)
from app.schemas import SupportedLanguage


DEMO_TENANT_ID = "proof-of-one-demo"
SYNTHETIC_BUILD_LOCK_TIMEOUT_SECONDS = 10.0


class SyntheticArtifactSafetyError(ValueError):
    """Raised when a configured demo artifact cannot be replaced safely."""


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


def _is_recognized_synthetic_demo_bank(path: Path) -> bool:
    """Return True only for the exact synthetic artifact version we may replace."""

    connection: duckdb.DuckDBPyConnection | None = None
    try:
        connection = duckdb.connect(
            str(path),
            read_only=True,
            config={"enable_external_access": "false"},
        )
        rows = connection.execute(
            "SELECT schema_version, builder_version FROM build_metadata"
        ).fetchall()
    except Exception:
        return False
    finally:
        if connection is not None:
            connection.close()

    return rows == [
        (SYNTHETIC_SCHEMA_VERSION, SYNTHETIC_BUILDER_VERSION)
    ]


def _assert_replaceable_synthetic_target(target: Path) -> None:
    if target.is_symlink():
        raise SyntheticArtifactSafetyError(
            "Refusing to replace BANK_DB_PATH through a symbolic link."
        )
    if not target.exists():
        return
    if not target.is_file() or not _is_recognized_synthetic_demo_bank(target):
        raise SyntheticArtifactSafetyError(
            "Refusing to replace existing BANK_DB_PATH because it is not a "
            "recognized Proof of One synthetic demo artifact."
        )


@contextmanager
def _synthetic_build_lock(target: Path) -> Iterator[None]:
    """Serialize first-time synthetic artifact creation across local workers."""

    lock_path = target.with_name(f".{target.name}.build.lock")
    deadline = time.monotonic() + SYNTHETIC_BUILD_LOCK_TIMEOUT_SECONDS

    while True:
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SyntheticArtifactSafetyError(
                    "Timed out waiting for the synthetic demo artifact build lock."
                )
            time.sleep(0.05)
            continue
        else:
            os.close(descriptor)
            break

    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def ensure_synthetic_demo_bank(path: Path) -> Path:
    """Ensure one valid synthetic demo artifact exists without refreshing it.

    Repeated startup is read-only once the exact synthetic artifact exists. If the
    target is absent, first-time creation is serialized so concurrent local workers
    cannot build over one another. Public multi-worker deployment remains separately
    gated until the broader deployment/concurrency repair set is complete.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_replaceable_synthetic_target(target)
    if target.exists():
        return target

    with _synthetic_build_lock(target):
        _assert_replaceable_synthetic_target(target)
        if not target.exists():
            build_synthetic_demo_bank(target)

    return target


def _write_synthetic_demo_bank(path: Path) -> None:
    connection = duckdb.connect(str(path))
    try:
        connection.execute(
            """
            CREATE TABLE build_metadata (
                schema_version INTEGER NOT NULL,
                builder_version VARCHAR NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO build_metadata VALUES (?, ?)",
            [SYNTHETIC_SCHEMA_VERSION, SYNTHETIC_BUILDER_VERSION],
        )
        connection.execute(
            """
            CREATE TABLE customers (
                customer_id VARCHAR,
                country VARCHAR,
                detected_accent VARCHAR,
                customer_status VARCHAR
            )
            """
        )
        connection.execute(
            """
            INSERT INTO customers VALUES
            ('DEMO-CUST-ES-001', 'Colombia', 'synthetic', 'Active'),
            ('DEMO-CUST-PT-001', 'Brazil', 'synthetic', 'Active')
            """
        )
        connection.execute(
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
        connection.execute(
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
        connection.execute(
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
        connection.execute(
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
        connection.execute("CHECKPOINT")
    finally:
        connection.close()


def build_synthetic_demo_bank(path: Path) -> Path:
    """Create or safely refresh the public synthetic banking artifact.

    An existing target is replaceable only when its build metadata positively
    identifies the exact Proof of One synthetic artifact version. Curated,
    unrelated, malformed, directory, and symlink targets fail closed.

    New bytes are built and validated beside the target first, then installed
    with os.replace so a build/replace failure cannot destroy the prior artifact.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_replaceable_synthetic_target(target)

    temporary = target.with_name(
        f".{target.name}.{uuid4().hex}.building"
    )
    temporary_wal = Path(str(temporary) + ".wal")

    try:
        _write_synthetic_demo_bank(temporary)
        if not _is_recognized_synthetic_demo_bank(temporary):
            raise RuntimeError(
                "Synthetic demo artifact failed post-build identity validation."
            )
        os.replace(temporary, target)
    finally:
        for stale in (temporary, temporary_wal):
            if stale.exists():
                stale.unlink()

    return target
