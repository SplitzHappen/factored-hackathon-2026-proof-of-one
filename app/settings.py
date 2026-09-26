from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime paths. Raw organizer data is intentionally not exposed here."""

    bank_db_path: Path
    runtime_db_path: Path


def load_settings() -> Settings:
    return Settings(
        bank_db_path=Path(os.getenv("BANK_DB_PATH", "data/curated/bank.duckdb")),
        runtime_db_path=Path(os.getenv("RUNTIME_DB_PATH", "runtime/runtime.sqlite")),
    )


settings = load_settings()
