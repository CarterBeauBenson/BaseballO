"""Evidence rows preserve unknowns and separate acts without assigning credit."""
import json
import unittest
from pathlib import Path

from rdflib import Dataset, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / 'sparql/metrics/runner-movement-evidence.rq'
BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')
CCO = Namespace('https://www.commoncoreontologies.org/')
EX = Namespace('https://example.org/')


class RunnerMovementEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.ds = Dataset()
        self.g = self.ds.graph(URIRef('https://w3id.org/baseball/graph/game/824315'))
        for t in [(EX.game, RDF.type, BASE.BaseballGame),
                  (EX.pa, RDF.type, BASE.PlateAppearance),
                  (EX.pa, BFO.BFO_0000132, EX.half),
                  (EX.half, BFO.BFO_0000132, EX.inning),
                  (EX.inning, BFO.BFO_0000132, EX.game)]: self.g.add(t)

    def movement(self, key, origin=None, destination=None, runner=EX.runner):
        rr, act = EX[key], EX[key + '-act']
        for t in [(rr, RDF.type, BASE.RunnerResolutionProcess),
                  (rr, BFO.BFO_0000132, EX.pa), (rr, BFO.BFO_0000062, act),
                  (act, RDF.type, BASE.BaserunningAct), (act, BFO.BFO_0000132, EX.pa)]: self.g.add(t)
        if runner: self.g.add((rr, BASE.hasResolvedRunner, runner))
        if origin: self.g.add((act, BASE.hasBaserunningOriginBase, origin))
        if destination:
            self.g.add((rr, BASE.hasAdjudicatedBase, destination))
            self.g.add((rr, RDF.type, BASE.SafeProcess))
        return rr, act

    def code(self, base, value):
        identifier = URIRef(str(base) + '/code')
        for t in [(identifier, RDF.type, CCO.ont00000649),
                  (identifier, CCO.ont00001916, base),
                  (identifier, CCO.ont00001765, Literal(value))]: self.g.add(t)

    def rows(self):
        return [r.asdict() for r in self.ds.query(QUERY.read_text())]

    def test_steal_and_single_remain_separate_with_explicit_codes(self):
        self.movement('steal', EX.alpha, EX.beta)
        rr, act = self.movement('single', EX.beta, EX.gamma)
        for base, value in [(EX.alpha, '1B'), (EX.beta, '2B'), (EX.gamma, '3B')]: self.code(base, value)
        for t in [(EX.contact, RDF.type, BASE.BattedBallPlayProcess),
                  (EX.contact, BFO.BFO_0000132, EX.pa),
                  (EX.contact, BFO.BFO_0000117, rr),
                  (EX.record, RDF.type, BASE.BaseballEventRecord),
                  (EX.record, CCO.ont00001808, rr),
                  (EX.record, CCO.ont00001808, act)]: self.g.add(t)
        rows = {r['resolution']: r for r in self.rows()}
        self.assertEqual(len(rows), 2)
        self.assertEqual(str(rows[EX.steal]['originCode']), '1B')
        self.assertEqual(str(rows[EX.steal]['destinationCode']), '2B')
        self.assertNotIn('contactPlay', rows[EX.steal])
        self.assertEqual(str(rows[EX.single]['originCode']), '2B')
        self.assertEqual(str(rows[EX.single]['destinationCode']), '3B')
        self.assertEqual(rows[EX.single]['record'], EX.record)
        self.assertEqual(rows[EX.single]['contactPlay'], EX.contact)

    def test_missing_origin_runner_and_code_stay_unbound(self):
        self.movement('unknown', destination=EX['base/1B'], runner=None)
        row, = self.rows()
        for key in ['runner', 'originBase', 'originCode', 'destinationCode']: self.assertNotIn(key, row)
        self.assertEqual(row['destinationBase'], EX['base/1B'])
        self.assertTrue(row['hasSafeType'].toPython())
        self.assertFalse(row['hasOutType'].toPython())

    def test_index_and_other_pa_evidence_do_not_join(self):
        rr, act = self.movement('out')
        self.g.add((rr, RDF.type, BASE.OutProcess))
        self.g.add((rr, BASE.settlesAwardFrom, EX.award))
        self.g.add((EX.award, BFO.BFO_0000132, EX.otherPA))
        indexed = self.ds.graph(URIRef('https://w3id.org/baseball/graph/index/game/824315'))
        for t in self.g: indexed.add(t)
        row, = self.rows()
        self.assertTrue(row['hasOutType'].toPython())
        self.assertNotIn('award', row)
        self.g.set((act, BFO.BFO_0000132, EX.otherPA))
        self.assertEqual(self.rows(), [])

    def test_conflicting_codes_are_visible_instead_of_arbitrarily_selected(self):
        self.movement('conflict', origin=EX.alpha)
        self.code(EX.alpha, '1B'); self.code(EX.alpha, '2B')
        self.assertEqual({str(r['originCode']) for r in self.rows()}, {'1B', '2B'})

    def test_catalog_is_single_source_read_only(self):
        catalog = json.loads((ROOT / 'sparql/source-scope-catalog.json').read_text())
        entries = [e for e in catalog['entries'] if any(QUERY in (ROOT / 'sparql').glob(p) for p in e['patterns'])]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['category'], 'single-source')
        self.assertEqual(entries[0]['sources'], ['mlb-game'])
        self.assertEqual(entries[0]['writesGraphLayers'], [])


if __name__ == '__main__':
    unittest.main()
