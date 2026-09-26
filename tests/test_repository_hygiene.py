from pathlib import Path


def test_private_ml_artifacts_are_gitignored() -> None:
    root = Path(__file__).resolve().parents[1]
    ignore_text = (root / ".gitignore").read_text(encoding="utf-8")
    lines = {line.strip() for line in ignore_text.splitlines()}

    assert "ml/private/" in lines
    assert r"\n# Offline ML working artifacts\nml/private/\n" not in ignore_text
