"""The metric prerequisite audit counts graph links, never metric credit."""
import json
import unittest
from pathlib import Path

from rdflib import Dataset, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
BASE = Namespace("https://baseballontology.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
EX = Namespace("https://example.org/")
QUERY = ROOT / "sparql/metrics/attribution-evidence.rq"


class MetricEvidenceQueryTests(unittest.TestCase):
    def dataset(self):
        ds = Dataset()
        self.graph = ds.graph(URIRef("https://w3id.org/baseball/graph/game/1"))
        for t in [(EX.game, RDF.type, BASE.BaseballGame), (EX.pa, RDF.type, BASE.PlateAppearance),
                  (EX.pa, BFO.BFO_0000132, EX.half), (EX.half, BFO.BFO_0000132, EX.inning),
                  (EX.inning, BFO.BFO_0000132, EX.game)]: self.graph.add(t)
        return ds

    def row(self, ds):
        rows = list(ds.query(QUERY.read_text()))
        self.assertEqual(len(rows), 1)
        return [int(v) for v in rows[0][3:]]

    def test_no_mapped_resolutions_is_coverage_zero_only(self):
        self.assertEqual(self.row(self.dataset()), [0, 0, 0, 0, 0, 0, 0])

    def test_distinct_links_and_missing_destination_are_counted_without_credit(self):
        ds = self.dataset()
        for rr in [EX.safe, EX.unknownSafe, EX.out]:
            self.graph.add((rr, RDF.type, BASE.RunnerResolutionProcess))
            self.graph.add((rr, BFO.BFO_0000132, EX.pa))
        for rr in [EX.safe, EX.unknownSafe]: self.graph.add((rr, RDF.type, BASE.SafeProcess))
        self.graph.add((EX.out, RDF.type, BASE.OutProcess))
        self.graph.add((EX.safe, BASE.hasResolvedRunner, EX.runner))
        self.graph.add((EX.safe, BASE.hasResolvedRunner, EX.otherRunner))
        self.graph.add((EX.safe, BASE.hasAdjudicatedBase, EX.second))
        self.graph.add((EX.safe, BFO.BFO_0000062, EX.act))
        self.graph.add((EX.act, RDF.type, BASE.BaserunningAct))
        self.graph.add((EX.act, BFO.BFO_0000132, EX.pa))
        self.graph.add((EX.act, BASE.hasBaserunningOriginBase, EX.first))
        self.graph.add((EX.safe, BASE.settlesAwardFrom, EX.award))
        self.graph.add((EX.award, BFO.BFO_0000132, EX.pa))
        for bp in [EX.contact1, EX.contact2]:
            self.graph.add((bp, RDF.type, BASE.BattedBallPlayProcess))
            self.graph.add((bp, BFO.BFO_0000132, EX.pa))
            self.graph.add((bp, BFO.BFO_0000117, EX.safe))
        # Deliberately duplicated/invalid links do not inflate resolution counts.
        # This audit is not a substitute for source SHACL conformance.
        self.assertEqual(self.row(ds), [3, 1, 1, 1, 1, 1, 1])
        indexed = ds.graph(URIRef("https://w3id.org/baseball/graph/index/game/1"))
        for triple in self.graph: indexed.add(triple)
        self.assertEqual(self.row(ds), [3, 1, 1, 1, 1, 1, 1])

    def test_query_has_exactly_one_single_source_catalog_entry(self):
        catalog = json.loads((ROOT / "sparql/source-scope-catalog.json").read_text())
        entries = [e for e in catalog['entries'] if any(QUERY in (ROOT / 'sparql').glob(p) for p in e['patterns'])]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['category'], 'single-source')
        self.assertEqual(entries[0]['sources'], ['mlb-game'])
        self.assertEqual(entries[0]['writesGraphLayers'], [])


if __name__ == '__main__':
    unittest.main()
