#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts" / "pipeline" / "materialize-serving-layer.py"
SPEC = importlib.util.spec_from_file_location("baseballo_dsq_sql_materializer", MATERIALIZER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def load_entries() -> list[dict[str, object]]:
    return MODULE.load_dsq_entries(
        json.loads(MODULE.DSQ_MATERIALIZATIONS.read_text(encoding="utf-8")),
        json.loads(MODULE.ADVANCED_CATALOG.read_text(encoding="utf-8")),
        json.loads(MODULE.ADVANCED_REDUCERS.read_text(encoding="utf-8")),
    )


class DsqSqlMaterializationTests(unittest.TestCase):
    def test_catalog_covers_every_approved_static_dsq_exactly(self) -> None:
        entries = load_entries()
        self.assertEqual(len(entries), 56)
        self.assertEqual(sum(entry["kind"] == "advanced" for entry in entries), 17)
        self.assertEqual(sum(entry["kind"] == "canned" for entry in entries), 39)
        self.assertEqual(len({entry["id"] for entry in entries}), 56)
        self.assertEqual(len({entry["table"] for entry in entries}), 56)
        self.assertTrue(all(str(entry["table"]).startswith("dsq_") for entry in entries))

    def test_every_dsq_can_be_bound_to_one_exact_game_graph(self) -> None:
        graph = "https://w3id.org/baseball/graph/game/566279"
        for entry in load_entries():
            with self.subTest(query=entry["path"]):
                bounded = MODULE.bounded_query(
                    (ROOT / str(entry["path"])).read_text(encoding="utf-8"), graph
                )
                self.assertNotIn("GRAPH ?graph", bounded)
                self.assertNotIn("GRAPH ?indexGraph", bounded)
                self.assertIn("566279", bounded)
                execution = MODULE.bounded_dsq_query(
                    (ROOT / str(entry["executionPath"])).read_text(encoding="utf-8"),
                    graph,
                    str(entry["executionLayer"]),
                )
                expected_graph = (
                    "https://w3id.org/baseball/graph/query-index/game/566279"
                    if entry["executionLayer"] == "indexed"
                    else graph
                )
                self.assertIn(f"GRAPH <{expected_graph}>", execution)

    def test_each_dsq_gets_an_isolated_filterable_sql_table(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE game_dimension (graph_iri TEXT PRIMARY KEY) STRICT")
        connection.execute("INSERT INTO game_dimension VALUES ('https://example.test/graph/1')")
        entry = {
            "id": "hits-by-player",
            "table": "dsq_test_hits_by_player",
            "variables": ["player", "playerLabel", "hits"],
            "reducer": {
                "mode": "additive",
                "dimensions": ["player", "playerLabel"],
                "sums": ["hits"],
            },
        }
        state: dict[str, object] = {"variables": None, "count": 0}
        recorded: list[tuple[str, str]] = []
        payload = {
            "head": {"vars": ["player", "playerLabel", "hits"]},
            "results": {
                "bindings": [
                    {
                        "player": {"type": "uri", "value": "https://example.test/player/1"},
                        "playerLabel": {"type": "literal", "value": "José Test"},
                        "hits": {
                            "type": "literal",
                            "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                            "value": "2",
                        },
                    }
                ]
            },
        }

        inserted = MODULE.insert_dsq_payload(
            connection,
            entry,
            "https://example.test/graph/1",
            payload,
            state,
            lambda table, row: recorded.append((table, row)),
        )

        self.assertEqual(inserted, 1)
        self.assertEqual(state["count"], 1)
        self.assertEqual(
            connection.execute(
                "SELECT player,playerLabel,hits FROM dsq_test_hits_by_player"
            ).fetchone(),
            ("https://example.test/player/1", "José Test", "2"),
        )
        self.assertEqual(recorded[0][0], "dsq_test_hits_by_player")
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list('dsq_test_hits_by_player')")
        }
        self.assertIn("dsq_test_hits_by_player_player_idx", indexes)
        self.assertIn("dsq_test_hits_by_player_playerLabel_idx", indexes)

    def test_nifi_backfill_is_isolated_from_rdf_and_route_admission(self) -> None:
        contract = json.loads(
            (ROOT / "serving" / "dsq-nifi" / "flow-contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["materialization"]["queryCount"], 56)
        self.assertEqual(
            contract["materialization"]["tableOwnership"],
            "one-dedicated-table-per-dsq",
        )
        self.assertEqual(
            contract["materialization"]["nightlyOwner"],
            "mlb-game schedule-batch post-promotion materialization",
        )
        self.assertTrue(contract["failurePolicy"]["authoritativeRdfUnaffected"])
        self.assertTrue(contract["failurePolicy"]["queryIndexRdfUnaffected"])
        self.assertTrue(contract["failurePolicy"]["sourceLanesUnaffected"])
        self.assertTrue(contract["failurePolicy"]["priorServingPointerUnaffected"])
        self.assertTrue(contract["failurePolicy"]["uiAdmissionUnaffected"])

    def test_table_rejects_a_binding_outside_the_sparql_head(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE game_dimension (graph_iri TEXT PRIMARY KEY) STRICT")
        connection.execute("INSERT INTO game_dimension VALUES ('g')")
        entry = {
            "id": "bad",
            "table": "dsq_test_bad",
            "variables": ["player"],
            "reducer": {"mode": "detail", "dimensions": [], "sums": []},
        }
        with self.assertRaisesRegex(ValueError, "undeclared binding"):
            MODULE.insert_dsq_payload(
                connection,
                entry,
                "g",
                {
                    "head": {"vars": ["player"]},
                    "results": {"bindings": [{"hidden": {"type": "literal", "value": "x"}}]},
                },
                {"variables": None, "count": 0},
                lambda _table, _row: None,
            )


if __name__ == "__main__":
    unittest.main()
