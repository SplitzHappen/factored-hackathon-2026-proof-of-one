from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime paths and public/organizer data mode."""

    bank_db_path: Path
    runtime_db_path: Path
    data_mode: str


def load_settings() -> Settings:
    data_mode = os.getenv("DATA_MODE", "synthetic").strip().casefold()
    if data_mode not in {"synthetic", "curated"}:
        raise ValueError("DATA_MODE must be 'synthetic' or 'curated'")
    default_bank = (
        "runtime/synthetic-demo.duckdb"
        if data_mode == "synthetic"
        else "data/curated/bank.duckdb"
    )
    return Settings(
        bank_db_path=Path(os.getenv("BANK_DB_PATH", default_bank)),
        runtime_db_path=Path(os.getenv("RUNTIME_DB_PATH", "runtime/runtime.sqlite")),
        data_mode=data_mode,
    )


settings = load_settings()
