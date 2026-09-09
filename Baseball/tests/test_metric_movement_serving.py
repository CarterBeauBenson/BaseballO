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
        if origin:
            graph.add((URIRef(str(act) + '/origin-designation'), BFO.BFO_0000176, record))
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
        self.assertEqual(forced['episode'], str(EX.forcedAdvance) + '/episode')
        self.assertEqual(forced['originRecord'], str(EX.forcedAdvanceRecord))
        self.assertEqual(forced['safeJudgment'], str(EX.forcedAdvance) + '/judgment')
        self.assertEqual(forced['safeDecision'], str(EX.forcedAdvance) + '/decision')
        self.assertNotIn('metricOrigin', movements[str(EX.unknownAdvance)])
        direct = M.live_result('tfs', rows, graph_count=1)
        observed = direct['coverage']['runnerMovements']
        self.assertEqual(observed['observedPairs'], 3)
        self.assertEqual(observed['withCausalRequiredAwardBinding'], 2)
        self.assertEqual(observed['withSegmentOriginBinding'], 1)
        self.assertEqual(observed['withEpisodeBinding'], 3)
        self.assertEqual(observed['withOriginRecordBinding'], 1)
        self.assertEqual(observed['withSafeDecisionBinding'], 2)
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
        for field in ('act', 'plateAppearance', 'resolution', 'runner', 'episode',
                      'originRecord', 'safeJudgment', 'safeDecision'):
            row = next(r for r in source if field in r and r['kind']['value'] == 'runner_movement')
            bad = {**row, field: {'type': 'literal', 'value': row[field]['value']}}
            with self.assertRaises(M.EvidenceError):
                M.normalize_bindings([bad], [G1])
        bad = dict(row)
        del bad['act']
        with self.assertRaises(M.EvidenceError):
            M.normalize_bindings([bad], [G1])

    def test_multiple_episode_assertions_survive_without_changing_pair_count(self):
        dataset = movement_fixture()
        graph = dataset.graph(URIRef(G1))
        for predicate, value in [(RDF.type, BASE.RunnerResolutionEpisode),
                                 (BFO.BFO_0000132, EX.pa),
                                 (BFO.BFO_0000117, EX.forcedAdvance),
                                 (BFO.BFO_0000117, EX.forcedAdvanceAct)]:
            graph.add((EX.otherEpisode, predicate, value))
        rows = M.normalize_bindings(bindings(dataset, [G1]), [G1])
        forced = [r for r in rows if r['kind'] == 'runner_movement' and r['entity'] == str(EX.forcedAdvance)]
        self.assertEqual({r['episode'] for r in forced},
                         {str(EX.otherEpisode), str(EX.forcedAdvance) + '/episode'})
        self.assertEqual(M.movement_coverage(rows)['observedPairs'], 3)
        self.assertEqual(M.live_result('tfs', rows, graph_count=1)['status'], 'unavailable')

    def test_unlinked_record_and_other_resolution_decision_do_not_supply_support(self):
        dataset = movement_fixture()
        graph = dataset.graph(URIRef(G1))
        graph.remove((URIRef(str(EX.forcedAdvanceAct) + '/origin-designation'),
                      BFO.BFO_0000176, EX.forcedAdvanceRecord))
        graph.remove((URIRef(str(EX.forcedAdvance) + '/decision'),
                      CCO.ont00001808, EX.forcedAdvance))
        graph.add((URIRef(str(EX.forcedAdvance) + '/decision'),
                   CCO.ont00001808, EX.batterAdvance))
        rows = M.normalize_bindings(bindings(dataset, [G1]), [G1])
        forced, = [r for r in rows if r['kind'] == 'runner_movement' and r['entity'] == str(EX.forcedAdvance)]
        self.assertNotIn('originRecord', forced)
        self.assertNotIn('safeDecision', forced)
        self.assertNotIn('destinationBase', forced)
        self.assertEqual(forced['originCode'], '1B')

    def test_personal_whole_binding_survives_sql_without_admitting_continuity(self):
        dataset = movement_fixture()
        graph = dataset.graph(URIRef(G1))
        whole = URIRef('https://baseballontology.org/data/game/101/runner-trajectory/lifetime')
        for triple in [(whole, RDF.type, BFO.BFO_0000015),
                       (whole, BFO.BFO_0000117, URIRef(str(EX.forcedAdvance) + '/episode')),
                       (whole, BFO.BFO_0000057, EX.runner), (whole, BFO.BFO_0000132, EX.half),
                       (whole, BFO.BFO_0000199, EX.interval),
                       (EX.half, RDF.type, BASE.HalfInning),
                       (EX.interval, RDF.type, BFO.BFO_0000038)]:
            graph.add(triple)
        source = bindings(dataset, [G1])
        rows = M.normalize_bindings(source, [G1])
        forced, = [r for r in rows if r.get('trajectory')]
        self.assertEqual(forced['trajectory'], str(whole))
        self.assertEqual(forced['trajectoryInterval'], str(EX.interval))
        self.assertEqual(M.movement_coverage(rows)['withPersonalTrajectoryBinding'], 1)
        self.assertEqual(M.live_result('tfs', rows, graph_count=1)['status'], 'unavailable')
        with database() as connection:
            M.materialize_game(connection, G1, source)
            stored = [json.loads(r[0]) for r in connection.execute(
                'SELECT binding_json FROM metric_suite_evidence WHERE graph_iri=?', (G1,))]
            self.assertIn(forced, stored)
        raw = next(r for r in source if 'trajectory' in r)
        for field in ('trajectory', 'trajectoryHalf', 'trajectoryInterval'):
            bad = {**raw, field: {'type': 'literal', 'value': raw[field]['value']}}
            with self.assertRaises(M.EvidenceError):
                M.normalize_bindings([bad], [G1])


if __name__ == '__main__':
    unittest.main()
