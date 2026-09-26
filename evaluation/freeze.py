from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from app.schemas import SupportedLanguage
from evaluation.contracts import (
    DevelopmentAnswerKey,
    DevelopmentCase,
    FrozenEvaluationManifest,
    HeldoutAnswerKey,
    HeldoutCase,
)
from evaluation.generate import generate
from evaluation.suite import (
    SUITE_VERSION,
    build_manifest as build_suite_manifest,
    canonical_jsonl,
    load_jsonl,
    sha256_bytes,
    validate_suite,
)


FREEZE_VERSION = "factored-eval-freeze-v1"
DEFAULT_SEED = "proof-of-one-eval-v1"


class FreezeError(RuntimeError):
    """Raised when the evaluation freeze cannot be completed safely."""


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(repo_root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise FreezeError(
            "Refusing to freeze from a dirty Git working tree. Commit/stash changes first."
        )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise FreezeError("Could not resolve a canonical 40-character Git commit.")
    return commit


def _load_curated_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "builder_version",
        "curated_schema_version",
        "database_sha256",
        "row_counts",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise FreezeError(
            "Curated build manifest is missing required fields: "
            + ", ".join(missing)
        )
    return payload



def _validate_curated_metadata(
    *,
    database_path: Path,
    curated_manifest: dict[str, object],
) -> None:
    con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        row = con.execute(
            "SELECT schema_version, builder_version FROM build_metadata LIMIT 1"
        ).fetchone()
    finally:
        con.close()

    if row is None:
        raise FreezeError("Curated database is missing build metadata.")
    if int(row[0]) != int(curated_manifest["curated_schema_version"]):
        raise FreezeError(
            "Curated database schema version disagrees with build manifest."
        )
    if str(row[1]) != str(curated_manifest["builder_version"]):
        raise FreezeError(
            "Curated database builder version disagrees with build manifest."
        )

    row_counts = curated_manifest.get("row_counts")
    if not isinstance(row_counts, dict):
        raise FreezeError("Curated build manifest row_counts is invalid.")

    con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        actual_counts = {
            table: int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("customers", "products", "transactions")
        }
    finally:
        con.close()

    for table, actual in actual_counts.items():
        if actual != int(row_counts[table]):
            raise FreezeError(
                f"Curated database {table} row count disagrees with build manifest."
            )


def _validate_development_pool(
    cases: list[DevelopmentCase],
    keys: list[DevelopmentAnswerKey],
    heldout_cases: list[HeldoutCase],
) -> None:
    errors: list[str] = []

    if len(cases) != 100:
        errors.append(f"expected 100 development cases; found {len(cases)}")

    spanish = sum(case.language is SupportedLanguage.ES for case in cases)
    portuguese = sum(case.language is SupportedLanguage.PT for case in cases)
    if spanish != 75:
        errors.append(f"expected 75 Spanish development cases; found {spanish}")
    if portuguese != 25:
        errors.append(f"expected 25 Portuguese development cases; found {portuguese}")

    case_ids = [case.case_id for case in cases]
    key_ids = [key.case_id for key in keys]
    if len(case_ids) != len(set(case_ids)):
        errors.append("development case IDs must be unique")
    if len(key_ids) != len(set(key_ids)):
        errors.append("development answer-key IDs must be unique")
    if set(case_ids) != set(key_ids):
        errors.append("development case IDs and answer-key IDs must match exactly")

    keys_by_id = {key.case_id: key for key in keys}
    cases_by_id = {case.case_id: case for case in cases}
    for case in cases:
        key = keys_by_id.get(case.case_id)
        if key is not None and len(case.steps) != len(key.expectations):
            errors.append(
                f"{case.case_id}: step count does not match answer-key expectations"
            )
        expected_prefix = f"DEV-{case.language.value.upper()}-"
        if not case.case_id.startswith(expected_prefix):
            errors.append(
                f"{case.case_id}: development ID prefix does not match language"
            )
        if case.language is SupportedLanguage.PT:
            if case.source_pair_id is None:
                errors.append(
                    f"{case.case_id}: Portuguese development case lacks source_pair_id"
                )
            else:
                source = cases_by_id.get(case.source_pair_id)
                if source is None or source.language is not SupportedLanguage.ES:
                    errors.append(
                        f"{case.case_id}: Portuguese source_pair_id must reference "
                        "a Spanish development case"
                    )

    heldout_customers = {
        case.locator.customer_id
        for case in heldout_cases
        if case.language is SupportedLanguage.ES
    }
    development_customers = {
        case.locator.customer_id
        for case in cases
        if case.language is SupportedLanguage.ES
    }
    overlap = heldout_customers & development_customers
    if overlap:
        errors.append("held-out and development primary customers overlap")

    if errors:
        raise FreezeError("\n".join(errors))



def _verify_locator_integrity(
    *,
    database_path: Path,
    heldout_cases: list[HeldoutCase],
    development_cases: list[DevelopmentCase],
) -> None:
    """Independently verify frozen locator ownership and pool separation."""

    con = duckdb.connect(
        str(database_path),
        read_only=True,
        config={"enable_external_access": "false"},
    )
    try:
        metadata = con.execute(
            "SELECT schema_version FROM build_metadata LIMIT 1"
        ).fetchone()
        if metadata is None:
            raise FreezeError("Curated database is missing build metadata.")

        def owners_for_pool(
            cases: list[HeldoutCase] | list[DevelopmentCase],
        ) -> set[str]:
            referenced_owners: set[str] = set()
            for case in cases:
                customer_exists = con.execute(
                    "SELECT 1 FROM customers WHERE customer_id = ? LIMIT 1",
                    [case.locator.customer_id],
                ).fetchone()
                if customer_exists is None:
                    raise FreezeError("Evaluation locator references an unknown customer.")

                referenced_owners.add(case.locator.customer_id)

                for product_id in case.locator.product_ids:
                    row = con.execute(
                        "SELECT customer_id FROM products WHERE product_id = ? LIMIT 1",
                        [product_id],
                    ).fetchone()
                    if row is None:
                        raise FreezeError("Evaluation locator references an unknown product.")
                    if str(row[0]) != case.locator.customer_id:
                        raise FreezeError(
                            "Evaluation primary product does not belong to locator customer."
                        )
                    referenced_owners.add(str(row[0]))

                transaction_owners: list[str] = []
                for transaction_id in case.locator.transaction_ids:
                    row = con.execute(
                        "SELECT customer_id FROM transactions "
                        "WHERE transaction_id = ? LIMIT 1",
                        [transaction_id],
                    ).fetchone()
                    if row is None:
                        raise FreezeError(
                            "Evaluation locator references an unknown transaction."
                        )
                    owner = str(row[0])
                    transaction_owners.append(owner)
                    referenced_owners.add(owner)

                if (
                    transaction_owners
                    and transaction_owners[0] != case.locator.customer_id
                ):
                    raise FreezeError(
                        "Evaluation primary transaction does not belong to "
                        "locator customer."
                    )

            return referenced_owners

        heldout_owners = owners_for_pool(heldout_cases)
        development_owners = owners_for_pool(development_cases)
        if heldout_owners & development_owners:
            raise FreezeError(
                "Held-out and development pools share organizer customers."
            )
    finally:
        con.close()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    _atomic_write(
        path,
        (
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8"),
    )


def _canonical_sorted_jsonl(models: list[object], id_attr: str = "case_id") -> bytes:
    ordered = sorted(models, key=lambda model: getattr(model, id_attr))
    return canonical_jsonl(ordered)


def freeze_evaluation(
    *,
    database_path: Path,
    curated_manifest_path: Path,
    output_root: Path,
    repo_root: Path,
) -> FrozenEvaluationManifest:
    database_path = database_path.expanduser().resolve()
    curated_manifest_path = curated_manifest_path.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    if not database_path.is_file():
        raise FileNotFoundError(f"Curated database does not exist: {database_path}")
    if not curated_manifest_path.is_file():
        raise FileNotFoundError(
            f"Curated build manifest does not exist: {curated_manifest_path}"
        )

    final_dir = output_root / "private" / "frozen" / SUITE_VERSION
    if final_dir.exists():
        raise FreezeError(
            f"Frozen evaluation directory already exists: {final_dir}. "
            "Use verify mode instead of overwriting a frozen suite."
        )

    curated_manifest = _load_curated_manifest(curated_manifest_path)
    database_sha = _sha256_file(database_path)
    expected_database_sha = str(curated_manifest["database_sha256"])
    if database_sha != expected_database_sha:
        raise FreezeError(
            "Curated database SHA-256 does not match its build manifest."
        )
    _validate_curated_metadata(
        database_path=database_path,
        curated_manifest=curated_manifest,
    )

    build_dir = output_root / "private" / ".freeze-building"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    try:
        summary = generate(
            database_path=database_path,
            output_dir=build_dir,
            seed=DEFAULT_SEED,
        )
        private_dir = build_dir / "private"

        heldout_cases = load_jsonl(
            private_dir / "heldout_cases.jsonl",
            HeldoutCase,
        )
        heldout_keys = load_jsonl(
            private_dir / "heldout_answer_keys.jsonl",
            HeldoutAnswerKey,
        )
        development_cases = load_jsonl(
            private_dir / "development_cases.jsonl",
            DevelopmentCase,
        )
        development_keys = load_jsonl(
            private_dir / "development_answer_keys.jsonl",
            DevelopmentAnswerKey,
        )

        validate_suite(heldout_cases, heldout_keys)
        _validate_development_pool(
            development_cases,
            development_keys,
            heldout_cases,
        )
        _verify_locator_integrity(
            database_path=database_path,
            heldout_cases=heldout_cases,
            development_cases=development_cases,
        )

        if summary["customer_overlap"] != 0:
            raise FreezeError("Generator reported nonzero held-out/development overlap.")

        # Build the frozen held-out manifest from canonical model objects.
        suite_manifest = build_suite_manifest(heldout_cases, heldout_keys)

        heldout_case_bytes = _canonical_sorted_jsonl(heldout_cases)
        heldout_key_bytes = _canonical_sorted_jsonl(heldout_keys)
        development_case_bytes = _canonical_sorted_jsonl(development_cases)
        development_key_bytes = _canonical_sorted_jsonl(development_keys)

        if sha256_bytes(heldout_case_bytes) != suite_manifest.cases_sha256:
            raise FreezeError("Held-out case bytes do not match suite manifest hash.")
        if sha256_bytes(heldout_key_bytes) != suite_manifest.answer_keys_sha256:
            raise FreezeError("Held-out answer-key bytes do not match suite manifest hash.")

        development_combined = (
            development_case_bytes
            + b"---ANSWER-KEYS---\n"
            + development_key_bytes
        )

        row_counts = curated_manifest["row_counts"]
        if not isinstance(row_counts, dict):
            raise FreezeError("Curated build manifest row_counts is invalid.")

        manifest = FrozenEvaluationManifest(
            freeze_version=FREEZE_VERSION,
            frozen_utc=datetime.now(timezone.utc).isoformat(),
            generator_seed=DEFAULT_SEED,
            implementation_commit=_git_head(repo_root),
            curated_database_sha256=database_sha,
            curated_manifest_sha256=_sha256_file(curated_manifest_path),
            curated_schema_version=int(curated_manifest["curated_schema_version"]),
            curated_builder_version=str(curated_manifest["builder_version"]),
            curated_customer_count=int(row_counts["customers"]),
            curated_product_count=int(row_counts["products"]),
            curated_transaction_count=int(row_counts["transactions"]),
            suite=suite_manifest,
            development_cases_sha256=sha256_bytes(development_case_bytes),
            development_answer_keys_sha256=sha256_bytes(development_key_bytes),
            development_combined_sha256=sha256_bytes(development_combined),
            development_case_count=len(development_cases),
            development_spanish_count=sum(
                case.language is SupportedLanguage.ES
                for case in development_cases
            ),
            development_portuguese_count=sum(
                case.language is SupportedLanguage.PT
                for case in development_cases
            ),
            heldout_development_customer_overlap=0,
        )

        staging = final_dir.with_name(final_dir.name + ".staging")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        _atomic_write(staging / "heldout_cases.jsonl", heldout_case_bytes)
        _atomic_write(staging / "heldout_answer_keys.jsonl", heldout_key_bytes)
        _atomic_write(staging / "development_cases.jsonl", development_case_bytes)
        _atomic_write(
            staging / "development_answer_keys.jsonl",
            development_key_bytes,
        )
        _atomic_write_json(
            staging / "freeze_manifest.json",
            manifest.model_dump(mode="json"),
        )

        final_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, final_dir)

        verified = verify_frozen_evaluation(
            frozen_dir=final_dir,
            database_path=database_path,
            curated_manifest_path=curated_manifest_path,
        )
        if verified != manifest:
            raise FreezeError(
                "Persisted evaluation freeze did not verify against the in-memory manifest."
            )
        return verified
    finally:
        if build_dir.exists():
            shutil.rmtree(build_dir)


def verify_frozen_evaluation(
    *,
    frozen_dir: Path,
    database_path: Path,
    curated_manifest_path: Path,
) -> FrozenEvaluationManifest:
    frozen_dir = frozen_dir.expanduser().resolve()
    manifest_path = frozen_dir / "freeze_manifest.json"
    if not manifest_path.is_file():
        raise FreezeError(f"Freeze manifest is missing: {manifest_path}")

    manifest = FrozenEvaluationManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if manifest.freeze_version != FREEZE_VERSION:
        raise FreezeError(
            f"Frozen evaluation version {manifest.freeze_version!r} is unsupported; "
            f"expected {FREEZE_VERSION!r}."
        )
    if manifest.generator_seed != DEFAULT_SEED:
        raise FreezeError("Frozen evaluation generator seed is not the canonical seed.")

    heldout_cases = load_jsonl(
        frozen_dir / "heldout_cases.jsonl",
        HeldoutCase,
    )
    heldout_keys = load_jsonl(
        frozen_dir / "heldout_answer_keys.jsonl",
        HeldoutAnswerKey,
    )
    development_cases = load_jsonl(
        frozen_dir / "development_cases.jsonl",
        DevelopmentCase,
    )
    development_keys = load_jsonl(
        frozen_dir / "development_answer_keys.jsonl",
        DevelopmentAnswerKey,
    )

    validate_suite(heldout_cases, heldout_keys)
    _validate_development_pool(
        development_cases,
        development_keys,
        heldout_cases,
    )
    _verify_locator_integrity(
        database_path=database_path.resolve(),
        heldout_cases=heldout_cases,
        development_cases=development_cases,
    )

    suite_manifest = build_suite_manifest(heldout_cases, heldout_keys)
    if suite_manifest != manifest.suite:
        raise FreezeError("Frozen held-out artifacts no longer match suite manifest.")

    development_case_bytes = _canonical_sorted_jsonl(development_cases)
    development_key_bytes = _canonical_sorted_jsonl(development_keys)
    development_combined = (
        development_case_bytes
        + b"---ANSWER-KEYS---\n"
        + development_key_bytes
    )
    if sha256_bytes(development_case_bytes) != manifest.development_cases_sha256:
        raise FreezeError("Frozen development cases hash mismatch.")
    if (
        sha256_bytes(development_key_bytes)
        != manifest.development_answer_keys_sha256
    ):
        raise FreezeError("Frozen development answer keys hash mismatch.")
    if (
        sha256_bytes(development_combined)
        != manifest.development_combined_sha256
    ):
        raise FreezeError("Frozen development combined hash mismatch.")

    if _sha256_file(database_path.resolve()) != manifest.curated_database_sha256:
        raise FreezeError("Current curated database does not match frozen provenance.")
    if (
        _sha256_file(curated_manifest_path.resolve())
        != manifest.curated_manifest_sha256
    ):
        raise FreezeError("Current curated build manifest does not match frozen provenance.")

    return manifest


def _safe_summary(manifest: FrozenEvaluationManifest) -> dict[str, object]:
    return {
        "freeze_version": manifest.freeze_version,
        "generator_seed": manifest.generator_seed,
        "implementation_commit": manifest.implementation_commit,
        "curated_database_sha256": manifest.curated_database_sha256,
        "curated_manifest_sha256": manifest.curated_manifest_sha256,
        "curated_customer_count": manifest.curated_customer_count,
        "curated_product_count": manifest.curated_product_count,
        "curated_transaction_count": manifest.curated_transaction_count,
        "suite_version": manifest.suite.suite_version,
        "heldout_cases": manifest.suite.case_count,
        "spanish_cases": manifest.suite.spanish_count,
        "portuguese_cases": manifest.suite.portuguese_count,
        "multi_turn_cases": manifest.suite.multi_turn_count,
        "high_risk_repeat_cases": manifest.suite.high_risk_repeat_count,
        "heldout_cases_sha256": manifest.suite.cases_sha256,
        "heldout_answer_keys_sha256": manifest.suite.answer_keys_sha256,
        "heldout_combined_sha256": manifest.suite.combined_sha256,
        "development_cases": manifest.development_case_count,
        "development_spanish_cases": manifest.development_spanish_count,
        "development_portuguese_cases": manifest.development_portuguese_count,
        "development_combined_sha256": manifest.development_combined_sha256,
        "heldout_development_customer_overlap": (
            manifest.heldout_development_customer_overlap
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/curated/bank.duckdb")
    parser.add_argument(
        "--curated-manifest",
        default="data/curated/build_manifest.json",
    )
    parser.add_argument("--output-root", default="evaluation")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing frozen suite instead of creating one.",
    )
    args = parser.parse_args()

    if args.verify:
        manifest = verify_frozen_evaluation(
            frozen_dir=(
                Path(args.output_root)
                / "private"
                / "frozen"
                / SUITE_VERSION
            ),
            database_path=Path(args.database),
            curated_manifest_path=Path(args.curated_manifest),
        )
        print("EVALUATION FREEZE VERIFIED")
    else:
        manifest = freeze_evaluation(
            database_path=Path(args.database),
            curated_manifest_path=Path(args.curated_manifest),
            output_root=Path(args.output_root),
            repo_root=Path(args.repo_root),
        )
        print("EVALUATION FREEZE COMPLETE")

    print(json.dumps(_safe_summary(manifest), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
