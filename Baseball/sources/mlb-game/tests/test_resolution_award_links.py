from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("resolution_context", ROOT / "scripts/pipeline/prepare-rml-context.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = Namespace("https://baseballontology.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
CCO = Namespace("https://www.commoncoreontologies.org/")
SHAPE = Namespace("https://w3id.org/baseball/shacl/")
DATA = Namespace("https://baseballontology.org/data/")


def fixture(game, pa):
    path = ROOT / ("data/raw/game-566279.json" if game == "566279" else f"data/raw/samples/2026-08-25/{game}.json")
    return json.loads(path.read_bytes())["liveData"]["plays"]["allPlays"][pa]


class ResolutionAwardContextTests(unittest.TestCase):
    def test_safe_destination_and_separate_steal_then_score(self):
        double = MODULE.runner_resolution_links(fixture("566279", 2), "2")
        self.assertEqual([(x["resolutionKind"], x["baseCode"]) for x in double["adjudicatedBaseLinks"]], [("reach", "2B")])
        mixed = MODULE.runner_resolution_links(fixture("566279", 23), "23")
        self.assertEqual([(x["runnerIndex"], x["baseCode"]) for x in mixed["adjudicatedBaseLinks"]], [("0", "2B"), ("1", "1B")])
        self.assertEqual(mixed["runnerResolutionLinks"][2]["resolutionKind"], "score")
        self.assertEqual(mixed["awardResolutionLinks"], [])

    def test_direct_and_forced_awards_keep_distinct_existing_resolutions(self):
        for game, pa, rows in [("822693", 6, ["1", "0"]), ("823016", 39, ["2", "1", "0"])]:
            with self.subTest(game=game):
                links = MODULE.runner_resolution_links(fixture(game, pa), str(pa))
                self.assertEqual([x["runnerIndex"] for x in links["awardResolutionLinks"]], rows)
                self.assertEqual(len({x["runnerId"] for x in links["awardResolutionLinks"]}), len(rows))

    def test_balk_before_walk_is_not_award_completion(self):
        links = MODULE.runner_resolution_links(fixture("566279", 12), "12")
        self.assertEqual([x["runnerIndex"] for x in links["awardResolutionLinks"]], ["1"])
        self.assertEqual([x["baseCode"] for x in links["adjudicatedBaseLinks"]], ["2B", "1B"])

    def test_unknown_is_not_out_or_destination(self):
        play = fixture("823826", 78)
        links = MODULE.runner_resolution_links(play, "78")
        self.assertNotIn("3", [x["runnerIndex"] for x in links["runnerResolutionLinks"]])
        play = fixture("566279", 2)
        play["runners"][0]["movement"]["end"] = None
        links = MODULE.runner_resolution_links(play, "2")
        self.assertEqual(links["adjudicatedBaseLinks"], [])
        self.assertEqual(len(links["runnerResolutionLinks"]), 1)

    def test_ambiguous_award_evidence_withholds_links(self):
        for condition in ["incomplete", "duplicate-event", "review", "bad-call", "batter-duplicate", "unknown-batter", "boolean-index"]:
            with self.subTest(condition=condition):
                play = fixture("823016", 39)
                if condition == "incomplete": play["about"]["isComplete"] = False
                elif condition == "duplicate-event": play["playEvents"].append({"index": 1})
                elif condition == "review": play["about"]["hasReview"] = True
                elif condition == "bad-call": play["playEvents"][-1]["details"]["call"]["code"] = "B"
                elif condition == "batter-duplicate": play["runners"].append(copy.deepcopy(play["runners"][-1]))
                elif condition == "unknown-batter": play["runners"][-1]["movement"]["isOut"] = None
                else: play["runners"][-1]["details"]["playIndex"] = True
                self.assertEqual(MODULE.runner_resolution_links(play, "39")["awardResolutionLinks"], [])

    def test_gap_mixed_reason_or_overshoot_never_infers_forced_chain(self):
        for condition in ["gap", "mixed", "overshoot", "post-mismatch", "duplicate-start"]:
            with self.subTest(condition=condition):
                play = fixture("823016", 39)
                if condition == "gap": del play["runners"][1]
                elif condition == "mixed": play["runners"][1]["details"]["eventType"] = "wild_pitch"
                elif condition == "overshoot": play["runners"][1]["movement"]["end"] = "3B"
                elif condition == "post-mismatch": play["matchup"]["postOnSecond"]["id"] = 1
                else: play["runners"].append(copy.deepcopy(play["runners"][1]))
                links = MODULE.runner_resolution_links(play, "39")["awardResolutionLinks"]
                self.assertEqual([x["runnerId"] for x in links], ["681047"])


class ResolutionAwardShaclTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile = Graph().parse(ROOT / "sources/mlb-game/shacl/authoritative.ttl")
        cls.shapes = Graph()
        pending = [SHAPE.ResolvedRunnerLinksShape, SHAPE.AdjudicatedBaseLinksShape,
                   SHAPE.AwardResolutionLinksShape, SHAPE.LinkedBaserunningBaseCodeShape]
        visited = set()
        while pending:
            node = pending.pop()
            if node in visited: continue
            visited.add(node)
            for triple in profile.triples((node, None, None)):
                cls.shapes.add(triple)
                obj = triple[2]
                if isinstance(obj, BNode) or str(obj).startswith(str(SHAPE)): pending.append(obj)

    def graph(self):
        g = Graph()
        self.rr = DATA['game/1/runner-resolution/advance/6/0']
        self.pa = DATA['game/1/plate-appearance/6']
        self.award = URIRef(str(self.pa) + '/result')
        self.runner = DATA['player/1']
        self.base = DATA['venue/2/artifact/base/2B']
        self.field = DATA['venue/2/baseball-field']
        self.judgment = URIRef(str(self.rr) + '/judgment')
        self.decision = URIRef(str(self.rr) + '/decision')
        self.record = URIRef(str(self.rr) + '/record')
        code = URIRef(str(self.base) + '/identifier/source-base-code')
        for triple in [
            (code, RDF.type, CCO.ont00000649), (code, CCO.ont00001916, self.base),
            (code, CCO.ont00001765, Literal('2B')),
            (self.rr, RDF.type, BASE.RunnerResolutionProcess), (self.rr, RDF.type, BASE.SafeProcess),
            (self.rr, BASE.hasResolvedRunner, self.runner), (self.runner, RDF.type, CCO.ont00001262),
            (self.rr, BFO.BFO_0000057, self.runner), (self.rr, BFO.BFO_0000132, self.pa),
            (self.pa, RDF.type, BASE.PlateAppearance), (self.rr, BASE.hasAdjudicatedBase, self.base),
            (self.base, RDF.type, BASE.Base), (self.rr, CCO.ont00001918, self.field),
            (self.rr, BASE.settlesAwardFrom, self.award), (self.award, RDF.type, BASE.WalkProcess),
            (self.award, BFO.BFO_0000132, self.pa), (self.award, CCO.ont00001918, self.field),
            (self.rr, BFO.BFO_0000117, self.judgment), (self.judgment, CCO.ont00001986, self.decision),
            (self.decision, CCO.ont00001808, self.rr), (self.record, RDF.type, BASE.BaseballEventRecord),
            (self.record, CCO.ont00001808, self.rr), (self.record, CCO.ont00001808, self.decision),
        ]: g.add(triple)
        return g

    def test_valid_safe_and_counted_scoring_award(self):
        g = self.graph()
        self.assertTrue(validate(g, shacl_graph=self.shapes)[0])
        g.remove((self.rr, RDF.type, BASE.SafeProcess))
        g.remove((self.rr, BASE.hasAdjudicatedBase, None))
        g.add((self.rr, RDF.type, BASE.RunProcess))
        self.assertTrue(validate(g, shacl_graph=self.shapes)[0])

    def test_contract_rejects_wrong_bearer_base_award_and_missing_evidence(self):
        for condition in ["missing-runner", "two-runners", "not-participant", "wrong-field", "home", "other-pa", "wrong-award", "missing-destination", "missing-record", "out-with-base"]:
            with self.subTest(condition=condition):
                g = self.graph()
                if condition == "missing-runner": g.remove((self.rr, BASE.hasResolvedRunner, None))
                elif condition == "two-runners": g.add((self.rr, BASE.hasResolvedRunner, DATA['player/2']))
                elif condition == "not-participant": g.remove((self.rr, BFO.BFO_0000057, None))
                elif condition in {"wrong-field", "home"}:
                    g.remove((self.rr, BASE.hasAdjudicatedBase, None))
                    other = DATA['venue/9/artifact/base/2B' if condition == 'wrong-field' else 'venue/2/artifact/home-plate']
                    g.add((other, RDF.type, BASE.Base)); g.add((self.rr, BASE.hasAdjudicatedBase, other))
                elif condition == "other-pa": g.remove((self.award, BFO.BFO_0000132, None))
                elif condition == "wrong-award": g.remove((self.award, RDF.type, BASE.WalkProcess)); g.add((self.award, RDF.type, BASE.BalkProcess))
                elif condition == "missing-destination": g.remove((self.rr, BASE.hasAdjudicatedBase, None))
                elif condition == "missing-record": g.remove((self.record, CCO.ont00001808, self.decision))
                else: g.remove((self.rr, RDF.type, BASE.SafeProcess)); g.add((self.rr, RDF.type, BASE.OutProcess))
                self.assertFalse(validate(g, shacl_graph=self.shapes)[0])


if __name__ == "__main__":
    unittest.main()
