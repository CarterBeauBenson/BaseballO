"""Read accepted PA-start evidence without constructing a new location state."""
import json
import unittest
from pathlib import Path

from rdflib import Dataset, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / 'sparql/metrics/runner-location-evidence.rq'
BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')
CCO = Namespace('https://www.commoncoreontologies.org/')
EX = Namespace('https://example.org/')


class RunnerLocationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.ds = Dataset()
        self.g = self.ds.graph(URIRef('https://w3id.org/baseball/graph/game/1'))
        for t in [(EX.game, RDF.type, BASE.BaseballGame),
                  (EX.half, BFO.BFO_0000132, EX.inning),
                  (EX.inning, BFO.BFO_0000132, EX.game),
                  (EX.runner, RDF.type, CCO.ont00001262),
                  (EX.site, RDF.type, BASE.BaseSite)]: self.g.add(t)

    def stasis(self, key):
        pa, stasis = EX[key], EX[key + '-stasis']
        for t in [(pa, RDF.type, BASE.PlateAppearance),
                  (pa, BFO.BFO_0000132, EX.half),
                  (stasis, RDF.type, BASE.BaserunnerAtBaseStasis),
                  (stasis, BFO.BFO_0000132, pa),
                  (stasis, BFO.BFO_0000057, EX.runner),
                  (stasis, CCO.ont00001918, EX.site)]: self.g.add(t)
        return pa, stasis

    def rows(self):
        return [r.asdict() for r in self.ds.query(QUERY.read_text())]

    def test_existence_of_relata_does_not_supply_location_or_stasis_time(self):
        self.stasis('pa')
        self.g.add((EX.runner, BFO.BFO_0000108, EX.instant))
        self.g.add((EX.site, BFO.BFO_0000108, EX.instant))
        row, = self.rows()
        self.assertFalse(row['hasExplicitRunnerBaseSiteLink'].toPython())
        for name in ['stasisInterval', 'stasisFirstInstant', 'paInterval', 'paFirstInstant', 'enclosingLocation']:
            self.assertNotIn(name, row)

    def test_same_runner_and_site_keep_distinct_pa_time_anchors(self):
        for key in ['pa1', 'pa2']:
            pa, stasis = self.stasis(key)
            for t in [(stasis, BFO.BFO_0000199, EX[key + '-stasis-interval']),
                      (EX[key + '-stasis-interval'], BFO.BFO_0000222, EX[key + '-start']),
                      (pa, BFO.BFO_0000199, EX[key + '-interval']),
                      (EX[key + '-interval'], BFO.BFO_0000222, EX[key + '-start'])]: self.g.add(t)
        self.g.add((EX.runner, BFO.BFO_0000171, EX.site))
        self.g.add((EX.site, BFO.BFO_0000171, EX.outer))
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        for row in rows:
            key = str(row['plateAppearance']).rsplit('/', 1)[1]
            self.assertEqual(row['stasisFirstInstant'], EX[key + '-start'])
            self.assertEqual(row['paFirstInstant'], EX[key + '-start'])
            self.assertEqual(row['enclosingLocation'], EX.outer)
            self.assertTrue(row['hasExplicitRunnerBaseSiteLink'].toPython())
        # The query is read-only and does not add a transitive runner/outer link.
        self.assertNotIn((EX.runner, BFO.BFO_0000171, EX.outer), self.g)

    def test_index_and_generic_stasis_are_not_pa_start_evidence(self):
        _, stasis = self.stasis('pa')
        indexed = self.ds.graph(URIRef('https://w3id.org/baseball/graph/index/game/1'))
        for t in self.g: indexed.add(t)
        self.assertEqual(len(self.rows()), 1)
        self.g.remove((stasis, RDF.type, BASE.BaserunnerAtBaseStasis))
        self.g.add((stasis, RDF.type, CCO.ont00000819))
        self.assertEqual(self.rows(), [])

    def test_catalog_is_single_source_read_only(self):
        catalog = json.loads((ROOT / 'sparql/source-scope-catalog.json').read_text())
        entries = [e for e in catalog['entries'] if any(QUERY in (ROOT / 'sparql').glob(p) for p in e['patterns'])]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['category'], 'single-source')
        self.assertEqual(entries[0]['sources'], ['mlb-game'])
        self.assertEqual(entries[0]['writesGraphLayers'], [])


if __name__ == '__main__':
    unittest.main()
