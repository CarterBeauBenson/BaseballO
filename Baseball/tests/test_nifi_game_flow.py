#!/usr/bin/env python3
"""Offline contract tests for the staged NiFi per-game RDF flow."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVER = ROOT / "scripts" / "pipeline" / "archive-and-queue-game-json.py"
STAGE = ROOT / "scripts" / "pipeline" / "process-nifi-rdf-stage.ps1"
FIXTURE = ROOT / "data" / "raw" / "game-566279.json"
POWERSHELL = shutil.which("powershell")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(POWERSHELL, "Windows PowerShell is required")
class NiFiGameFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.local_root = Path(self.temporary.name) / "local"
        self.state_root = self.local_root / "state"
        self.state_root.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def archive(self) -> tuple[dict, Path]:
        completed = subprocess.run(
            [
                sys.executable,
                str(ARCHIVER),
                "--input",
                str(FIXTURE),
                "--state-root",
                str(self.state_root),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        )
        result = json.loads(completed.stdout)
        queued = Path(result["semanticWorkRequest"])
        staging = self.state_root / "pipeline" / "staging" / "rdf-requests"
        staging.mkdir(parents=True, exist_ok=True)
        request = staging / queued.name
        queued.replace(request)
        return result, request

    def invoke_assess(self, request: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["BASEBALLO_LOCAL_ROOT"] = str(self.local_root)
        return subprocess.run(
            [
                str(POWERSHELL),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(STAGE),
                "-Stage",
                "assess",
                "-RequestJson",
                str(request),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=environment,
            check=False,
        )

    def test_archive_is_immutable_and_assessment_emits_evidence(self) -> None:
        result, request_path = self.archive()
        raw_path = Path(result["rawPath"])
        self.assertEqual(sha256(raw_path), sha256(FIXTURE))
        self.assertEqual(result["status"], "queued-for-rdf")

        completed = self.invoke_assess(request_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        manifest = json.loads(completed.stdout)
        self.assertEqual(manifest["stage"], "assess")
        self.assertEqual(manifest["status"], "succeeded")
        self.assertEqual(manifest["result"]["action"], "rebuild")
        request = json.loads(request_path.read_text(encoding="utf-8-sig"))
        self.assertEqual(request["stages"]["assess"]["status"], "succeeded")

    def test_raw_hash_mismatch_is_quarantined(self) -> None:
        result, request_path = self.archive()
        request = json.loads(request_path.read_text(encoding="utf-8-sig"))
        request["rawSha256"] = "0" * 64
        request_path.write_text(json.dumps(request), encoding="utf-8")

        completed = self.invoke_assess(request_path)
        self.assertNotEqual(completed.returncode, 0)
        quarantine = (
            self.state_root
            / "pipeline"
            / "quarantine"
            / "nifi-rdf"
            / "566279"
            / result["pipelineRunId"]
            / "assess"
        )
        manifest = json.loads((quarantine / "manifest.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(manifest["status"], "failed")
        self.assertIn("raw hash", manifest["error"])
        self.assertTrue((quarantine / "request.json").is_file())
        self.assertTrue((quarantine / "stage.log").is_file())


if __name__ == "__main__":
    unittest.main()
