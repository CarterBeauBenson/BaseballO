from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "batted_runner_context", ROOT / "scripts/pipeline/prepare-rml-context.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = Namespace("https://baseballontology.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
SHAPE = Namespace("https://w3id.org/baseball/shacl/")
EX = Namespace("https://example.org/")


class BattedRunnerContainmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plays = json.loads((ROOT / "data/raw/game-566279.json").read_bytes())["liveData"]["plays"]["allPlays"]

    def test_steal_then_single_links_only_single_resolutions(self):
        links = MODULE.batted_runner_resolution_links(self.plays[23], "23")
        self.assertEqual([(x["runnerIndex"], x["resolutionKind"]) for x in links], [("1", "reach"), ("2", "score")])
        self.assertEqual({x["playId"] for x in links}, {"234cbb96-ffd3-47c2-b9e6-60d556d920cd"})

    def test_double_play_reuses_distinct_existing_out_rows(self):
        links = MODULE.batted_runner_resolution_links(self.plays[15], "15")
        self.assertEqual([(x["runnerIndex"], x["resolutionKind"]) for x in links], [("0", "out"), ("1", "out")])

    def test_mixed_error_row_is_not_assigned_by_index_alone(self):
        links = MODULE.batted_runner_resolution_links(self.plays[40], "40")
        self.assertEqual([x["runnerIndex"] for x in links], ["0", "2"])

    def test_noncontact_and_uncaught_third_strike_produce_no_links(self):
        for game, pa in [("822693", 36), ("823826", 78)]:
            doc = json.loads((ROOT / f"data/raw/samples/2026-08-25/{game}.json").read_bytes())
            self.assertEqual(MODULE.batted_runner_resolution_links(doc["liveData"]["plays"]["allPlays"][pa], str(pa)), [])
        self.assertEqual(MODULE.batted_runner_resolution_links(self.plays[4], "4"), [])

    def test_incomplete_unknown_or_ambiguous_source_does_not_gain_membership(self):
        for condition in ("incomplete", "unknown", "duplicate-index", "missing-index", "null-placeholder", "boolean-index"):
            with self.subTest(condition=condition):
                play = copy.deepcopy(self.plays[2])
                terminal = [event for event in play["playEvents"] if event.get("isPitch") is True][-1]
                if condition == "incomplete":
                    play["about"]["isComplete"] = False
                elif condition == "unknown":
                    play["result"]["eventType"] = "unreviewed-contact-result"
                elif condition == "duplicate-index":
                    play["playEvents"].append({"index": terminal["index"]})
                elif condition == "missing-index":
                    del terminal["index"]
                elif condition == "null-placeholder":
                    play["runners"][0]["movement"]["isOut"] = None
                else:
                    play["runners"][0]["details"]["playIndex"] = True
                self.assertEqual(MODULE.batted_runner_resolution_links(play, "2"), [])

    def test_shacl_requires_shared_pa_and_one_contact_play(self):
        profile = Graph().parse(ROOT / "sources/mlb-game/shacl/authoritative.ttl", format="turtle")
        shapes = Graph()
        # Exercise the new source shape without duplicating its constraints in Python.
        for triple in profile.triples((SHAPE.BattedRunnerResolutionContainmentShape, None, None)):
            shapes.add(triple)
            if triple[1] == Namespace("http://www.w3.org/ns/shacl#").sparql:
                for nested in profile.triples((triple[2], None, None)):
                    shapes.add(nested)
        data = Graph()
        for triple in [(EX.play, RDF.type, BASE.BattedBallPlayProcess), (EX.pa, RDF.type, BASE.PlateAppearance), (EX.resolution, RDF.type, BASE.RunnerResolutionProcess), (EX.play, BFO.BFO_0000132, EX.pa), (EX.resolution, BFO.BFO_0000132, EX.pa), (EX.play, BFO.BFO_0000117, EX.resolution)]:
            data.add(triple)
        self.assertTrue(validate(data, shacl_graph=shapes)[0])
        data.remove((EX.resolution, BFO.BFO_0000132, EX.pa))
        data.add((EX.resolution, BFO.BFO_0000132, EX.otherPA))
        self.assertFalse(validate(data, shacl_graph=shapes)[0])
        data.remove((EX.resolution, BFO.BFO_0000132, EX.otherPA))
        data.add((EX.resolution, BFO.BFO_0000132, EX.pa))
        data.add((EX.otherPlay, RDF.type, BASE.BattedBallPlayProcess))
        data.add((EX.otherPlay, BFO.BFO_0000132, EX.pa))
        data.add((EX.otherPlay, BFO.BFO_0000117, EX.resolution))
        self.assertFalse(validate(data, shacl_graph=shapes)[0])


if __name__ == "__main__":
    unittest.main()
