"""Accepted movement paths survive the authoritative-query/SQL boundary."""
import json
import unittest

from rdflib import Literal, Namespace, RDF, URIRef

from runner_pattern_fixture import movement, award, BASE, BFO, CCO
from test_metric_suite_serving import M, G1, G2, fixture, bindings, database

EX = Namespace('urn:test:101:')


def movement_fixture():
    dataset = fixture(decisions=())
    graph = dataset.graph(URIRef(G1))
    graph.add((EX.act, RDF.type, BASE.BatterAct))
    for key, runner, origin, destination in [
        ('batterAdvance', EX.player, None, EX.first),
        ('forcedAdvance', EX.runner, EX.first, EX.second),
        ('unknownAdvance', EX.otherRunner, None, None),
    ]:
        act, resolution, record = EX[key + 'Act'], EX[key], EX[key + 'Record']
        movement(graph, resolution, act, EX.pa, runner, origin, destination)
        graph.add((record, RDF.type, BASE.BaseballEventRecord))
        graph.add((record, CCO.ont00001808, act))
        graph.add((record, CCO.ont00001808, resolution))
        if key != 'unknownAdvance':
            award(graph, EX.walk, act, EX.pa)
    for base, code in [(EX.first, '1B'), (EX.second, '2B')]:
        identifier = URIRef(str(base) + '/code')
        graph.add((identifier, RDF.type, CCO.ont00000649))
        graph.add((identifier, CCO.ont00001916, base))
        graph.add((identifier, CCO.ont00001765, Literal(code)))
    return dataset


class MovementServing(unittest.TestCase):
    def test_movement_paths_and_unknowns_survive_sql_without_admitting_scores(self):
        source = bindings(movement_fixture(), [G1])
        rows = M.normalize_bindings(source, [G1])
        movements = {r['entity']: r for r in rows if r['kind'] == 'runner_movement'}
        self.assertEqual(len(movements), 3)
        batter = movements[str(EX.batterAdvance)]
        self.assertEqual(batter['metricOrigin'], '0')
        self.assertNotIn('originBase', batter)
        forced = movements[str(EX.forcedAdvance)]
        self.assertEqual((forced['originCode'], forced['destinationCode']), ('1B', '2B'))
        self.assertEqual(forced['record'], str(EX.forcedAdvanceRecord))
        self.assertEqual(forced['award'], str(EX.walk))
        self.assertNotIn('metricOrigin', movements[str(EX.unknownAdvance)])
        direct = M.live_result('tfs', rows, graph_count=1)
        observed = direct['coverage']['runnerMovements']
        self.assertEqual(observed['observedPairs'], 3)
        self.assertEqual(observed['withCausalRequiredAwardBinding'], 2)
        self.assertEqual(observed['withSegmentOriginBinding'], 1)
        self.assertEqual(observed['withOneMetricOriginBinding'], 2)
        self.assertEqual(observed['withoutMetricOriginBinding'], 1)
        self.assertFalse(observed['populationComplete'])
        self.assertEqual(direct['status'], 'unavailable')
        self.assertIsNone(direct['value'])
        with database() as connection:
            M.materialize_game(connection, G1, source + source)
            M.materialize_game(connection, G1, source)
            stored = [json.loads(r[0]) for r in connection.execute(
                'SELECT binding_json FROM metric_suite_evidence WHERE graph_iri=?', (G1,))]
            self.assertEqual(sorted(stored, key=M._json), sorted(rows, key=M._json))
            result = M.query_sql(connection, {'metricId': 'tfs'}, {
                'gameSet': 'regular_season', 'startDate': '2026-08-01', 'endDate': '2026-08-01'})
            self.assertEqual(result['metric'], direct)

    def test_conflicting_origins_survive_and_do_not_inflate_pair_counts(self):
        dataset = movement_fixture()
        dataset.graph(URIRef(G1)).add((URIRef(str(EX.first) + '/code'), CCO.ont00001765, Literal('3B')))
        rows = M.normalize_bindings(bindings(dataset, [G1]), [G1])
        forced = [r for r in rows if r['kind'] == 'runner_movement' and r['entity'] == str(EX.forcedAdvance)]
        self.assertEqual({r['metricOrigin'] for r in forced}, {'1', '3'})
        coverage = M.movement_coverage(rows + rows)
        self.assertEqual(coverage['observedPairs'], 3)
        self.assertEqual(coverage['withMultipleMetricOriginBindings'], 1)
        self.assertEqual(coverage['withOneMetricOriginBinding'], 1)
        self.assertEqual(M.live_result('tfs', rows, graph_count=1)['status'], 'unavailable')

    def test_scopes_and_identity_types_remain_enforced_for_movement_branch(self):
        dataset = movement_fixture()
        for triple in dataset.graph(URIRef(G1)):
            dataset.graph(URIRef(G2)).add(triple)
        source = bindings(dataset, [G1])
        self.assertEqual({r['graph']['value'] for r in source}, {G1})
        self.assertEqual(bindings(dataset, []), [])
        both = M.normalize_bindings(bindings(dataset, [G1, G2]), [G1, G2])
        self.assertEqual(M.movement_coverage(both)['observedPairs'], 6)
        row = next(r for r in source if r['kind']['value'] == 'runner_movement')
        for field in ('act', 'plateAppearance', 'resolution', 'runner'):
            bad = {**row, field: {'type': 'literal', 'value': row[field]['value']}}
            with self.assertRaises(M.EvidenceError):
                M.normalize_bindings([bad], [G1])
        bad = dict(row)
        del bad['act']
        with self.assertRaises(M.EvidenceError):
            M.normalize_bindings([bad], [G1])


if __name__ == '__main__':
    unittest.main()
