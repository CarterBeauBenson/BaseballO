"""Legacy single-batter scores must not duplicate accepted PA participation."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

from rdflib import Dataset, Literal, Namespace, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parents[1]
BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')
QUERY = (ROOT / 'sparql/advanced/plate-appearance-fingerprint.rq').read_text(encoding='utf-8')


def fixture(batters=1, pitchers=1):
    dataset = Dataset()
    graph = dataset.graph(URIRef('https://w3id.org/baseball/graph/game/1'))
    game, inning, half, pa, interval, result, judgment = [URIRef('urn:' + name)
        for name in ('game', 'inning', 'half', 'pa', 'interval', 'result', 'judgment')]
    graph.add((game, RDF.type, BASE.BaseballGame))
    graph.add((pa, RDF.type, BASE.PlateAppearance))
    graph.add((pa, BFO.BFO_0000199, interval))
    for part, whole in ((pa, half), (half, inning), (inning, game), (result, pa)):
        graph.add((part, BFO.BFO_0000132, whole))
    graph.add((result, RDF.type, BASE.BaseballInstitutionalProcess))
    graph.add((result, RDF.type, BASE.StrikeoutProcess))
    graph.add((result, BFO.BFO_0000117, judgment))
    graph.add((judgment, RDF.type, BASE.BaseballAdjudicationAct))
    for kind, total, act_type in [('batter', batters, BASE.BatterAct), ('pitcher', pitchers, BASE.PitchAct)]:
        for i in range(total):
            actor = URIRef(f'urn:{kind}:{i}')
            act = URIRef(f'urn:{kind}:act:{i}')
            graph.add((act, RDF.type, act_type))
            graph.add((act, BFO.BFO_0000132, pa))
            graph.add((act, BFO.BFO_0000057, actor))
            graph.add((actor, RDFS.label, Literal(f'{kind} {i}')))
    return dataset, graph


@unittest.skipUnless(os.environ.get('BASEBALLO_TEST_JENA_CLASSPATH'), 'requires the deployed Jena runtime')
class LegacyPaqQueryTests(unittest.TestCase):
    def run_query(self, dataset):
        # Exercise the production engine, including empty grouped results and
        # optional unbound aggregates which RDFLib evaluates differently.
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            dataset.serialize(work / 'fixture.trig', format='trig')
            (work / 'query.rq').write_text(QUERY, encoding='utf-8')
            (work / 'QueryFixture.java').write_text('''
import org.apache.jena.query.*;
import org.apache.jena.riot.RDFDataMgr;
class QueryFixture {
  public static void main(String[] args) {
    Dataset data = DatasetFactory.create();
    try {
      RDFDataMgr.read(data, args[0]);
      try (QueryExecution query = QueryExecutionFactory.create(QueryFactory.read(args[1]), data)) {
        ResultSetFormatter.outputAsJSON(query.execSelect());
      }
    } finally { data.close(); }
  }
}
''', encoding='utf-8')
            result = subprocess.run([os.environ.get('BASEBALLO_TEST_JAVA', 'java'),
                '-Xmx256m', '--class-path', os.environ['BASEBALLO_TEST_JENA_CLASSPATH'],
                str(work / 'QueryFixture.java'), str(work / 'fixture.trig'), str(work / 'query.rq')],
                capture_output=True, text=True, encoding='utf-8', timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)['results']['bindings']

    def test_substituted_batters_withhold_legacy_score_without_removing_participation(self):
        dataset, graph = fixture(batters=2)
        self.assertEqual(self.run_query(dataset), [])
        self.assertEqual(len(list(graph.subjects(RDF.type, BASE.BatterAct))), 2)

    def test_single_batter_multiple_pitchers_still_has_one_pa_and_no_false_pitcher(self):
        for pitchers in (0, 1, 2):
            with self.subTest(pitchers=pitchers):
                dataset, graph = fixture(pitchers=pitchers)
                # Additional display labels must not multiply a fact either.
                graph.add((URIRef('urn:batter:0'), RDFS.label, Literal('Alternative name')))
                rows = self.run_query(dataset)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['batter']['value'], 'urn:batter:0')
                self.assertEqual(rows[0].get('pitcher', {}).get('value'), 'urn:pitcher:0' if pitchers == 1 else None)
                self.assertEqual(int(rows[0]['pitches']['value']), pitchers)


if __name__ == '__main__':
    unittest.main()
