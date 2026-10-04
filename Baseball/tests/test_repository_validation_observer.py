#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "record-repository-validation.py"
SPEC = importlib.util.spec_from_file_location("baseballo_repository_observer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
OBSERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OBSERVER)


class RepositoryValidationObserverTests(unittest.TestCase):
    def setUp(self):
        self.clean_state = {'commit': 'a' * 40, 'dirty': False}
        self.state_patch = patch.object(OBSERVER, 'repository_state', return_value=self.clean_state)
        self.state_mock = self.state_patch.start()
        self.addCleanup(self.state_patch.stop)

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

    def test_unfinished_edits_defer_without_starting_validation(self) -> None:
        self.state_mock.return_value = {**self.clean_state, 'dirty': True}
        evidence, exit_code, _ = self.run_fixture(7)
        self.assertEqual(exit_code, 0)
        self.assertEqual(evidence['status'], 'deferred')
        self.assertFalse(evidence['validationAttempted'])
        self.assertIsNone(evidence['exitCode'])
        self.assertEqual(Path(evidence['stdoutPath']).read_bytes(), b'')
        self.assertEqual(evidence['deferredReason'], 'uncommitted-repository-changes')

    def test_edits_or_commit_during_run_preserve_logs_but_do_not_certify(self) -> None:
        for observed in ({**self.clean_state, 'dirty': True}, {'commit': 'b' * 40, 'dirty': False}):
            for result in (0, 7):
                with self.subTest(observed=observed, result=result):
                    self.state_mock.side_effect = [self.clean_state, observed]
                    evidence, exit_code, _ = self.run_fixture(result)
                    self.assertEqual(exit_code, 0)
                    self.assertEqual(evidence['status'], 'deferred')
                    self.assertTrue(evidence['validationAttempted'])
                    self.assertEqual(evidence['exitCode'], result)
                    self.assertIn(b'fixture output', Path(evidence['stdoutPath']).read_bytes())
                    self.assertEqual(evidence['repositoryAfter'], observed)


if __name__ == "__main__":
    unittest.main()
