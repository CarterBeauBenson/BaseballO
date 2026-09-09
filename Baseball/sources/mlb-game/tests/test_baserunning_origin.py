from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("origin_context", ROOT / "scripts/pipeline/prepare-rml-context.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = Namespace("https://baseballontology.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
CCO = Namespace("https://www.commoncoreontologies.org/")
SHAPE = Namespace("https://w3id.org/baseball/shacl/")
DATA = Namespace("https://baseballontology.org/data/")


def play(pa=12):
    return json.loads((ROOT / "data/raw/samples/2026-08-23/824315.json").read_bytes())["liveData"]["plays"]["allPlays"][pa]


class OriginContextTests(unittest.TestCase):
    def test_steal_and_later_single_keep_different_origins(self):
        for pa in (12, 64):
            links = MODULE.runner_resolution_links(play(pa), str(pa))
            self.assertEqual([(x['runnerIndex'], x['baseCode']) for x in links['baserunningOriginLinks']], [('0', '1B'), ('2', '2B')])
            self.assertEqual(links['baserunningOriginLinks'][0]['runnerId'], links['baserunningOriginLinks'][1]['runnerId'])
            self.assertEqual([(x['runnerIndex'], x['baseCode']) for x in links['adjudicatedBaseLinks']], [('0', '2B'), ('1', '1B'), ('2', '3B')])

    def test_null_batter_origin_never_becomes_home(self):
        links = MODULE.runner_resolution_links(play(), '12')['baserunningOriginLinks']
        self.assertNotIn('1', [x['runnerIndex'] for x in links])

    def test_unsupported_origin_is_withheld_without_affecting_earlier_steal(self):
        for condition in ['missing', 'disagreement', 'unknown-resolution', 'bad-runner', 'unsupported', 'boolean-index', 'missing-event', 'duplicate-event', 'duplicate-runner-row']:
            with self.subTest(condition=condition):
                p = play(); row = p['runners'][2]
                if condition == 'missing': row['movement']['originBase'] = None
                elif condition == 'disagreement': row['movement']['originBase'] = '1B'
                elif condition == 'unknown-resolution': row['movement']['isOut'] = None
                elif condition == 'bad-runner': row['details']['runner']['id'] = None
                elif condition == 'unsupported': row['movement']['start'] = row['movement']['originBase'] = 'HOME'
                elif condition == 'boolean-index': row['details']['playIndex'] = True
                elif condition == 'missing-event': row['details']['playIndex'] = 999
                elif condition == 'duplicate-event': p['playEvents'].append({'index': 8})
                else: p['runners'].append(copy.deepcopy(row))
                links = MODULE.runner_resolution_links(p, '12')['baserunningOriginLinks']
                self.assertEqual([(x['runnerIndex'], x['baseCode']) for x in links], [('0', '1B')])

    def test_incomplete_play_does_not_gain_origin(self):
        p = play(); p['about']['isComplete'] = False
        self.assertEqual(MODULE.runner_resolution_links(p, '12')['baserunningOriginLinks'], [])


class OriginShaclTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile = Graph().parse(ROOT / 'sources/mlb-game/shacl/authoritative.ttl')
        cls.shapes = Graph(); visited = set()
        pending = [SHAPE.BaserunningOriginLinksShape, SHAPE.LinkedBaserunningBaseCodeShape]
        while pending:
            node = pending.pop()
            if node in visited: continue
            visited.add(node)
            for triple in profile.triples((node, None, None)):
                cls.shapes.add(triple)
                if isinstance(triple[2], BNode) or str(triple[2]).startswith(str(SHAPE)): pending.append(triple[2])

    def graph(self):
        self.act = DATA['game/824315/runner-act/movement/12/2']
        self.rr = DATA['game/824315/runner-resolution/advance/12/2']
        self.pa = DATA['game/824315/plate-appearance/12']
        self.record = DATA['game/824315/runner-record/12/2']
        self.runner = DATA['player/677587']
        self.field = DATA['venue/1/baseball-field']
        self.base = DATA['venue/1/artifact/base/2B']
        self.code = URIRef(str(self.base) + '/identifier/source-base-code')
        g = Graph()
        for t in [(self.act, RDF.type, BASE.BaserunningAct), (self.act, BASE.hasBaserunningOriginBase, self.base),
                  (self.act, BFO.BFO_0000057, self.runner), (self.act, BFO.BFO_0000132, self.pa),
                  (self.act, CCO.ont00001918, self.field), (self.rr, RDF.type, BASE.RunnerResolutionProcess),
                  (self.rr, BFO.BFO_0000062, self.act), (self.rr, BASE.hasResolvedRunner, self.runner),
                  (self.rr, BFO.BFO_0000132, self.pa), (self.rr, CCO.ont00001918, self.field),
                  (self.pa, RDF.type, BASE.PlateAppearance), (self.runner, RDF.type, CCO.ont00001262),
                  (self.record, RDF.type, BASE.BaseballEventRecord), (self.record, CCO.ont00001808, self.act),
                  (self.record, CCO.ont00001808, self.rr), (self.base, RDF.type, BASE.Base),
                  (self.code, RDF.type, CCO.ont00000649), (self.code, CCO.ont00001916, self.base),
                  (self.code, CCO.ont00001765, Literal('2B'))]: g.add(t)
        return g

    def test_valid_origin_with_explicit_code_and_record(self):
        self.assertTrue(validate(self.graph(), shacl_graph=self.shapes)[0])

    def test_wrong_runner_context_origin_or_provenance_fails(self):
        for condition in ['runner', 'pa', 'field', 'no-record', 'no-code', 'conflicting-code', 'wrong-code', 'two-origins', 'wrong-class']:
            with self.subTest(condition=condition):
                g = self.graph()
                if condition == 'runner': g.remove((self.act, BFO.BFO_0000057, self.runner))
                elif condition == 'pa': g.remove((self.rr, BFO.BFO_0000132, self.pa))
                elif condition == 'field': g.remove((self.rr, CCO.ont00001918, self.field))
                elif condition == 'no-record': g.remove((self.record, CCO.ont00001808, self.act))
                elif condition == 'no-code': g.remove((self.code, CCO.ont00001765, None))
                elif condition == 'conflicting-code': g.add((self.code, CCO.ont00001765, Literal('3B')))
                elif condition == 'wrong-code': g.remove((self.code, CCO.ont00001765, None)); g.add((self.code, CCO.ont00001765, Literal('1B')))
                elif condition == 'two-origins': g.add((self.act, BASE.hasBaserunningOriginBase, DATA['venue/1/artifact/base/1B']))
                else: g.remove((self.act, RDF.type, BASE.BaserunningAct))
                self.assertFalse(validate(g, shacl_graph=self.shapes)[0])


if __name__ == '__main__':
    unittest.main()
