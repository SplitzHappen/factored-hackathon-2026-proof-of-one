from __future__ import annotations

from pathlib import Path
from typing import Literal

import duckdb


BankArtifactMode = Literal["synthetic", "curated"]

SYNTHETIC_SCHEMA_VERSION = 1
SYNTHETIC_BUILDER_VERSION = "synthetic-demo-v1"
CURATED_SCHEMA_VERSION = 1
CURATED_BUILDER_VERSION = "r3b-1"
FULL_CURATED_BUILDER_VERSION = "r3b-full-1"
CURATED_BUILDER_VERSIONS = frozenset(
    {
        CURATED_BUILDER_VERSION,
        FULL_CURATED_BUILDER_VERSION,
    }
)


class BankArtifactIdentityError(RuntimeError):
    """Raised when a banking artifact cannot be identified unambiguously."""


def identify_bank_artifact_mode(path: Path) -> BankArtifactMode:
    """Identify the trusted data mode from immutable DuckDB build metadata."""

    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise BankArtifactIdentityError(
            f"Banking artifact does not exist or is not a file: {target}"
        )

    connection: duckdb.DuckDBPyConnection | None = None
    try:
        connection = duckdb.connect(
            str(target),
            read_only=True,
            config={"enable_external_access": "false"},
        )
        rows = connection.execute(
            "SELECT schema_version, builder_version FROM build_metadata"
        ).fetchall()
    except Exception as exc:
        raise BankArtifactIdentityError(
            "Banking artifact is missing readable build identity metadata."
        ) from exc
    finally:
        if connection is not None:
            connection.close()

    if len(rows) != 1:
        raise BankArtifactIdentityError(
            "Banking artifact must contain exactly one build identity row."
        )

    identity = (int(rows[0][0]), str(rows[0][1]))
    if identity == (SYNTHETIC_SCHEMA_VERSION, SYNTHETIC_BUILDER_VERSION):
        return "synthetic"
    if (
        identity[0] == CURATED_SCHEMA_VERSION
        and identity[1] in CURATED_BUILDER_VERSIONS
    ):
        return "curated"

    raise BankArtifactIdentityError(
        "Banking artifact build identity is not recognized by this runtime."
    )
