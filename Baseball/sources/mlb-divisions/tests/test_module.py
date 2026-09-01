#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph

MODULE = Path(__file__).resolve().parents[1]
PREPARE = MODULE / "mapping" / "prepare-context.py"
MAPPING = MODULE / "mapping" / "mlb-divisions.rml.ttl"
SHACL = MODULE / "shacl" / "authoritative.ttl"
FIXTURE = MODULE / "schema" / "fixtures" / "division-one-record.json"


def load_prepare():
    spec = importlib.util.spec_from_file_location("mlb_divisions_prepare", PREPARE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load divisions context builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_prepare()


class MlbDivisionsModuleTests(unittest.TestCase):
    def test_division_contract_is_endpoint_specific(self):
        raw = FIXTURE.read_bytes()
        context = prepare.build_context(
            json.loads(raw.decode("utf-8")), endpoint_family="divisions",
            request_scope="fixture:divisions", response_sha256=hashlib.sha256(raw).hexdigest(),
        )
        self.assertEqual(context["_baseballO"]["sourceModule"], "mlb-divisions")
        self.assertEqual(
            {(row["entityKind"], row["entityId"]) for row in context["organizationRecords"]},
            {("division", "201"), ("league", "103")},
        )

    def test_executable_contracts_parse(self):
        self.assertGreater(len(Graph().parse(MAPPING, format="turtle")), 0)
        self.assertGreater(len(Graph().parse(SHACL, format="turtle")), 0)
        mapping = MAPPING.read_text(encoding="utf-8")
        self.assertNotIn("TeamSource", mapping)
        self.assertNotIn("SeasonSource", mapping)
        self.assertNotIn("teams-context.json", mapping)
        self.assertNotIn("leagues-context.json", mapping)

    def test_connector_rejects_other_endpoint_families(self):
        with self.assertRaises(prepare.ContractError):
            prepare.build_context(
                {"leagues": [{"id": 103}]}, endpoint_family="leagues",
                request_scope="fixture:leagues", response_sha256="0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
