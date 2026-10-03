from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ALLOWED_INTERPRETATION_PROVIDERS = {
    "deterministic",
    "openai-gpt-6-luna",
}


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime paths, data mode, and bounded interpretation provider selection."""

    bank_db_path: Path
    runtime_db_path: Path
    data_mode: str
    interpretation_provider: str = "deterministic"


def load_settings() -> Settings:
    data_mode = os.getenv("DATA_MODE", "synthetic").strip().casefold()
    if data_mode not in {"synthetic", "curated"}:
        raise ValueError("DATA_MODE must be 'synthetic' or 'curated'")

    interpretation_provider = os.getenv(
        "INTERPRETATION_PROVIDER",
        "deterministic",
    ).strip()
    if not interpretation_provider:
        interpretation_provider = "deterministic"
    if interpretation_provider not in ALLOWED_INTERPRETATION_PROVIDERS:
        raise ValueError(
            "INTERPRETATION_PROVIDER must be 'deterministic' "
            "or 'openai-gpt-6-luna'"
        )

    default_bank = (
        "runtime/synthetic-demo.duckdb"
        if data_mode == "synthetic"
        else "data/curated/bank.duckdb"
    )
    default_runtime = (
        "runtime/synthetic-runtime.sqlite"
        if data_mode == "synthetic"
        else "runtime/curated-runtime.sqlite"
    )
    return Settings(
        bank_db_path=Path(os.getenv("BANK_DB_PATH", default_bank)),
        runtime_db_path=Path(os.getenv("RUNTIME_DB_PATH", default_runtime)),
        data_mode=data_mode,
        interpretation_provider=interpretation_provider,
    )


settings = load_settings()
