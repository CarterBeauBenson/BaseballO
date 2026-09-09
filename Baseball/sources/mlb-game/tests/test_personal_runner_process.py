"""C1 graph conformance without claiming source-history completeness."""
import sys
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests'))
from runner_pattern_fixture import BASE, BFO, CCO, movement

SH = Namespace('https://w3id.org/baseball/shacl/')
EX = Namespace('https://baseballontology.org/data/game/1/')


def fixture():
    g = Graph()
    whole = EX['runner-trajectory/proven-lifetime']
    for triple in [(whole, RDF.type, BFO.BFO_0000015),
                   (whole, BFO.BFO_0000132, EX.half),
                   (whole, BFO.BFO_0000057, EX.runner),
                   (whole, BFO.BFO_0000199, EX.interval),
                   (EX.half, RDF.type, BASE.HalfInning),
                   (EX.half, BFO.BFO_0000132, EX.inning),
                   (EX.inning, BFO.BFO_0000132, URIRef(str(EX).rstrip('/'))),
                   (URIRef(str(EX).rstrip('/')), RDF.type, BASE.BaseballGame),
                   (EX.interval, RDF.type, BFO.BFO_0000038)]:
        g.add(triple)
    for number in (1, 2):
        pa, act, resolution = EX[f'pa{number}'], EX[f'act{number}'], EX[f'resolution{number}']
        g.add((pa, RDF.type, BASE.PlateAppearance))
        g.add((pa, BFO.BFO_0000132, EX.half))
        episode, _, _ = movement(g, resolution, act, pa, EX.runner,
                                 destination=EX[f'base{number}'])
        g.add((whole, BFO.BFO_0000117, episode))
    return g, whole


class PersonalRunnerProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile = Graph().parse(ROOT / 'sources/mlb-game/shacl/authoritative.ttl')
        cls.shapes = Graph()
        pending = [SH.PersonalRunnerProcessTargetShape]
        visited = set()
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            for triple in profile.triples((node, None, None)):
                cls.shapes.add(triple)
                if isinstance(triple[2], BNode) or str(triple[2]).startswith(str(SH)):
                    pending.append(triple[2])

    def conforms(self, graph):
        result, _, report = validate(graph, shacl_graph=self.shapes)
        return result, report

    def test_personal_whole_spans_pas_without_becoming_an_episode_or_act(self):
        g, whole = fixture()
        self.assertTrue(self.conforms(g)[0], self.conforms(g)[1])
        self.assertNotIn((whole, RDF.type, BASE.RunnerResolutionEpisode), g)
        self.assertEqual(list(g.objects(whole, BFO.BFO_0000055)), [])

    def test_graph_contract_rejects_wrong_person_scope_and_terminal_structure(self):
        for fault in ('person', 'half', 'interval', 'pa-parent', 'realizes', 'agent',
                      'episode-type', 'two-terminals', 'contradictory-terminal', 'game', 'missing-type'):
            with self.subTest(fault=fault):
                g, whole = fixture()
                if fault == 'person':
                    g.set((EX.act2, CCO.ont00001833, EX.otherRunner))
                elif fault == 'half':
                    g.set((EX.pa2, BFO.BFO_0000132, EX.otherHalf))
                elif fault == 'interval':
                    g.remove((whole, BFO.BFO_0000199, None))
                elif fault == 'pa-parent':
                    g.add((whole, BFO.BFO_0000132, EX.pa1))
                elif fault == 'realizes':
                    g.add((whole, BFO.BFO_0000055, EX.role))
                elif fault == 'agent':
                    g.add((whole, CCO.ont00001833, EX.runner))
                elif fault == 'episode-type':
                    g.add((whole, RDF.type, BASE.RunnerResolutionEpisode))
                elif fault == 'two-terminals':
                    g.add((EX.resolution1, RDF.type, BASE.OutProcess))
                    g.add((EX.resolution2, RDF.type, BASE.RunProcess))
                elif fault == 'contradictory-terminal':
                    g.add((EX.resolution1, RDF.type, BASE.OutProcess))
                    g.add((EX.resolution1, RDF.type, BASE.RunProcess))
                elif fault == 'game':
                    g.set((EX.inning, BFO.BFO_0000132, EX.otherGame))
                else:
                    g.remove((whole, RDF.type, BFO.BFO_0000015))
                self.assertFalse(self.conforms(g)[0])

    def test_unrelated_processes_are_not_retyped_as_personal_trajectories(self):
        g, whole = fixture()
        g.add((EX.unrelated, BFO.BFO_0000117, EX.whatever))
        g.add((EX.unrelated, RDF.type, BFO.BFO_0000015))
        self.assertTrue(self.conforms(g)[0])


if __name__ == '__main__':
    unittest.main()
