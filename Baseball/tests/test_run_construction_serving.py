import unittest

from rdflib import Dataset, Literal, Namespace, RDF, URIRef

from runner_pattern_fixture import movement, BASE, BFO, CCO
from test_metric_suite_serving import M, G1, G2, database, bindings, fixture

EX = Namespace('https://baseballontology.org/data/game/101/')
WHOLE = EX['runner-trajectory/scored-life']


def run_fixture(held=False):
    dataset = Dataset(); graph = dataset.graph(G1)
    graph.add((EX.game, RDF.type, BASE.BaseballGame))
    graph.add((EX.inning, BFO.BFO_0000132, EX.game))
    graph.add((EX.half, RDF.type, BASE.HalfInning))
    graph.add((EX.half, BFO.BFO_0000132, EX.inning))
    for triple in [(WHOLE, RDF.type, BFO.BFO_0000015), (WHOLE, BFO.BFO_0000132, EX.half),
                   (WHOLE, BFO.BFO_0000199, EX.interval), (EX.interval, RDF.type, BFO.BFO_0000038),
                   (WHOLE, BFO.BFO_0000057, EX.runner)]: graph.add(triple)
    for i, origin, destination in [(0, None, EX.first), (1, EX.first, EX.first if held else EX.second),
                                   (2, EX.first if held else EX.second, None)]:
        pa, act, resolution = EX[f'pa{i}'], EX[f'act{i}'], EX[f'resolution{i}']
        graph.add((pa, RDF.type, BASE.PlateAppearance)); graph.add((pa, BFO.BFO_0000132, EX.half))
        if i == 0:
            for triple in [(EX.batterAct, RDF.type, BASE.BatterAct), (EX.batterAct, BFO.BFO_0000132, pa),
                           (EX.batterAct, BFO.BFO_0000055, EX.role), (EX.role, RDF.type, BASE.BatterRole),
                           (EX.role, BFO.BFO_0000197, EX.runner)]: graph.add(triple)
        episode, _, _ = movement(graph, resolution, act, pa, EX.runner, origin, destination)
        graph.add((WHOLE, BFO.BFO_0000117, episode))
        if i == 2: graph.add((resolution, RDF.type, BASE.RunProcess))
    for base, code in [(EX.first, '1B'), (EX.second, '2B')]:
        identifier = URIRef(str(base) + '/code')
        for triple in [(identifier, RDF.type, CCO.ont00000649), (identifier, CCO.ont00001916, base),
                       (identifier, CCO.ont00001765, Literal(code))]: graph.add(triple)
    return dataset


def score(dataset):
    return M.live_result('run-construction-depth', M.normalize_bindings(bindings(dataset, [G1]), [G1]), graph_count=1)


class RunConstructionServing(unittest.TestCase):
    def test_full_run_depth_reaches_sql_without_claiming_population_completeness(self):
        dataset = run_fixture(); source = bindings(dataset, [G1]); result = score(dataset)
        run, = result['runs']
        self.assertEqual(run['value'], M.exact(3))
        self.assertTrue(run['completeTrajectory'])
        self.assertEqual(run['grain'], 'run')
        self.assertFalse(result['coverage']['populationComplete'])
        self.assertIsNone(result['value'])
        with database() as connection:
            M.materialize_game(connection, G1, source + source)
            M.materialize_game(connection, G2, bindings(fixture(graph=G2, decisions=()), [G2]))
            scope = {'gameSet':'regular_season', 'startDate':'2026-08-01', 'endDate':'2026-08-01'}
            self.assertEqual(M.query_sql(connection, {'metricId':'run-construction-depth'}, scope)['metric'], result)
            scope['startDate'] = scope['endDate'] = '2026-08-02'
            self.assertEqual(M.query_sql(connection, {'metricId':'run-construction-depth'}, scope)['metric']['runs'], [])

    def test_held_base_observation_adds_no_depth(self):
        run, = score(run_fixture(held=True))['runs']
        self.assertEqual(run['value'], M.exact(2))
        self.assertEqual(len(run['episodes']), 3)

    def same_pa_fixture(self, held=True):
        dataset = run_fixture(held=held)
        graph = dataset.graph(G1)
        # The batter reaches first and has another movement observation during
        # the SAME PA. Canonical evidence deliberately keeps metricOrigin=0 for
        # batter consequence arithmetic; the segment designation remains 1B.
        for subject, predicate, _ in list(graph.triples((None, BFO.BFO_0000132, EX.pa1))):
            graph.remove((subject, predicate, EX.pa1))
            graph.add((subject, predicate, EX.pa0))
        graph.remove((EX.pa1, None, None))
        return dataset

    def test_same_pa_batter_hold_does_not_add_run_depth(self):
        dataset = self.same_pa_fixture()
        source = bindings(dataset, [G1])
        rows = M.normalize_bindings(source, [G1])
        held, = [r for r in rows if r.get('resolution') == str(EX.resolution1)]
        self.assertEqual((held['metricOrigin'], held['originCode']), ('0', '1B'))
        result = M.live_result('run-construction-depth', rows, graph_count=1)
        run, = result['runs']
        self.assertEqual(run['value'], M.exact(2))
        episode, = [r for r in run['episodes'] if r['resolution'] == str(EX.resolution1)]
        self.assertEqual((episode['start'], episode['end'], episode['changesState']), (1, 1, False))
        with database() as connection:
            M.materialize_game(connection, G1, source)
            scope = {'gameSet':'regular_season', 'startDate':'2026-08-01', 'endDate':'2026-08-01'}
            self.assertEqual(M.query_sql(connection, {'metricId':'run-construction-depth'}, scope)['metric'], result)

    def test_same_pa_batter_further_advance_still_counts_once(self):
        run, = score(self.same_pa_fixture(held=False))['runs']
        self.assertEqual(run['value'], M.exact(3))
        episode, = [r for r in run['episodes'] if r['resolution'] == str(EX.resolution1)]
        self.assertEqual((episode['start'], episode['end']), (1, 2))

    def test_batter_home_override_cannot_hide_conflicting_segment_origins(self):
        dataset = self.same_pa_fixture()
        dataset.graph(G1).add((URIRef(str(EX.first) + '/code'), CCO.ont00001765, Literal('3B')))
        self.assertEqual(score(dataset)['runs'], [])

    def test_designated_but_unidentified_base_cannot_fall_back_to_batter_home(self):
        dataset = self.same_pa_fixture()
        dataset.graph(G1).remove((URIRef(str(EX.first) + '/code'), CCO.ont00001765, None))
        self.assertEqual(score(dataset)['runs'], [])

    def test_missing_movement_cannot_shorten_a_complete_run(self):
        dataset = run_fixture()
        dataset.graph(G1).remove((EX.resolution1, BFO.BFO_0000062, None))
        result = score(dataset)
        self.assertEqual(result['runs'], [])
        self.assertEqual(result['unresolvedRuns'][0]['gaps'], ['PERSONAL_HISTORY_MEMBER_COVERAGE'])
        self.assertEqual(result['coverage']['runGapCounts'], {'PERSONAL_HISTORY_MEMBER_COVERAGE': 1})

    def test_missing_c1_whole_or_extra_member_withholds_score(self):
        for extra in (False, True):
            dataset = run_fixture(); graph = dataset.graph(G1)
            if extra: graph.add((WHOLE, BFO.BFO_0000117, EX.unresolvedEpisode))
            else: graph.remove((WHOLE, RDF.type, BFO.BFO_0000015))
            self.assertEqual(score(dataset)['runs'], [])

    def test_ambiguous_origin_and_conflicting_terminal_are_not_chosen(self):
        for fault in ('origin', 'out'):
            dataset = run_fixture(); graph = dataset.graph(G1)
            if fault == 'origin': graph.add((URIRef(str(EX.first) + '/code'), CCO.ont00001765, Literal('3B')))
            else: graph.add((EX.resolution2, RDF.type, BASE.OutProcess))
            self.assertEqual(score(dataset)['runs'], [])

    def test_missing_history_identifies_the_actual_counted_run(self):
        dataset = run_fixture()
        dataset.graph(G1).remove((WHOLE, RDF.type, BFO.BFO_0000015))
        result = score(dataset)
        self.assertEqual(result['coverage']['observedRunsWithoutResult'], 1)
        missing, = result['unresolvedRuns']
        self.assertEqual(missing['run'], str(EX.resolution2))
        self.assertEqual(missing['gaps'], ['MISSING_PERSONAL_SCORING_HISTORY'])

    def test_two_personal_histories_cannot_double_count_one_run(self):
        dataset = run_fixture()
        graph = dataset.graph(G1)
        other = EX['runner-trajectory/ambiguous-life']
        for _, predicate, obj in list(graph.triples((WHOLE, None, None))):
            graph.add((other, predicate, obj))
        result = score(dataset)
        self.assertEqual(result['runs'], [])
        missing, = result['unresolvedRuns']
        self.assertEqual(missing['gaps'], ['AMBIGUOUS_SCORING_HISTORY'])
        self.assertEqual(len(missing['trajectories']), 2)
        self.assertEqual(result['coverage']['observedRunsWithoutResult'], 1)

    def test_unresolved_member_does_not_disappear_from_dashboard_or_sql(self):
        dataset = run_fixture()
        graph = dataset.graph(G1)
        graph.add((EX.unresolvedRun, RDF.type, BASE.RunProcess))
        graph.add((EX.unresolvedRun, BFO.BFO_0000132, EX.pa2))
        source = bindings(dataset, [G1])
        rows = M.normalize_bindings(source, [G1])
        expected = M.live_result('run-construction-depth', rows, graph_count=1)
        self.assertEqual(len(expected['runs']), 1)
        self.assertEqual(len(expected['unresolvedRuns']), 1)
        with database() as connection:
            M.materialize_game(connection, G1, source)
            scope = {'gameSet':'regular_season', 'startDate':'2026-08-01', 'endDate':'2026-08-01'}
            response = M.query_sql(connection, {'view':'dashboard'}, scope)
            actual, = [r for r in response['metrics'] if r['metricId'] == 'run-construction-depth']
            self.assertEqual(actual, expected)


if __name__ == '__main__': unittest.main()
