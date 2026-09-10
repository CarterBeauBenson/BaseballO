"""A complete forced-award chain is usable without asserting complete PA history."""
import unittest

from rdflib import Literal, RDF, URIRef

from runner_pattern_fixture import movement, award, BASE, BFO, CCO
from test_metric_movement_serving import EX
from test_metric_suite_serving import M, G1, G2, fixture, bindings, database


def loaded_fixture():
    dataset = fixture(decisions=())
    graph = dataset.graph(URIRef(G1))
    graph.add((EX.act, RDF.type, BASE.BatterAct))
    for i, runner, origin, destination in [
        (0, EX.player, None, EX.first),
        (1, EX.runner1, EX.first, EX.second),
        (2, EX.runner2, EX.second, EX.third),
        (3, EX.runner3, EX.third, None),
    ]:
        act, resolution, record = EX[f'advance{i}'], EX[f'resolution{i}'], EX[f'record{i}']
        movement(graph, resolution, act, EX.pa, runner, origin, destination)
        award(graph, EX.walk, act, EX.pa)
        graph.add((record, RDF.type, BASE.BaseballEventRecord))
        for target in (act, resolution):
            graph.add((record, CCO.ont00001808, target))
        if origin:
            graph.add((URIRef(str(act) + '/origin-designation'), BFO.BFO_0000176, record))
        if i == 3:
            graph.add((resolution, RDF.type, BASE.RunProcess))
    for base, code in [(EX.first, '1B'), (EX.second, '2B'), (EX.third, '3B')]:
        identifier = URIRef(str(base) + '/code')
        for triple in [(identifier, RDF.type, CCO.ont00000649),
                       (identifier, CCO.ont00001916, base),
                       (identifier, CCO.ont00001765, Literal(code))]:
            graph.add(triple)
    return dataset


def result(dataset, metric_id='tfs'):
    return M.live_result(metric_id, M.normalize_bindings(bindings(dataset, [G1]), [G1]), graph_count=1)


class LoadedAwardTFS(unittest.TestCase):
    def test_offensive_reach_counts_positive_paths_and_round_trips_without_aggregating(self):
        source = bindings(loaded_fixture(), [G1])
        rows = M.normalize_bindings(source + source, [G1])
        reach = M.live_result('offensive-reach', rows, graph_count=1)
        tfs = M.live_result('tfs', rows, graph_count=1)
        self.assertEqual(reach['status'], 'unavailable')
        self.assertIsNone(reach['value'])
        self.assertEqual(set(reach['gaps']), {'ATTRIBUTION', 'PATH_IDENTITY', 'COMPLETENESS'})
        score, = reach['consequences']
        self.assertEqual(score['value'], M.exact(4))
        self.assertEqual(score['components'], {'positiveTrajectories': M.exact(4)})
        self.assertEqual(score['evidence'], tfs['consequences'][0]['evidence'])
        self.assertEqual(score['movements'], tfs['consequences'][0]['movements'])
        self.assertEqual(score['grain'], 'award_consequence')
        self.assertFalse(score['completePlateAppearance'])
        with database() as connection:
            M.materialize_game(connection, G1, source + source)
            M.materialize_game(connection, G2, bindings(fixture(graph=G2, decisions=()), [G2]))
            scope = {'gameSet':'regular_season', 'startDate':'2026-08-01', 'endDate':'2026-08-01'}
            self.assertEqual(M.query_sql(connection, {'metricId':'offensive-reach'}, scope)['metric'], reach)
            scope['endDate'] = '2026-08-02'
            pooled = M.query_sql(connection, {'metricId':'offensive-reach'}, scope)['metric']
            self.assertEqual(pooled['consequences'], reach['consequences'])
            self.assertIsNone(pooled['value'])
            self.assertEqual(pooled['coverage']['observedPAsWithoutSupportedAwardConsequence'], 1)
            scope['startDate'] = '2026-08-02'
            self.assertEqual(M.query_sql(connection, {'metricId':'offensive-reach'}, scope)['metric']['consequences'], [])

    def test_exact_consequence_preserves_full_pa_gap_and_all_four_proofs(self):
        scored = result(loaded_fixture())
        self.assertEqual(scored['status'], 'unavailable')
        self.assertIsNone(scored['value'])
        self.assertFalse(scored['coverage']['populationComplete'])
        game, = scored['coverage']['byGame']
        self.assertEqual(game['supportedAwardConsequences'], 1)
        self.assertEqual(game['runnerMovements']['withRunnerEpisodeRecordBinding'], 4)
        row, = scored['consequences']
        self.assertEqual(row['value'], M.exact(M.Fraction(25, 12)))
        self.assertEqual(row['components']['erosion'], M.exact(0))
        self.assertFalse(row['completePlateAppearance'])
        self.assertEqual({r['metricOrigin'] for r in row['movements']}, {'0','1','2','3'})
        self.assertIn(str(EX.record3), row['evidence'])
        self.assertIn(str(EX.resolution1) + '/decision', row['evidence'])
        self.assertNotIn('outsBefore', row)

    def test_hbp_has_same_accepted_consequence(self):
        dataset = loaded_fixture()
        graph = dataset.graph(URIRef(G1))
        graph.remove((EX.walk, RDF.type, BASE.WalkProcess))
        graph.add((EX.walk, RDF.type, BASE.HitByPitchProcess))
        self.assertEqual(result(dataset)['consequences'][0]['value'], M.exact(M.Fraction(25,12)))

    def test_missing_or_contradictory_required_evidence_withholds_whole_chain(self):
        changes = [
            ('cause', (EX.walk, CCO.ont00001803, EX.advance1), None),
            ('rule', (URIRef(str(EX.walk) + '/rule'), CCO.ont00001974, EX.advance1), None),
            ('origin record', (URIRef(str(EX.advance1) + '/origin-designation'), BFO.BFO_0000176, EX.record1), None),
            ('safe decision', (URIRef(str(EX.resolution1) + '/decision'), CCO.ont00001808, EX.resolution1), None),
            ('run', (EX.resolution3, RDF.type, BASE.RunProcess), None),
            ('out', None, (EX.resolution1, RDF.type, BASE.OutProcess)),
            ('conflicting origin', None, (URIRef(str(EX.first) + '/code'), CCO.ont00001765, Literal('3B'))),
            ('same runner twice', (EX.advance2, CCO.ont00001833, EX.runner2), (EX.advance2, CCO.ont00001833, EX.runner1)),
            ('batter conflict', None, (EX.role, BFO.BFO_0000197, EX.otherBatter)),
            ('contact ambiguity', None, (EX.play, BFO.BFO_0000117, EX.resolution1)),
        ]
        for label, remove, add in changes:
            with self.subTest(label=label):
                dataset = loaded_fixture()
                graph = dataset.graph(URIRef(G1))
                if remove: graph.remove(remove)
                if add: graph.add(add)
                self.assertEqual(result(dataset)['consequences'], [])
                self.assertEqual(result(dataset, 'offensive-reach')['consequences'], [])

    def test_extra_movement_is_not_filtered_away_before_selection(self):
        dataset = loaded_fixture()
        movement(dataset.graph(URIRef(G1)), EX.extraResolution, EX.extraAct, EX.pa, EX.runner1)
        self.assertEqual(result(dataset)['consequences'], [])
        self.assertEqual(result(dataset, 'offensive-reach')['consequences'], [])

    def test_duplicates_scopes_and_sql_round_trip(self):
        dataset = loaded_fixture()
        source = bindings(dataset, [G1])
        direct = result(dataset)
        normalized = M.normalize_bindings(source + source, [G1])
        self.assertEqual(M.live_result('tfs', normalized, graph_count=1), direct)
        with database() as connection:
            M.materialize_game(connection, G1, source + source)
            M.materialize_game(connection, G2, bindings(fixture(graph=G2, decisions=()), [G2]))
            selection = {'gameSet':'regular_season','startDate':'2026-08-01','endDate':'2026-08-01'}
            self.assertEqual(M.query_sql(connection, {'metricId':'tfs'}, selection)['metric'], direct)
            selection['endDate'] = '2026-08-02'
            pooled = M.query_sql(connection, {'metricId':'tfs'}, selection)['metric']
            self.assertEqual(len(pooled['consequences']), 1)
            self.assertEqual(pooled['coverage']['observedPAsWithoutSupportedAwardConsequence'], 1)
            self.assertIsNone(pooled['value'])
            selection['startDate'] = '2026-08-02'
            self.assertEqual(M.query_sql(connection, {'metricId':'tfs'}, selection)['metric']['consequences'], [])


if __name__ == '__main__':
    unittest.main()
