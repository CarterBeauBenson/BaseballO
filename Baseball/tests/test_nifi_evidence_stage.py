#!/usr/bin/env python3
"""Regression tests for the dependency-aware NiFi evidence stage boundary."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "pipeline" / "run-nifi-evidence-stage.py"


class NiFiEvidenceStageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.state = self.root / "state"
        self.repository.mkdir()
        self.state.mkdir()
        (self.repository / "input.txt").write_text("one\n", encoding="utf-8")
        (self.repository / "success.py").write_text(
            "from pathlib import Path\nPath('ran.txt').write_text('yes', encoding='utf-8')\n",
            encoding="utf-8",
        )
        (self.repository / "failure.py").write_text(
            "raise SystemExit(7)\n", encoding="utf-8"
        )
        self.contract = self.repository / "contract.json"
        self.contract.write_text(
            json.dumps(
                {
                    "contractVersion": 1,
                    "stages": {
                        "success": {
                            "description": "test success",
                            "schedule": "1 hour",
                            "cacheable": True,
                            "timeoutSeconds": 30,
                            "command": ["{python}", "success.py"],
                            "dependencies": ["input.txt", "success.py"],
                        },
                        "failure": {
                            "description": "test failure",
                            "schedule": "1 hour",
                            "cacheable": True,
                            "timeoutSeconds": 30,
                            "command": ["{python}", "failure.py"],
                            "dependencies": ["input.txt", "failure.py"],
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_stage(self, stage: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repository-root",
                str(self.repository),
                "--contract",
                str(self.contract),
                "--state-root",
                str(self.state),
                "--stage",
                stage,
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        return completed, json.loads(completed.stdout)

    def test_unchanged_success_is_skipped_and_dependency_change_reruns(self) -> None:
        first, first_manifest = self.run_stage("success")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first_manifest["status"], "succeeded")

        second, second_manifest = self.run_stage("success")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second_manifest["status"], "skipped")
        self.assertEqual(
            first_manifest["dependencyFingerprint"],
            second_manifest["dependencyFingerprint"],
        )

        (self.repository / "input.txt").write_text("two\n", encoding="utf-8")
        third, third_manifest = self.run_stage("success")
        self.assertEqual(third.returncode, 0, third.stderr)
        self.assertEqual(third_manifest["status"], "succeeded")
        self.assertNotEqual(
            first_manifest["dependencyFingerprint"],
            third_manifest["dependencyFingerprint"],
        )

    def test_failure_writes_manifest_and_quarantine_log(self) -> None:
        completed, manifest = self.run_stage("failure")
        self.assertEqual(completed.returncode, 7)
        self.assertEqual(manifest["status"], "failed")
        quarantine = Path(manifest["quarantinePath"])
        self.assertTrue((quarantine / "manifest.json").is_file())
        self.assertTrue((quarantine / "stage.log").is_file())
        latest = (
            self.state
            / "pipeline"
            / "evidence"
            / "nifi"
            / "failure"
            / "latest-success.json"
        )
        self.assertFalse(latest.exists())


if __name__ == "__main__":
    unittest.main()
