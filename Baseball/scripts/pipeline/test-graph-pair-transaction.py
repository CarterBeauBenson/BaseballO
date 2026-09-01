#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("graph-pair-transaction.py")


def load_module():
    spec = importlib.util.spec_from_file_location("baseballo_graph_pair_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load graph-pair transaction")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


transaction = load_module()


class MemoryStore:
    def __init__(self, graphs=None):
        self.graphs = dict(graphs or {})

    def get(self, graph):
        return self.graphs.get(graph)

    def put(self, graph, body):
        self.graphs[graph] = body

    def delete(self, graph):
        self.graphs.pop(graph, None)


class GraphPairTransactionTests(unittest.TestCase):
    def test_failure_restores_both_prior_graphs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = transaction.graph_names("1")
            old_authoritative = b"<urn:a> <urn:p> <urn:old> .\n"
            old_index = b"<urn:i> <urn:p> <urn:old> .\n"
            store = MemoryStore({names["authoritative"]: old_authoritative, names["index"]: old_index})
            transaction.prepare(store, root, "1", "a" * 32)
            store.put(names["authoritative"], b"<urn:a> <urn:p> <urn:new> .\n")
            store.delete(names["index"])
            result = transaction.restore(store, root, "1", "a" * 32, "index-failure")
            self.assertEqual(result["state"], "restored")
            self.assertTrue(transaction.isomorphic(transaction.nt_graph(store.get(names["authoritative"])), transaction.nt_graph(old_authoritative)))
            self.assertTrue(transaction.isomorphic(transaction.nt_graph(store.get(names["index"])), transaction.nt_graph(old_index)))

    def test_restore_removes_graph_that_was_previously_absent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = transaction.graph_names("2")
            store = MemoryStore({names["authoritative"]: b"<urn:a> <urn:p> <urn:old> .\n"})
            transaction.prepare(store, root, "2", "b" * 32)
            store.put(names["index"], b"<urn:i> <urn:p> <urn:new> .\n")
            transaction.restore(store, root, "2", "b" * 32, "partial-write")
            self.assertIsNone(store.get(names["index"]))

    def test_recovery_commits_only_after_immutable_promotion_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = "c" * 32
            names = transaction.graph_names("3")
            store = MemoryStore({names["authoritative"]: b"<urn:a> <urn:p> <urn:old> .\n"})
            transaction.prepare(store, root, "3", run)
            store.put(names["authoritative"], b"<urn:a> <urn:p> <urn:new> .\n")
            promotion = root / "pipeline" / "evidence" / "nifi" / "game-promotion" / "3" / f"{run}.json"
            transaction.atomic_json(promotion, {"artifactType": "baseball-nifi-game-promotion"})
            result = transaction.recover(store, root, "3")
            self.assertEqual(result["committedRuns"], [run])
            manifest = json.loads((root / "pipeline" / "work" / "graph-pair-transactions" / "3" / run / "transaction.json").read_text())
            self.assertEqual(manifest["state"], "committed")
            self.assertIsNotNone(store.get(names["authoritative"]))


if __name__ == "__main__":
    unittest.main()
