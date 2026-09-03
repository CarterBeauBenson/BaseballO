#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER_PATH = ROOT / "scripts" / "pipeline" / "materialize-authority-serving.py"
EMITTER_PATH = ROOT / "scripts" / "pipeline" / "emit-promoted-graph-event.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MATERIALIZER = load_module("baseballo_authority_materializer_test", MATERIALIZER_PATH)
EMITTER = load_module("baseballo_authority_event_emitter_test", EMITTER_PATH)


class AuthorityServingMaterializerTests(unittest.TestCase):
    def promotion(self, state: Path, run: str, name: str) -> dict[str, object]:
        path = state / "pipeline" / "evidence" / "mlb-people" / "person-1" / run / "promotion.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "artifactType": "baseballo-source-graph-promotion",
                    "contractVersion": 1,
                    "sourceModule": "mlb-people",
                    "scopeKey": "person-1",
                    "pipelineRunId": run,
                    "promotedAtUtc": f"2026-09-03T12:00:0{1 if run.startswith('a') else 2}Z",
                    "authoritativeGraph": "https://w3id.org/baseball/graph/authority/mlb-people/person-1",
                    "tripleCount": 20,
                    "rdfSha256": ("b" if run.startswith("a") else "c") * 64,
                    "replacedPriorGraph": not run.startswith("a"),
                    "testName": name,
                }
            ),
            encoding="utf-8",
        )
        return EMITTER.emit(state, path)

    def args(self, state: Path, no_promote: bool = False) -> argparse.Namespace:
        return argparse.Namespace(
            state_root=state,
            endpoint="http://example.invalid/query",
            timeout=5,
            max_events=100,
            full_rebuild=False,
            no_promote=no_promote,
            retain_builds=3,
        )

    def test_event_build_is_promoted_and_correction_replaces_graph_partition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            first_event = self.promotion(state, "a" * 32, "First Name")
            current_name = ["Eugenio Suárez"]

            def fake_sparql(_endpoint: str, query: str, _timeout: int):
                if "Generated authority query: people-proper-names" in query:
                    return {
                        "head": {"vars": ["authorityGraph", "entity", "nameICE", "nameText"]},
                        "results": {
                            "bindings": [
                                {
                                    "authorityGraph": {"type": "uri", "value": "https://w3id.org/baseball/graph/authority/mlb-people/person-1"},
                                    "entity": {"type": "uri", "value": "https://baseballontology.org/data/person/1"},
                                    "nameICE": {"type": "uri", "value": "https://baseballontology.org/data/person/1/name/full"},
                                    "nameText": {"type": "literal", "value": current_name[0]},
                                }
                            ]
                        },
                    }
                return {"head": {"vars": []}, "results": {"bindings": []}}

            original = MATERIALIZER.sparql
            MATERIALIZER.sparql = fake_sparql
            try:
                first = MATERIALIZER.build(self.args(state))
                self.assertEqual(first["status"], "promoted")
                pointer_path = state / "serving" / "authority" / "current.json"
                pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
                with contextlib.closing(sqlite3.connect(pointer["databasePath"])) as connection:
                    self.assertEqual(
                        connection.execute("SELECT name_text FROM entity_name_fact").fetchall(),
                        [("Eugenio Suárez",)],
                    )
                self.assertTrue(
                    (state / "pipeline" / "evidence" / "serving-authority" / "events" / f"{first_event['eventId']}.json").is_file()
                )
                self.assertEqual(MATERIALIZER.build(self.args(state))["status"], "no-op")

                second_event = self.promotion(state, "d" * 32, "Corrected Name")
                current_name[0] = "Corrected Name"
                second = MATERIALIZER.build(self.args(state))
                self.assertEqual(second["sourceGraphCount"], 1)
                self.assertEqual(second["resultRowCount"], 1)
                pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
                with contextlib.closing(sqlite3.connect(pointer["databasePath"])) as connection:
                    self.assertEqual(
                        connection.execute("SELECT name_text FROM entity_name_fact").fetchall(),
                        [("Corrected Name",)],
                    )
                self.assertTrue(
                    (state / "pipeline" / "evidence" / "serving-authority" / "events" / f"{second_event['eventId']}.json").is_file()
                )
            finally:
                MATERIALIZER.sparql = original

    def test_query_failure_cannot_replace_current_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            self.promotion(state, "a" * 32, "Name")

            def fail_sparql(_endpoint: str, _query: str, _timeout: int):
                raise RuntimeError("simulated endpoint failure")

            original = MATERIALIZER.sparql
            MATERIALIZER.sparql = fail_sparql
            try:
                with self.assertRaisesRegex(RuntimeError, "simulated endpoint failure"):
                    MATERIALIZER.build(self.args(state))
            finally:
                MATERIALIZER.sparql = original
            self.assertFalse((state / "serving" / "authority" / "current.json").exists())
            self.assertEqual(
                list((state / "serving" / "authority" / "builds").glob("*.sqlite")), []
            )

    def test_contract_and_schema_are_exactly_compatible(self) -> None:
        contract, _catalog, _modules = MATERIALIZER.validate_contract()
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "authority.sqlite"
            with contextlib.closing(sqlite3.connect(database)) as connection:
                connection.executescript(MATERIALIZER.SCHEMA_PATH.read_text(encoding="utf-8"))
                for entry in contract["queries"]:
                    expected = [
                        "query_id",
                        "graph_iri",
                        "source_module",
                        *entry["constants"].keys(),
                        *(column["name"] for column in entry["columns"]),
                        "binding_json",
                        "binding_sha256",
                    ]
                    self.assertEqual(MATERIALIZER.table_columns(connection, entry["table"]), expected)


if __name__ == "__main__":
    unittest.main()
