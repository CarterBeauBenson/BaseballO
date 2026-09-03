#!/usr/bin/env python3
"""Focused regression check for static SPARQL source isolation."""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_repository.py"
SPEC = importlib.util.spec_from_file_location("baseballo_validate_repository", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SparqlSourceScopeTests(unittest.TestCase):
    def test_every_static_query_has_exact_scope_and_single_source_graph_guard(self) -> None:
        modules, source_ids = VALIDATOR.validate_source_module_contract()
        self.assertEqual(modules, 7)
        self.assertGreater(VALIDATOR.validate_query_source_scopes(source_ids), 0)

    def test_reviewed_runner_is_the_exact_exception_to_intrinsic_scoping(self) -> None:
        catalog = json.loads(
            (ROOT / "sparql" / "source-scope-catalog.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(catalog["runtimeBinders"]), 1)
        binder = catalog["runtimeBinders"][0]
        routing = json.loads((ROOT / binder["queryRegistry"]).read_text(encoding="utf-8"))
        registered = {ROOT / route["authoritative"] for route in routing["routes"]}
        self.assertEqual(len(registered), 19)
        unguarded = set()
        for entry in catalog["entries"]:
            if entry["category"] != "single-source":
                continue
            for pattern in entry["patterns"]:
                for path in (ROOT / "sparql").glob(pattern):
                    query = path.read_text(encoding="utf-8")
                    if re.search(r"\bGRAPH\s+\?graph\s*\{", query, re.IGNORECASE) and not re.search(
                        r"FILTER\s*\(\s*STRSTARTS\s*\(\s*STR\s*\(\s*\?graph\s*\)",
                        query,
                        re.IGNORECASE,
                    ):
                        unguarded.add(path)
        self.assertTrue(unguarded)
        self.assertTrue(unguarded.issubset(registered))
        runner = (ROOT / binder["runner"]).read_text(encoding="utf-8")
        self.assertIn("VALUES ?graph { $values }", runner)
        self.assertIn(binder["graphPrefix"], runner)


if __name__ == "__main__":
    unittest.main()
