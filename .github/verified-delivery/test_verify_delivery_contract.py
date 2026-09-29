from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_delivery_contract.py"
SPEC = importlib.util.spec_from_file_location("verify_delivery_contract", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

BASE = "1" * 40
HEAD = "2" * 40


def contract() -> dict:
    return {
        "schema_version": 1,
        "contract_id": "TEST-CONTRACT",
        "revision": 1,
        "status": "frozen",
        "project_slug": "factored-ai-data-hackathon-2026",
        "risk_class": "high_assurance",
        "baseline": {
            "repository": "SplitzHappen/factored-hackathon-2026-proof-of-one",
            "commit_sha": BASE,
        },
        "scope": {
            "deliverables": ["bounded change"],
            "non_goals": ["no unrelated change"],
            "allowed_write_surfaces": ["app/**", ".github/**"],
            "forbidden_write_surfaces": ["data/raw/**"],
            "protected_verifier_surfaces": [".github/workflows/**", "tests/**"],
        },
        "roles": {
            "owner": "owner",
            "builder": "builder-family",
            "independent_auditor": "auditor-family",
        },
        "acceptance": [
            {
                "requirement_id": "REQ-001",
                "condition": "bounded condition",
                "verification_class": "test",
                "required_evidence": ["deterministic result"],
            }
        ],
        "assurance": {
            "exact_candidate_required": True,
            "builder_cannot_self_certify_independent_assurance": True,
            "acceptance_changes_require_revision": True,
            "owner_acceptance_required": True,
            "heldout_policy": "protected_and_adversarial",
            "repeat_failure_stop_after": 3,
        },
    }


def body(
    *,
    head: str = HEAD,
    evidence: str = "pending",
    audit: str = "pending",
    owner: str = "pending",
    verifier: str = "none",
) -> str:
    return f"""Verified-Delivery-Contract: contract.json
Candidate-Head-SHA: {head}
Evidence-Status: {evidence}
Independent-Audit: {audit}
Owner-Acceptance: {owner}
Verifier-Change-Disposition: {verifier}
Release-Intent: none
"""


@contextmanager
def event_env(event: dict):
    old_cwd = os.getcwd()
    old_event = os.environ.get("GITHUB_EVENT_PATH")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "contract.json").write_text(json.dumps(contract()), encoding="utf-8")
        event_path = root / "event.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        os.chdir(root)
        os.environ["GITHUB_EVENT_PATH"] = str(event_path)
        try:
            yield root
        finally:
            os.chdir(old_cwd)
            if old_event is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = old_event


def event(*, draft: bool, pr_body: str) -> dict:
    return {
        "pull_request": {
            "draft": draft,
            "body": pr_body,
            "base": {"sha": BASE},
            "head": {"sha": HEAD},
        }
    }


class VerifiedDeliveryGateTests(unittest.TestCase):
    def run_main(self, ev: dict, changed: list[str]) -> int:
        with event_env(ev):
            with mock.patch.object(gate, "git_changed_paths", return_value=changed):
                return gate.main()

    def test_draft_pending_state_can_pass(self):
        self.assertEqual(
            self.run_main(event(draft=True, pr_body=body()), ["app/example.py"]),
            0,
        )

    def test_wrong_candidate_head_fails(self):
        self.assertEqual(
            self.run_main(
                event(draft=True, pr_body=body(head="3" * 40)),
                ["app/example.py"],
            ),
            1,
        )

    def test_ready_pr_cannot_have_pending_evidence(self):
        self.assertEqual(
            self.run_main(
                event(
                    draft=False,
                    pr_body=body(audit="complete", owner="accepted"),
                ),
                ["app/example.py"],
            ),
            1,
        )

    def test_ready_pr_requires_completed_gates(self):
        self.assertEqual(
            self.run_main(
                event(
                    draft=False,
                    pr_body=body(
                        evidence="complete",
                        audit="complete",
                        owner="accepted",
                    ),
                ),
                ["app/example.py"],
            ),
            0,
        )

    def test_protected_verifier_change_requires_disposition(self):
        self.assertEqual(
            self.run_main(
                event(draft=True, pr_body=body()),
                [".github/workflows/ci.yml"],
            ),
            1,
        )

    def test_protected_verifier_change_accepts_governed_revision(self):
        self.assertEqual(
            self.run_main(
                event(
                    draft=True,
                    pr_body=body(verifier="contract-revision:R2"),
                ),
                [".github/workflows/ci.yml"],
            ),
            0,
        )

    def test_forbidden_surface_fails(self):
        self.assertEqual(
            self.run_main(event(draft=True, pr_body=body()), ["data/raw/secret.csv"]),
            1,
        )

    def test_builder_cannot_be_independent_auditor(self):
        with event_env(event(draft=True, pr_body=body())):
            payload = contract()
            payload["roles"]["independent_auditor"] = payload["roles"]["builder"]
            Path("contract.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(gate.Failure):
                gate.validate_contract(Path("contract.json"))


if __name__ == "__main__":
    unittest.main()
