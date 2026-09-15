"""Focused real-RDF -> canonical SPARQL -> exact metric -> SQL proof.

Run only on the isolated one-game output after its authoritative SHACL gate.
Jena evaluates the same canonical query used by Fuseki; no store is changed.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('metric_suite', ROOT / 'serving/metric_suite.py')
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)

JAVA = '''
import java.nio.file.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
class MetricQuery {
  public static void main(String[] args) throws Exception {
    var dataset = DatasetFactory.createTxnMem();
    dataset.addNamedModel(args[1], RDFDataMgr.loadModel(args[0]));
    var query = QueryFactory.create(Files.readString(Path.of(args[2])));
    try (var execution = QueryExecutionFactory.create(query, dataset);
         var output = Files.newOutputStream(Path.of(args[3]))) {
      ResultSetFormatter.outputAsJSON(output, execution.execSelect());
    }
    dataset.close();
  }
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rdf', type=Path, required=True)
    parser.add_argument('--java', required=True)
    parser.add_argument('--jena-classpath', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--include-boundaries', action='store_true')
    args = parser.parse_args()
    graph = 'https://w3id.org/baseball/graph/game/566279'
    with tempfile.TemporaryDirectory(prefix='baseballo-run-query-') as temporary:
        directory = Path(temporary)
        (directory / 'MetricQuery.java').write_text(JAVA, encoding='utf-8')
        (directory / 'query.rq').write_text(M.evidence_query([graph]), encoding='utf-8')
        subprocess.run([args.java, '-Xmx512m', '--class-path', args.jena_classpath,
                        str(directory / 'MetricQuery.java'), str(args.rdf.resolve()), graph,
                        str(directory / 'query.rq'), str(directory / 'bindings.json')], check=True, timeout=60)
        bindings = json.loads((directory / 'bindings.json').read_bytes())['results']['bindings']
    rows = M.normalize_bindings(bindings, [graph])
    result = M.live_result('run-construction-depth', rows, graph_count=1)
    boundary_result = M.live_result('tfs', rows, graph_count=1) if args.include_boundaries else None
    flores = [r for r in result['runs'] if r['runner'].endswith('/527038')]
    assert len(flores) == 1 and flores[0]['value'] == M.exact(3), flores
    assert all(r['completeTrajectory'] for r in result['runs'])
    with sqlite3.connect(':memory:') as database:
        database.executescript((ROOT / 'serving/schema.sql').read_text())
        M.initialize_sql(database)
        database.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                         (graph, 'https://baseballontology.org/data/game/566279', '566279',
                          '2019-04-01', '2019-04-01T00:00:00Z', 2019, 'regular_season', None, None, None, None, None, None))
        M.materialize_game(database, graph, bindings)
        response = M.query_sql(database, {'metricId':'run-construction-depth'},
                              {'gameSet':'regular_season', 'startDate':'2019-04-01', 'endDate':'2019-04-01'})
        assert response['metric'] == result
        if boundary_result is not None:
            boundary_response = M.query_sql(database, {'metricId': 'tfs'},
                                           {'gameSet':'regular_season', 'startDate':'2019-04-01', 'endDate':'2019-04-01'})
            assert boundary_response['metric'] == boundary_result
    report = dict(metric=result, sqlExactMatch=True, implementationSha256=M.fingerprint())
    if boundary_result is not None:
        report['boundaryMetric'] = boundary_result
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(supportedRuns=len(result['runs']),
                          observedRuns=result['coverage']['observedEntities']['run'],
                          floresDepth=flores[0]['value'], sqlExactMatch=True,
                          runnerBoundaryStates=len(boundary_result['runnerBoundaryStates']) if boundary_result else None)))


if __name__ == '__main__': main()
