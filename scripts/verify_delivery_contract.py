#!/usr/bin/env python3
"""Fail-closed PR preflight for Factored high-assurance verified delivery.

This check intentionally verifies only repository-visible prerequisites. The
private Continuity control plane remains authoritative for independent audit,
held-out evidence, reconciliation, and owner acceptance records.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = "SplitzHappen/factored-hackathon-2026-proof-of-one"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
META_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*?)\s*$")

REQUIRED_BODY_FIELDS = (
    "Verified-Delivery-Contract",
    "Candidate-Head-SHA",
    "Evidence-Status",
    "Independent-Audit",
    "Owner-Acceptance",
    "Verifier-Change-Disposition",
    "Release-Intent",
)


class Failure(Exception):
    pass


def fail(message: str) -> None:
    raise Failure(message)


def load_event() -> dict[str, Any]:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        fail("GITHUB_EVENT_PATH is missing.")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Cannot read GitHub event payload: {exc}")


def parse_metadata(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in body.splitlines():
        match = META_RE.match(line.strip())
        if match:
            key, value = match.groups()
            if key in REQUIRED_BODY_FIELDS:
                result[key] = value.strip()
    missing = [key for key in REQUIRED_BODY_FIELDS if not result.get(key)]
    if missing:
        fail("Missing PR metadata field(s): " + ", ".join(missing))
    return result


def git_changed_paths(base_sha: str, head_sha: str) -> list[str]:
    for sha, label in ((base_sha, "base"), (head_sha, "head")):
        if not FULL_SHA.fullmatch(sha):
            fail(f"{label} SHA is not a full 40-character lowercase Git SHA: {sha!r}")
    try:
        output = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"git diff failed:\n{exc.output}")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def matches(path: str, patterns: list[str]) -> bool:
    return any(
        path == pattern
        or path.startswith(pattern.rstrip("/") + "/")
        or fnmatch.fnmatch(path, pattern)
        for pattern in patterns
    )


def require_str(obj: dict[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{where}.{key} must be a non-empty string.")
    return value.strip()


def require_list(obj: dict[str, Any], key: str, where: str, *, nonempty: bool = False) -> list[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        fail(f"{where}.{key} must be a list.")
    if nonempty and not value:
        fail(f"{where}.{key} must not be empty.")
    return value


def validate_contract(path: Path) -> dict[str, Any]:
    if path.is_absolute() or ".." in path.parts:
        fail("Verified-Delivery-Contract must be a repository-relative path.")
    if not path.is_file():
        fail(f"Verified Delivery Contract does not exist: {path}")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Verified Delivery Contract is not valid JSON: {exc}")
    if not isinstance(contract, dict):
        fail("Verified Delivery Contract root must be an object.")

    if contract.get("schema_version") != 1:
        fail("contract.schema_version must equal 1.")
    require_str(contract, "contract_id", "contract")
    if not isinstance(contract.get("revision"), int) or contract["revision"] < 1:
        fail("contract.revision must be an integer >= 1.")
    if contract.get("status") != "frozen":
        fail("contract.status must be 'frozen' for a governed PR.")
    if contract.get("project_slug") != "factored-ai-data-hackathon-2026":
        fail("contract.project_slug is not the Factored project.")
    if contract.get("risk_class") != "high_assurance":
        fail("contract.risk_class must be 'high_assurance'.")

    baseline = contract.get("baseline")
    if not isinstance(baseline, dict):
        fail("contract.baseline must be an object.")
    if baseline.get("repository") != REPO:
        fail(f"contract.baseline.repository must be {REPO!r}.")
    baseline_sha = require_str(baseline, "commit_sha", "contract.baseline")
    if not FULL_SHA.fullmatch(baseline_sha):
        fail("contract.baseline.commit_sha must be a full lowercase 40-character SHA.")

    scope = contract.get("scope")
    if not isinstance(scope, dict):
        fail("contract.scope must be an object.")
    require_list(scope, "deliverables", "contract.scope", nonempty=True)
    require_list(scope, "non_goals", "contract.scope")
    allowed = require_list(scope, "allowed_write_surfaces", "contract.scope", nonempty=True)
    forbidden = require_list(scope, "forbidden_write_surfaces", "contract.scope")
    protected = require_list(scope, "protected_verifier_surfaces", "contract.scope", nonempty=True)
    for name, values in (("allowed_write_surfaces", allowed), ("forbidden_write_surfaces", forbidden), ("protected_verifier_surfaces", protected)):
        if not all(isinstance(item, str) and item.strip() for item in values):
            fail(f"contract.scope.{name} must contain only non-empty strings.")

    acceptance = require_list(contract, "acceptance", "contract", nonempty=True)
    ids: set[str] = set()
    for index, item in enumerate(acceptance):
        where = f"contract.acceptance[{index}]"
        if not isinstance(item, dict):
            fail(f"{where} must be an object.")
        rid = require_str(item, "requirement_id", where)
        if rid in ids:
            fail(f"Duplicate acceptance requirement_id: {rid}")
        ids.add(rid)
        require_str(item, "condition", where)
        require_str(item, "verification_class", where)
        evidence = require_list(item, "required_evidence", where, nonempty=True)
        if not all(isinstance(entry, str) and entry.strip() for entry in evidence):
            fail(f"{where}.required_evidence must contain non-empty strings.")

    assurance = contract.get("assurance")
    if not isinstance(assurance, dict):
        fail("contract.assurance must be an object.")
    if assurance.get("exact_candidate_required") is not True:
        fail("contract.assurance.exact_candidate_required must be true.")
    if assurance.get("builder_cannot_self_certify_independent_assurance") is not True:
        fail("contract.assurance.builder_cannot_self_certify_independent_assurance must be true.")
    if assurance.get("acceptance_changes_require_revision") is not True:
        fail("contract.assurance.acceptance_changes_require_revision must be true.")
    if assurance.get("owner_acceptance_required") is not True:
        fail("contract.assurance.owner_acceptance_required must be true.")
    if assurance.get("repeat_failure_stop_after") != 3:
        fail("contract.assurance.repeat_failure_stop_after must equal 3.")
    if assurance.get("heldout_policy") not in {"none", "protected", "protected_and_adversarial"}:
        fail("contract.assurance.heldout_policy is invalid.")

    roles = contract.get("roles")
    if not isinstance(roles, dict):
        fail("contract.roles must be an object.")
    builder = require_str(roles, "builder", "contract.roles")
    auditor = require_str(roles, "independent_auditor", "contract.roles")
    require_str(roles, "owner", "contract.roles")
    if builder.casefold() == auditor.casefold():
        fail("Builder and independent auditor must not be the same declared role/identity.")

    return contract


def main() -> int:
    try:
        event = load_event()
        pr = event.get("pull_request")
        if not isinstance(pr, dict):
            fail("This check requires a pull_request event.")

        body = pr.get("body") or ""
        meta = parse_metadata(body)
        head_sha = str(pr.get("head", {}).get("sha", "")).lower()
        base_sha = str(pr.get("base", {}).get("sha", "")).lower()
        draft = bool(pr.get("draft"))

        if not FULL_SHA.fullmatch(head_sha):
            fail(f"GitHub PR head SHA is invalid: {head_sha!r}")
        if meta["Candidate-Head-SHA"].lower() != head_sha:
            fail(
                "Candidate-Head-SHA must equal the current PR head exactly. "
                f"body={meta['Candidate-Head-SHA']!r}, actual={head_sha}"
            )

        contract_path = Path(meta["Verified-Delivery-Contract"])
        contract = validate_contract(contract_path)
        baseline_sha = contract["baseline"]["commit_sha"]
        if baseline_sha != base_sha:
            fail(
                "Frozen contract baseline must equal the current PR base SHA. "
                f"contract={baseline_sha}, PR base={base_sha}. "
                "Rebase/retargeting requires an explicit contract revision."
            )

        changed = git_changed_paths(base_sha, head_sha)
        scope = contract["scope"]
        allowed: list[str] = scope["allowed_write_surfaces"]
        forbidden: list[str] = scope["forbidden_write_surfaces"]
        protected: list[str] = scope["protected_verifier_surfaces"]

        unauthorized = [path for path in changed if not matches(path, allowed)]
        if unauthorized:
            fail("Changed paths outside contract allowed_write_surfaces:\n- " + "\n- ".join(unauthorized))

        forbidden_changes = [path for path in changed if matches(path, forbidden)]
        if forbidden_changes:
            fail("Changed paths intersect contract forbidden_write_surfaces:\n- " + "\n- ".join(forbidden_changes))

        protected_changes = [path for path in changed if matches(path, protected)]
        disposition = meta["Verifier-Change-Disposition"]
        if protected_changes and disposition.casefold() in {"none", "n/a", "na", "not-applicable"}:
            fail(
                "Protected verifier surface changed without governed disposition:\n- "
                + "\n- ".join(protected_changes)
            )
        if protected_changes and not (
            disposition.startswith("contract-revision:")
            or disposition.startswith("audited-repair:")
            or disposition.startswith("governance-bootstrap:")
        ):
            fail(
                "Protected verifier changes require Verifier-Change-Disposition to begin "
                "with contract-revision:, audited-repair:, or governance-bootstrap:."
            )

        release_intent = meta["Release-Intent"].casefold()
        if release_intent not in {"none", "prototype", "submission", "pilot", "production"}:
            fail("Release-Intent must be one of none|prototype|submission|pilot|production.")

        evidence = meta["Evidence-Status"].casefold()
        audit = meta["Independent-Audit"].casefold()
        owner = meta["Owner-Acceptance"].casefold()

        if draft:
            if evidence not in {"pending", "complete"}:
                fail("Draft PR Evidence-Status must be pending or complete.")
            if audit not in {"pending", "complete"} and not audit.startswith("not-required:"):
                fail("Draft PR Independent-Audit must be pending, complete, or not-required:<reason>.")
            if owner not in {"pending", "accepted"}:
                fail("Draft PR Owner-Acceptance must be pending or accepted.")
        else:
            if evidence != "complete":
                fail("Ready-for-review PRs require Evidence-Status: complete.")
            if audit != "complete" and not audit.startswith("not-required:"):
                fail("Ready-for-review PRs require Independent-Audit: complete or not-required:<reason>.")
            if owner != "accepted":
                fail("Ready-for-review PRs require Owner-Acceptance: accepted.")

        print("VERIFIED DELIVERY PREFLIGHT PASS")
        print(f"contract={contract['contract_id']} revision={contract['revision']}")
        print(f"base={base_sha}")
        print(f"candidate={head_sha}")
        print(f"draft={draft}")
        print(f"changed_paths={len(changed)} protected_changes={len(protected_changes)}")
        print(
            "NOTE: this repository-visible gate does not itself certify independent audit, "
            "held-out integrity, or owner identity. Canonical evidence remains in Continuity."
        )
        return 0
    except Failure as exc:
        print(f"VERIFIED DELIVERY PREFLIGHT FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
