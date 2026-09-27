from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
FROZEN_REALISTIC_CASES = (
    ROOT
    / "evaluation"
    / "frozen"
    / "factored-realistic-language-v1"
    / "cases.jsonl"
)


def test_required_demo_timezones_are_available_cross_platform() -> None:
    assert ZoneInfo("America/Bogota").key == "America/Bogota"
    assert ZoneInfo("America/Sao_Paulo").key == "America/Sao_Paulo"


def test_tzdata_is_pinned_in_runtime_requirements() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()

    assert "tzdata==2026.4" in {line.strip() for line in requirements}


def test_frozen_evaluation_tree_is_forced_to_lf() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()

    assert "evaluation/frozen/** text eol=lf" in {
        line.strip() for line in attributes
    }


def test_frozen_realistic_cases_are_lf_byte_stable() -> None:
    raw = FROZEN_REALISTIC_CASES.read_bytes()

    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
