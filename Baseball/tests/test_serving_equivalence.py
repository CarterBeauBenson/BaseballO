#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "prove-serving-equivalence.py"
SPEC = importlib.util.spec_from_file_location("baseballo_serving_equivalence", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
EQUIVALENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EQUIVALENCE)


class ServingEquivalenceTests(unittest.TestCase):
    def test_signature_distinguishes_sequence_but_preserves_multiset(self) -> None:
        first = {
            "head": {"vars": ["player", "hits"]},
            "results": {"bindings": [
                {"player": {"type": "uri", "value": "p1"}, "hits": {"type": "literal", "value": "2"}},
                {"player": {"type": "uri", "value": "p2"}, "hits": {"type": "literal", "value": "1"}},
            ]},
        }
        second = {
            "head": first["head"],
            "results": {"bindings": list(reversed(first["results"]["bindings"]))},
        }
        left = EQUIVALENCE.result_signature(first, "left")
        right = EQUIVALENCE.result_signature(second, "right")
        self.assertEqual(left["rowMultisetSha256"], right["rowMultisetSha256"])
        self.assertNotEqual(left["rowSequenceSha256"], right["rowSequenceSha256"])

    def test_signature_preserves_unbound_and_rdf_term_metadata(self) -> None:
        payload = {
            "head": {"vars": ["label", "optional"]},
            "results": {"bindings": [{
                "label": {"type": "literal", "value": "Suárez", "xml:lang": "es"}
            }]},
        }
        signature = EQUIVALENCE.result_signature(payload, "unicode")
        self.assertEqual(signature["rowCount"], 1)
        self.assertRegex(signature["rowSequenceSha256"], r"^[0-9a-f]{64}$")

    def test_response_metadata_requires_the_requested_layer(self) -> None:
        payload = {"meta": {"layer": "authoritative", "corpusFingerprint": "f" * 64}}
        self.assertEqual(
            EQUIVALENCE.response_metadata(payload, "authoritative", "probe")["corpusFingerprint"],
            "f" * 64,
        )
        with self.assertRaisesRegex(EQUIVALENCE.EquivalenceError, "did not execute"):
            EQUIVALENCE.response_metadata(payload, "materialized", "probe")

    def test_option_signature_compares_complete_ordered_options(self) -> None:
        first = {
            "options": [
                {"value": "p1", "label": "Player One"},
                {"value": "p2", "label": "Player Two"},
            ]
        }
        second = {"options": list(reversed(first["options"]))}
        left = EQUIVALENCE.option_signature(first, "left")
        right = EQUIVALENCE.option_signature(second, "right")
        self.assertEqual(left["rowMultisetSha256"], right["rowMultisetSha256"])
        self.assertNotEqual(left["rowSequenceSha256"], right["rowSequenceSha256"])

    def test_option_metadata_requires_fingerprint_and_candidate_build(self) -> None:
        authoritative = {"layer": "authoritative", "corpusFingerprint": "a" * 64}
        candidate = {
            "layer": "materialized",
            "servingBuildId": "build-1",
            "corpusFingerprint": "a" * 64,
        }
        self.assertIsNone(
            EQUIVALENCE.option_response_metadata(
                authoritative, "authoritative", "options"
            )["buildId"]
        )
        self.assertEqual(
            EQUIVALENCE.option_response_metadata(
                candidate, "materialized", "options"
            )["buildId"],
            "build-1",
        )


if __name__ == "__main__":
    unittest.main()
