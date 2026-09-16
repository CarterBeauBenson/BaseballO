import unittest

from test_metric_suite_serving import M, G1, G2, database, bindings, fixture
from test_run_construction_serving import run_fixture


class MetricDashboard(unittest.TestCase):
    def test_dashboard_uses_the_existing_materialized_metric_contract(self):
        import copy
        from test_serving_layer import MODULE
        contract = MODULE.load_object(MODULE.CONTRACT)
        request = {'route':'metric-suite','view':'dashboard'}
        MODULE.require_materialized_route_admission(request, contract)
        for key in ('liveAvailability', 'schema', 'implementation'):
            wrong = copy.deepcopy(contract)
            wrong['metricSuite'][key] = 'unsupported'
            with self.assertRaises(ValueError): MODULE.require_materialized_route_admission(request, wrong)
        with self.assertRaises(ValueError):
            MODULE.require_materialized_route_admission({**request, 'metricId':'fake'}, contract)

    def test_shared_selection_matches_every_individual_metric_and_sql(self):
        source = bindings(run_fixture(), [G1])
        rows = M.normalize_bindings(source, [G1])
        expected = M.selected_results({'view':'dashboard'}, rows, graph_count=1)
        self.assertEqual(len(expected['metrics']), 20)
        for result in expected['metrics']:
            self.assertEqual(result, M.live_result(result['metricId'], rows, graph_count=1))
        depth = next(r for r in expected['metrics'] if r['metricId']=='run-construction-depth')
        self.assertEqual(depth['runs'][0]['value'], M.exact(3))
        self.assertIsNone(depth['value'])
        with database() as connection:
            M.materialize_game(connection, G1, source)
            M.materialize_game(connection, G2, bindings(fixture(graph=G2, decisions=()), [G2]))
            scope = {'gameSet':'regular_season','startDate':'2026-08-01','endDate':'2026-08-01'}
            result = M.query_sql(connection, {'view':'dashboard'}, scope)
            # SQL adds independent schedule/source admission. Compare the
            # shared request with each separately selected SQL metric; raw
            # graph inventory is deliberately not a population certificate.
            for metric in result['metrics']:
                single=M.query_sql(connection,{'metricId':metric['metricId']},scope)['metric']
                self.assertEqual(metric,single)
                self.assertFalse(metric.get('playerPopulationComplete',False))
                self.assertEqual(metric.get('playerResults',[]),[])
            self.assertEqual(result['graphCount'], 1)
            # A single missing metric invalidates the dashboard's SQL selection.
            connection.execute('DELETE FROM metric_suite_result WHERE graph_iri=? AND metric_id=?', (G1,'paq-2'))
            with self.assertRaises(M.EvidenceError): M.query_sql(connection, {'view':'dashboard'}, scope)

    def test_unknown_or_ambiguous_selection_does_not_expand_to_all_metrics(self):
        for request in ({}, {'view':'other'}, {'view':'dashboard','metricId':'tfs'}, {'metricId':'fake'}):
            with self.assertRaises(M.EvidenceError): M.requested_metric_ids(request)

    def test_empty_selection_keeps_twenty_unavailable_scores(self):
        results = M.selected_results({'view':'dashboard'}, [], graph_count=0)['metrics']
        self.assertEqual(len(results), 20)
        self.assertTrue(all(r['value'] is None and r['coverage']['games']==0 for r in results))


if __name__ == '__main__': unittest.main()
