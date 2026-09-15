"""C2 on accepted RDF paths, without using source indexes as temporal order."""
import unittest

from rdflib import Literal, RDF, XSD

from test_run_construction_serving import EX, WHOLE, run_fixture
from runner_pattern_fixture import BASE, BFO, CCO
from test_metric_suite_serving import M, G1, database, bindings


def times(graph, pa, minute):
    interval, start, end = EX[str(pa).rsplit('/', 1)[-1] + '/interval'], EX[str(pa).rsplit('/', 1)[-1] + '/start'], EX[str(pa).rsplit('/', 1)[-1] + '/end']
    graph.add((pa, BFO.BFO_0000199, interval))
    graph.add((interval, RDF.type, BFO.BFO_0000038))
    for instant, edge, value, suffix in ((start, BFO.BFO_0000222, minute, 'start-time'),
                                        (end, BFO.BFO_0000224, minute + 1, 'end-time')):
        graph.add((interval, edge, instant))
        graph.add((instant, RDF.type, BASE.BaseballEventTemporalInstant))
        stamp = EX[str(pa).rsplit('/', 1)[-1] + '/' + suffix]
        graph.add((stamp, RDF.type, BASE.BaseballTimestampICE))
        graph.add((stamp, CCO.ont00001916, instant))
        graph.add((stamp, CCO.ont00001808, pa))
        graph.add((stamp, CCO.ont00001767, Literal(f'2026-08-01T12:{value:02d}:00Z', datatype=XSD.dateTime)))


def boundary_fixture():
    dataset = run_fixture()
    graph = dataset.graph(G1)
    for pa, minute in ((EX.pa0, 0), (EX.pa1, 4), (EX.pa2, 8)):
        times(graph, pa, minute)
    for pa, minute in ((EX.between, 2), (EX.after, 10)):
        graph.add((pa, RDF.type, BASE.PlateAppearance))
        graph.add((pa, BFO.BFO_0000132, EX.half))
        times(graph, pa, minute)
    return dataset


def project(dataset):
    return M.runner_boundary_states(M.normalize_bindings(bindings(dataset, [G1]), [G1]))


class BoundaryServingTests(unittest.TestCase):
    def test_safe_state_is_projected_only_inside_supported_continuity_bounds(self):
        result = project(boundary_fixture())
        state, = result['states']
        self.assertEqual(state['plateAppearance'], str(EX.between))
        self.assertEqual(state['basePosition'], 1)
        self.assertEqual(state['sourceEvent'], str(EX.resolution0))
        self.assertFalse(state['completePlateAppearance'])
        self.assertFalse(state['populationComplete'])
        self.assertNotIn('creditProgress', state)
        self.assertIn(str(EX['between/start-time']), state['evidence'])

    def test_c2_reaches_sql_and_shared_dashboard_without_admitting_tfs(self):
        source = bindings(boundary_fixture(), [G1])
        rows = M.normalize_bindings(source, [G1])
        expected = M.live_result('tfs', rows, graph_count=1)
        self.assertEqual(expected['status'], 'unavailable')
        self.assertEqual(len(expected['runnerBoundaryStates']), 1)
        with database() as connection:
            M.materialize_game(connection, G1, source)
            scope = {'gameSet': 'regular_season', 'startDate': '2026-08-01', 'endDate': '2026-08-01'}
            selected = M.query_sql(connection, {'view': 'dashboard'}, scope)
            self.assertEqual(next(row for row in selected['metrics'] if row['metricId'] == 'tfs'), expected)

    def test_no_new_graph_statements_are_created(self):
        dataset = boundary_fixture()
        before = set(dataset.graph(G1))
        project(dataset)
        self.assertEqual(set(dataset.graph(G1)), before)

    def test_missing_exact_member_blocks_projection(self):
        dataset = boundary_fixture()
        dataset.graph(G1).remove((EX.resolution1, BFO.BFO_0000062, None))
        result = project(dataset)
        self.assertEqual(result['states'], [])
        self.assertEqual(result['coverage']['withheldHistories'][0]['gap'], 'PERSONAL_HISTORY_MEMBER_COVERAGE')

    def test_timestamp_must_designate_the_pa_boundary_itself(self):
        dataset = boundary_fixture()
        dataset.graph(G1).remove((EX['pa0/end-time'], CCO.ont00001916, None))
        self.assertEqual(project(dataset)['states'], [])

    def test_conflicting_and_naive_timestamps_do_not_establish_order(self):
        for literal in (Literal('2026-08-01T12:09:00Z', datatype=XSD.dateTime),
                        Literal('2026-08-01T12:00:00', datatype=XSD.dateTime)):
            dataset = boundary_fixture()
            graph = dataset.graph(G1)
            if str(literal).endswith('12:00:00'):
                graph.remove((EX['pa0/start-time'], CCO.ont00001767, None))
            graph.add((EX['pa0/start-time'], CCO.ont00001767, literal))
            self.assertEqual(project(dataset)['states'], [])

    def test_iri_order_cannot_replace_supported_time_order(self):
        dataset = boundary_fixture()
        graph = dataset.graph(G1)
        graph.remove((EX['pa0/end-time'], CCO.ont00001767, None))
        graph.add((EX['pa0/end-time'], CCO.ont00001767, Literal('2026-08-01T12:05:00Z', datatype=XSD.dateTime)))
        result = project(dataset)
        self.assertEqual(result['states'], [])
        self.assertEqual(result['coverage']['withheldHistories'][0]['gap'], 'OVERLAPPING_EPISODE_BOUNDS')

    def test_no_extension_past_last_episode_or_to_another_half(self):
        dataset = boundary_fixture()
        graph = dataset.graph(G1)
        graph.remove((EX.between, BFO.BFO_0000132, EX.half))
        graph.add((EX.otherHalf, RDF.type, BASE.HalfInning))
        graph.add((EX.otherHalf, BFO.BFO_0000132, EX.inning))
        graph.add((EX.between, BFO.BFO_0000132, EX.otherHalf))
        self.assertEqual(project(dataset)['states'], [])

    def test_unordered_same_pa_episodes_remain_withheld(self):
        dataset = boundary_fixture()
        graph = dataset.graph(G1)
        for subject, predicate, _ in list(graph.triples((None, BFO.BFO_0000132, EX.pa1))):
            graph.remove((subject, predicate, EX.pa1))
            graph.add((subject, predicate, EX.pa0))
        result = project(dataset)
        self.assertEqual(result['states'], [])
        self.assertEqual(result['coverage']['withheldHistories'][0]['gap'], 'UNSUPPORTED_WITHIN_PA_EPISODE_ORDER')

    def test_unknown_safe_destination_and_conflicting_outcome_are_not_carried(self):
        for missing in ('decision', 'out'):
            dataset = boundary_fixture()
            graph = dataset.graph(G1)
            if missing == 'decision':
                graph.remove((EX.resolution0, BFO.BFO_0000117, None))
            else:
                graph.add((EX.resolution0, RDF.type, BASE.OutProcess))
            self.assertEqual(project(dataset)['states'], [])

    def test_duplicate_wholes_do_not_produce_two_runner_states(self):
        dataset = boundary_fixture()
        graph = dataset.graph(G1)
        for _, predicate, value in list(graph.triples((WHOLE, None, None))):
            graph.add((EX['runner-trajectory/other'], predicate, value))
        result = project(dataset)
        self.assertEqual(result['states'], [])
        self.assertEqual(result['coverage']['ambiguousRunnerPAs'], 1)

    def test_literal_boundary_identity_and_untyped_timestamp_are_rejected(self):
        source = bindings(boundary_fixture(), [G1])
        row = next(row for row in source if 'paStart' in row)
        for field, value in (('paStartInstant', {'type': 'literal', 'value': 'start'}),
                             ('paStart', {'type': 'literal', 'value': row['paStart']['value']})):
            with self.assertRaises(M.EvidenceError):
                M.normalize_bindings([{**row, field: value}], [G1])


if __name__ == '__main__':
    unittest.main()
