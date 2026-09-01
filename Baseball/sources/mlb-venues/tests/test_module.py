#!/usr/bin/env python3
"""Focused non-network tests for the MLB venues authority module."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph


MODULE = Path(__file__).resolve().parents[1]
PREPARE = MODULE / "mapping" / "prepare-context.py"
MAPPING = MODULE / "mapping" / "mlb-venues.rml.ttl"
SHACL = MODULE / "shacl" / "authoritative.ttl"
FIXTURE = MODULE / "schema" / "fixtures" / "one-venue.json"


def load_prepare_module():
    spec = importlib.util.spec_from_file_location("mlb_venues_prepare", PREPARE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load prepare-context.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_prepare_module()


class MlbVenuesModuleTests(unittest.TestCase):
    def build(self, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        records = prepare.response_records(payload, "2025", hashlib.sha256(raw).hexdigest())
        return records

    def test_fixture_emits_each_accepted_extension_grain(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        (
            venues,
            names,
            dimensions,
            coordinates,
            capacities,
            surfaces,
            roofs,
            open_roofs,
        ) = self.build(payload)
        self.assertEqual(len(venues), 1)
        self.assertEqual(len(names), 1)
        self.assertEqual(len(dimensions), 5)
        self.assertEqual(coordinates[0]["latitude"], "1.25")
        self.assertEqual(capacities[0]["capacity"], "40000")
        self.assertEqual(surfaces[0]["surfaceType"], "Grass")
        self.assertEqual(roofs[0]["roofType"], "Retractable")
        self.assertEqual(open_roofs, [])

    def test_open_roof_uses_information_only_branch(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["venues"][0]["fieldInfo"]["roofType"] = "Open"
        records = self.build(payload)
        self.assertEqual(records[6], [])
        self.assertEqual(records[7][0]["roofType"], "Open")

    def test_partial_coordinates_fail_before_rml(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del payload["venues"][0]["location"]["defaultCoordinates"]["longitude"]
        with self.assertRaises(ValueError):
            self.build(payload)

    def test_unknown_surface_code_fails_before_rml(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["venues"][0]["fieldInfo"]["turfType"] = "Provider Surprise"
        with self.assertRaises(ValueError):
            self.build(payload)

    def test_mapping_and_shacl_parse_as_turtle(self):
        self.assertGreater(len(Graph().parse(MAPPING, format="turtle")), 0)
        self.assertGreater(len(Graph().parse(SHACL, format="turtle")), 0)


if __name__ == "__main__":
    unittest.main()
