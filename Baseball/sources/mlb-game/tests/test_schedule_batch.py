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
            stderr=subprocess.PIPE,
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
                        {
                            "gamePk": 900002,
                            "gameType": "R",
                            "officialDate": "2026-08-31",
                            "status": {"abstractGameState": "Live"},
                        },
                        {
                            "gamePk": 900001,
                            "gameType": "R",
                            "officialDate": "2026-08-31",
                            "status": {"abstractGameState": "Final"},
                        },
                    ],
                },
                {
                    "date": "2026-09-01",
                    "games": [
                        {
                            "gamePk": 900003,
                            "gameType": "R",
                            "officialDate": "2026-09-01",
                            "status": {"abstractGameState": "Final"},
                        }
                    ],
                },
            ]
        }

    def test_emits_only_final_games_and_persists_compact_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary)
            result = self.run_script(state_root, self.payload())

            self.assertEqual(result.returncode, 0, result.stderr)
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
            self.assertEqual(
                [(row["gamePk"], row["gameType"]) for row in manifest["games"]],
                [("900001", "R"), ("900003", "R")],
            )
            self.assertNotIn("dates", manifest)

    def test_retry_is_idempotent_but_changed_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary)
            first = self.run_script(state_root, self.payload())
            second = self.run_script(state_root, self.payload())
            changed = self.payload()
            changed["dates"][0]["games"][1]["gamePk"] = 900004
            third = self.run_script(state_root, changed)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(third.returncode, 0)
            self.assertIn("different evidence", third.stderr)
            self.assertEqual(json.loads(third.stdout), changed)

    def test_postponed_and_final_rows_become_one_game_with_revision_evidence(self) -> None:
        payload = {
            "dates": [
                {
                    "date": "2026-04-02",
                    "games": [
                        {
                            "gamePk": 824621,
                            "gameType": "R",
                            "officialDate": "2026-04-02",
                            "gameDate": "2026-04-02T23:10:00Z",
                            "rescheduleDate": "2026-04-03T20:10:00Z",
                            "status": {
                                "abstractGameState": "Final",
                                "detailedState": "Postponed",
                                "reason": "Inclement Weather",
                            },
                        }
                    ],
                },
                {
                    "date": "2026-04-03",
                    "games": [
                        {
                            "gamePk": 824621,
                            "gameType": "R",
                            "officialDate": "2026-04-03",
                            "gameDate": "2026-04-03T20:10:00Z",
                            "rescheduledFrom": "2026-04-02",
                            "status": {
                                "abstractGameState": "Final",
                                "detailedState": "Final",
                            },
                        }
                    ],
                },
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary)
            result = self.run_script(state_root, payload)

            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(len(output["games"]), 1)
            request = output["games"][0]
            self.assertEqual(request["gamePk"], "824621")
            self.assertEqual(request["scheduleDate"], "2026-04-03")
            evidence_path = Path(request["scheduleEvidencePath"])
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["gamePk"], "824621")
            self.assertEqual(len(evidence["postponements"]), 1)
            postponement = evidence["postponements"][0]
            self.assertEqual(postponement["originalDate"], "2026-04-02")
            self.assertEqual(postponement["revisedDate"], "2026-04-03")
            self.assertEqual(postponement["reason"], "Inclement Weather")


if __name__ == "__main__":
    unittest.main()
