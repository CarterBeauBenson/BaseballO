from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = MODULE_ROOT / "nifi" / "prepare-quarantine-replay.py"
SPEC = importlib.util.spec_from_file_location("baseballo_quarantine_replay", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


PROOF_GAMES = ("831445", "823685", "831470", "823298", "823523")


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def input_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_quarantine(state: Path, game_pk: str, run_id: str) -> Path:
    path = state / "pipeline" / "quarantine" / "mlb-game" / game_pk / run_id / "input.json"
    write_json(
        path,
        {
            "gamePk": int(game_pk),
            "gameData": {"status": {"abstractGameState": "Final"}},
        },
    )
    return path


def add_promotion(state: Path, game_pk: str, raw_sha256: str, name: str = "promotion.json") -> Path:
    path = (
        state
        / "pipeline"
        / "evidence"
        / "nifi"
        / "game-promotion"
        / game_pk
        / name
    )
    write_json(
        path,
        {
            "artifactType": "baseball-nifi-game-promotion",
            "gamePk": game_pk,
            "promotedAtUtc": "2099-01-01T00:00:00Z",
            "rawSha256": raw_sha256,
            "authoritativeTripleCount": 10,
            "queryIndexTripleCount": 4,
        },
    )
    return path


class QuarantineReplayTests(unittest.TestCase):
    def contract(self, root: Path) -> Path:
        path = root / "contract.json"
        write_json(
            path,
            {
                "artifactType": "baseballo-nifi-source-flow-contract",
                "sourceModule": "mlb-game",
                "quarantineReplay": {
                    "proofGames": [
                        {"gamePk": game_pk, "reason": "fixture"}
                        for game_pk in PROOF_GAMES
                    ]
                },
            },
        )
        return path

    def test_plan_emits_five_proofs_and_one_gate_before_remainder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            for position, game_pk in enumerate((*PROOF_GAMES, "900001")):
                add_quarantine(state, game_pk, f"run{position}")

            submission = MODULE.create_plan(state, self.contract(state))

            self.assertEqual(submission["proofCount"], 5)
            self.assertEqual(submission["remainderCount"], 1)
            self.assertEqual([item["phase"] for item in submission["records"]], [
                "proof", "proof", "proof", "proof", "proof", "gate"
            ])

    def test_certified_replay_lane_selects_five_current_inputs_for_later_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            contract = self.contract(state)
            initial_paths = {
                game_pk: add_quarantine(state, game_pk, f"initial{position}")
                for position, game_pk in enumerate(PROOF_GAMES)
            }
            initial = MODULE.create_plan(state, contract)
            for game_pk, path in initial_paths.items():
                add_promotion(state, game_pk, input_hash(path))
                path.unlink()
            certified = MODULE.require_proof(state, Path(initial["planPath"]))

            for position in range(6):
                add_quarantine(state, str(900100 + position), f"later{position}")
            later = MODULE.create_plan(state, contract)
            later_plan = MODULE.read_object(Path(later["planPath"]))

            self.assertEqual(later["proofCount"], 5)
            self.assertEqual(later["remainderCount"], 1)
            self.assertEqual(
                later_plan["proofBasis"]["selectionMode"],
                "current-inputs-after-prior-certified-proof",
            )
            self.assertEqual(
                later_plan["proofBasis"]["priorProofEvidence"],
                str(Path(initial["planPath"]).parent / "proof.json"),
            )
            self.assertEqual(
                later_plan["proofBasis"]["priorProofEvidence"],
                certified["planPath"].replace("plan.json", "proof.json"),
            )

    def test_later_replay_still_blocks_without_a_certified_prior_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            for position in range(6):
                add_quarantine(state, str(900200 + position), f"later{position}")

            with self.assertRaisesRegex(ValueError, "no prior certified five-game"):
                MODULE.create_plan(state, self.contract(state))

    def test_remainder_is_blocked_until_all_exact_proof_hashes_are_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            paths = {
                game_pk: add_quarantine(state, game_pk, f"run{position}")
                for position, game_pk in enumerate((*PROOF_GAMES, "900001"))
            }
            submission = MODULE.create_plan(state, self.contract(state))
            plan = Path(submission["planPath"])
            for game_pk in PROOF_GAMES[:-1]:
                add_promotion(state, game_pk, input_hash(paths[game_pk]))

            with self.assertRaisesRegex(RuntimeError, PROOF_GAMES[-1]):
                MODULE.require_proof(state, plan)

            add_promotion(state, PROOF_GAMES[-1], input_hash(paths[PROOF_GAMES[-1]]))
            proof = MODULE.require_proof(state, plan)
            remainder = MODULE.emit_remainder(state, plan)

            self.assertEqual(len(proof["promotions"]), 5)
            self.assertEqual([item["gamePk"] for item in remainder["records"]], ["900001"])

    def test_open_plan_can_reemit_only_its_same_hash_proof_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            for position, game_pk in enumerate(PROOF_GAMES):
                add_quarantine(state, game_pk, f"original{position}")
            submission = MODULE.create_plan(state, self.contract(state))
            for position, item in enumerate(submission["records"][:-1]):
                duplicate = add_quarantine(state, item["gamePk"], f"retry{position}")
                duplicate.write_bytes(Path(item["inputPath"]).read_bytes())

            retry = MODULE.emit_latest_proof(state)

            self.assertEqual(retry["planPath"], submission["planPath"])
            self.assertEqual(retry["proofCount"], 5)
            self.assertEqual(retry["pendingProofCount"], 5)
            self.assertEqual(retry["completedProofCount"], 0)
            proof_records = [item for item in retry["records"] if item["phase"] == "proof"]
            self.assertEqual([item["phase"] for item in retry["records"][-1:]], ["gate"])
            self.assertEqual(
                {item["inputSha256"] for item in proof_records},
                {item["inputSha256"] for item in submission["records"][:-1]},
            )

    def test_proof_retry_reissues_only_gate_after_exact_promotions_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            paths = {
                game_pk: add_quarantine(state, game_pk, f"run{position}")
                for position, game_pk in enumerate(PROOF_GAMES)
            }
            submission = MODULE.create_plan(state, self.contract(state))
            for game_pk, path in paths.items():
                add_promotion(state, game_pk, input_hash(path))
                path.unlink()

            retry = MODULE.emit_latest_proof(state)

            self.assertEqual(retry["proofCount"], 5)
            self.assertEqual(retry["pendingProofCount"], 0)
            self.assertEqual(retry["completedProofCount"], 5)
            self.assertEqual(retry["records"], [
                {"phase": "gate", "planPath": submission["planPath"]}
            ])

    def test_remainder_retry_emits_only_inputs_still_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            paths = {
                game_pk: add_quarantine(state, game_pk, f"run{position}")
                for position, game_pk in enumerate((*PROOF_GAMES, "900001", "900002"))
            }
            submission = MODULE.create_plan(state, self.contract(state))
            for game_pk in PROOF_GAMES:
                add_promotion(state, game_pk, input_hash(paths[game_pk]))
            MODULE.require_proof(state, Path(submission["planPath"]))
            paths["900001"].unlink()

            retry = MODULE.emit_latest_remainder(state)

            self.assertEqual(retry["replayCount"], 1)
            self.assertEqual(retry["existingResolutionCount"], 0)
            self.assertEqual(
                [(item["phase"], item["gamePk"]) for item in retry["records"]],
                [("remainder", "900002")],
            )

    def test_resolution_removes_only_game_local_inputs_after_matching_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            paths = {
                game_pk: add_quarantine(state, game_pk, f"run{position}")
                for position, game_pk in enumerate(PROOF_GAMES)
            }
            older = add_quarantine(state, PROOF_GAMES[0], "older")
            submission = MODULE.create_plan(state, self.contract(state))
            selected = next(
                item for item in submission["records"] if item.get("gamePk") == PROOF_GAMES[0]
            )
            selected_path = Path(selected["inputPath"])
            add_promotion(state, PROOF_GAMES[0], selected["inputSha256"])

            result = MODULE.resolve_input(
                state,
                Path(submission["planPath"]),
                PROOF_GAMES[0],
                selected_path,
                selected["inputSha256"],
            )

            self.assertGreaterEqual(len(result["removedInputs"]), 1)
            self.assertFalse(selected_path.exists())
            self.assertFalse(older.exists())
            self.assertTrue((selected_path.parent / "resolution.json").is_file())
            self.assertTrue(paths[PROOF_GAMES[1]].is_file())


if __name__ == "__main__":
    unittest.main()
