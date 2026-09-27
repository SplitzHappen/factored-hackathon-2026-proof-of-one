from pathlib import Path


def _lines(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_private_and_generated_artifacts_are_gitignored() -> None:
    root = Path(__file__).resolve().parents[1]
    ignore_text = (root / ".gitignore").read_text(encoding="utf-8")
    lines = _lines(root / ".gitignore")

    required = {
        ".env",
        ".env.*",
        "runtime/",
        "*.sqlite",
        "*.sqlite3",
        "data/raw/",
        "data/curated/",
        "*.duckdb",
        "*.duckdb.wal",
        "evaluation/private/",
        "evaluation/results/private/",
        "ml/private/",
    }
    assert required <= lines
    assert "!.env.example" in lines
    assert r"\n# Offline ML working artifacts\nml/private/\n" not in ignore_text


def test_docker_context_excludes_local_state_and_private_data() -> None:
    root = Path(__file__).resolve().parents[1]
    lines = _lines(root / ".dockerignore")

    required = {
        ".git",
        ".github",
        ".venv",
        "runtime",
        "data",
        "*.sqlite",
        "*.sqlite3",
        "*.duckdb",
        ".env",
    }
    assert required <= lines


def test_env_example_contains_placeholders_not_credentials() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / ".env.example").read_text(encoding="utf-8")

    secret_keys = {
        "OPENAI_API_KEY",
        "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY",
    }
    values = {}
    for line in text.splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    for key in secret_keys:
        assert key in values
        assert values[key] == ""

    lowered = text.casefold()
    assert "sk-" not in lowered
    assert "api_key=your" not in lowered
