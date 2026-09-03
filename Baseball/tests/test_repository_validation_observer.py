#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "record-repository-validation.py"
SPEC = importlib.util.spec_from_file_location("baseballo_repository_observer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
OBSERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OBSERVER)


class RepositoryValidationObserverTests(unittest.TestCase):
    def run_fixture(self, exit_code: int) -> tuple[dict, int, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        validator = root / "validator.py"
        validator.write_text(
            f"import sys\nprint('fixture output')\nprint('fixture error', file=sys.stderr)\nraise SystemExit({exit_code})\n",
            encoding="utf-8",
        )
        evidence, observed = OBSERVER.record_validation(
            root / "state", validator=validator, python=sys.executable, timeout_seconds=10
        )
        return evidence, observed, root

    def test_pass_records_hash_verified_immutable_logs(self) -> None:
        evidence, exit_code, _ = self.run_fixture(0)
        self.assertEqual(exit_code, 0)
        self.assertEqual(evidence["status"], "passed")
        persisted = json.loads(Path(evidence["evidencePath"]).read_text(encoding="utf-8"))
        stdout = Path(persisted["stdoutPath"]).read_bytes()
        stderr = Path(persisted["stderrPath"]).read_bytes()
        self.assertEqual(OBSERVER.sha256_bytes(stdout), persisted["stdoutSha256"])
        self.assertEqual(OBSERVER.sha256_bytes(stderr), persisted["stderrSha256"])
        self.assertTrue(persisted["failureDoesNotControlSourceLanes"])

    def test_failure_is_evidence_and_does_not_claim_a_pass(self) -> None:
        evidence, exit_code, root = self.run_fixture(7)
        self.assertEqual(exit_code, 7)
        self.assertEqual(evidence["status"], "failed")
        self.assertFalse(
            (root / "state" / "pipeline" / "locks" / "repository-validation.lock").exists()
        )


if __name__ == "__main__":
    unittest.main()
