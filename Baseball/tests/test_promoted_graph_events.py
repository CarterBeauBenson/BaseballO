#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "emit-promoted-graph-event.py"
SPEC = importlib.util.spec_from_file_location("baseballo_promoted_events", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PromotedGraphEventTests(unittest.TestCase):
    def source_promotion(self, state: Path) -> Path:
        path = state / "pipeline" / "evidence" / "mlb-people" / "person-1" / "run" / "promotion.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "artifactType": "baseballo-source-graph-promotion",
                    "contractVersion": 1,
                    "sourceModule": "mlb-people",
                    "scopeKey": "person-1",
                    "pipelineRunId": "a" * 32,
                    "promotedAtUtc": "2026-09-03T12:00:00Z",
                    "authoritativeGraph": "https://w3id.org/baseball/graph/authority/mlb-people/person-1",
                    "tripleCount": 20,
                    "rdfSha256": "b" * 64,
                    "replacedPriorGraph": False,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_source_promotion_emits_idempotent_immutable_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            promotion = self.source_promotion(state)
            first = MODULE.emit(state, promotion)
            second = MODULE.emit(state, promotion)
            self.assertEqual(first["status"], "created")
            self.assertEqual(second["status"], "already-present")
            self.assertEqual(first["eventId"], second["eventId"])
            event = json.loads(Path(first["eventPath"]).read_text(encoding="utf-8"))
            self.assertEqual(event["sourceModule"], "mlb-people")
            self.assertEqual(event["authoritativeTripleCount"], 20)
            self.assertEqual(event["promotionEvidenceSha256"], MODULE.sha256_file(promotion))

    def test_game_event_retains_both_promoted_graphs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            promotion = state / "pipeline" / "evidence" / "nifi" / "game-promotion" / "1" / "tx.json"
            promotion.parent.mkdir(parents=True)
            promotion.write_text(
                json.dumps(
                    {
                        "artifactType": "baseball-nifi-game-promotion",
                        "contractVersion": 1,
                        "gamePk": "1",
                        "pipelineRunId": "c" * 32,
                        "transactionRunId": "d" * 32,
                        "promotedAtUtc": "2026-09-03T12:00:00Z",
                        "authoritativeGraph": "https://w3id.org/baseball/graph/game/1",
                        "authoritativeTripleCount": 100,
                        "queryIndexGraph": "https://w3id.org/baseball/graph/query-index/game/1",
                        "queryIndexTripleCount": 15,
                        "queryIndexManifest": "manifest.json",
                        "queryIndexManifestSha256": "e" * 64,
                    }
                ),
                encoding="utf-8",
            )
            result = MODULE.emit(state, promotion)
            event = json.loads(Path(result["eventPath"]).read_text(encoding="utf-8"))
            self.assertEqual(event["sourceModule"], "mlb-game")
            self.assertEqual(event["scopeKey"], "game-1")
            self.assertEqual(event["queryIndexGraph"], "https://w3id.org/baseball/graph/query-index/game/1")

    def test_wrong_source_graph_namespace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            promotion = self.source_promotion(state)
            value = json.loads(promotion.read_text(encoding="utf-8"))
            value["authoritativeGraph"] = "https://w3id.org/baseball/graph/authority/mlb-venues/1"
            promotion.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.EventError, "registered namespace"):
                MODULE.emit(state, promotion)

    def test_evidence_outside_state_evidence_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            outside = Path(temporary) / "promotion.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.EventError, "must be a file under"):
                MODULE.emit(state, outside)


if __name__ == "__main__":
    unittest.main()
