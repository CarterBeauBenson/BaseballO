from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = MODULE_ROOT / "nifi" / "prepare-schedule-batch.py"
BATCH_ID = "a" * 32


class ScheduleBatchTests(unittest.TestCase):
    def run_script(self, state_root: Path, payload: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--state-root",
                str(state_root),
                "--batch-id",
                BATCH_ID,
                "--request-kind",
                "backfill",
                "--start-date",
                "2026-08-31",
                "--end-date",
                "2026-09-01",
            ],
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def payload(self) -> dict:
        return {
            "dates": [
                {
                    "date": "2026-08-31",
                    "games": [
                        {"gamePk": 900002, "status": {"abstractGameState": "Live"}},
                        {"gamePk": 900001, "status": {"abstractGameState": "Final"}},
                    ],
                },
                {
                    "date": "2026-09-01",
                    "games": [
                        {"gamePk": 900003, "status": {"abstractGameState": "Final"}}
                    ],
                },
            ]
        }

    def test_emits_only_final_games_and_persists_compact_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary)
            result = self.run_script(state_root, self.payload())

            self.assertEqual(result.returncode, 0, result.stdout)
            output = json.loads(result.stdout)
            self.assertEqual(
                [row["gamePk"] for row in output["games"]],
                ["900001", "900003"],
            )
            self.assertTrue(all(row["materializeMode"] == "deferred" for row in output["games"]))
            manifest_path = (
                state_root
                / "pipeline"
                / "control"
                / "mlb-game"
                / "batches"
                / f"{BATCH_ID}.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "pending")
            self.assertEqual(manifest["expectedGamePks"], ["900001", "900003"])
            self.assertNotIn("dates", manifest)

    def test_retry_is_idempotent_but_changed_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary)
            first = self.run_script(state_root, self.payload())
            second = self.run_script(state_root, self.payload())
            changed = self.payload()
            changed["dates"][0]["games"][1]["gamePk"] = 900004
            third = self.run_script(state_root, changed)

            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertEqual(second.returncode, 0, second.stdout)
            self.assertNotEqual(third.returncode, 0)
            self.assertIn("different evidence", third.stdout)


if __name__ == "__main__":
    unittest.main()
