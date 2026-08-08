#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "scripts" / "pipeline" / "queue-ready-corpus-audits.py"
STAGE = ROOT / "scripts" / "pipeline" / "process-nifi-corpus-stage.py"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NifiCorpusFlowTests(unittest.TestCase):
    def test_promotions_queue_one_corpus_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            pipeline = state / "pipeline"
            submitted = datetime.now(timezone.utc) - timedelta(minutes=1)
            run_id = "submission-1"
            games = [{"gamePk": "1", "sha256": "a" * 64}, {"gamePk": "2", "sha256": "b" * 64}]
            write_json(pipeline / "manifests" / "submissions" / f"{run_id}.json", {
                "artifactType": "nifi-game-corpus-submission", "runId": run_id,
                "submittedAtUtc": submitted.isoformat(), "uniqueGameCount": 2,
                "auditRequested": True, "auditScope": "test", "games": games,
            })
            promotion_root = pipeline / "evidence" / "nifi" / "game-promotion"
            write_json(promotion_root / "1" / "one.json", {
                "artifactType": "baseball-nifi-game-promotion", "gamePk": "1",
                "rawSha256": "a" * 64, "promotedAtUtc": datetime.now(timezone.utc).isoformat(),
            })
            first = subprocess.run([sys.executable, str(QUEUE), "--state-root", str(state)], text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertFalse((pipeline / "inbox" / "corpus-audits" / f"{run_id}.json").exists())
            write_json(promotion_root / "2" / "two.json", {
                "artifactType": "baseball-nifi-game-promotion", "gamePk": "2",
                "rawSha256": "b" * 64, "promotedAtUtc": datetime.now(timezone.utc).isoformat(),
            })
            second = subprocess.run([sys.executable, str(QUEUE), "--state-root", str(state)], text=True, capture_output=True)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            request_path = pipeline / "inbox" / "corpus-audits" / f"{run_id}.json"
            request_hash = sha(request_path)
            subprocess.run([sys.executable, str(QUEUE), "--state-root", str(state)], check=True, capture_output=True)
            self.assertEqual(sha(request_path), request_hash)

    def test_completion_requires_and_fingerprints_all_stage_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            pipeline = state / "pipeline"
            run_id = "submission-2"
            submission_path = pipeline / "manifests" / "submissions" / f"{run_id}.json"
            write_json(submission_path, {"artifactType": "nifi-game-corpus-submission", "runId": run_id, "auditStatus": "queued"})
            stages = {}
            for short, full in (("canned", "canned-query-audit"), ("advanced", "advanced-query-audit"), ("equivalence", "authoritative-index-equivalence"), ("benchmark", "benchmark-evidence")):
                evidence = pipeline / "evidence" / "nifi" / full / "runs" / f"{short}.json"
                write_json(evidence, {"artifactType": "baseball-nifi-stage-evidence", "stage": full, "status": "succeeded"})
                stages[short] = {"status": "succeeded", "evidenceManifest": str(evidence), "evidenceManifestSha256": sha(evidence)}
            request_path = pipeline / "staging" / "corpus-audits" / f"{run_id}.json"
            write_json(request_path, {
                "artifactType": "baseball-nifi-corpus-audit-request", "contractVersion": 1,
                "submissionRunId": run_id, "submissionManifest": str(submission_path),
                "corpusSha256": "c" * 64, "gameCount": 8, "auditScope": "test", "stages": stages,
            })
            completed = subprocess.run([sys.executable, str(STAGE), "--stage", "complete", "--request", str(request_path), "--state-root", str(state)], text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            completion = pipeline / "evidence" / "nifi" / "corpus-completion" / f"{run_id}.json"
            self.assertTrue(completion.is_file())
            self.assertFalse(request_path.exists())
            self.assertEqual(json.loads(submission_path.read_text())["auditStatus"], "audited")


if __name__ == "__main__":
    unittest.main()
