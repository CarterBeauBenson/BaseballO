"""SQL building blocks versus the retained graph-evidence calculation oracle."""
from contextlib import ExitStack
import sqlite3
import unittest
from unittest.mock import patch

from test_metric_suite_serving import M, G1, G2, bindings, fixture, pitch_review_fixture, database
from test_batting_progress_players import fixture as progress_fixture, PROOF, SCOPE
from test_defensive_serving import defense_fixture, PROOF as DEFENSE_PROOF
from test_run_construction_serving import run_fixture
from test_recovery_players import sample, database as season_database, SCOPE as SEASON_SCOPE


def schedule(conn, day='2026-08-01', game='101'):
    text=M._json(dict(completeResponse=True,games=[dict(gamePk=game,gameType='R',final=True,unplayed=False)]))
    conn.execute('INSERT OR REPLACE INTO metric_suite_schedule_coverage VALUES (?,?,?)',(day,text,M._hash(text)))


def scores(result):
    return {k:v for k,v in result.items() if k!='buildingBlockCoverage'}


class MetricBlocks(unittest.TestCase):
    def test_all_metrics_equal_the_evidence_reader_across_distinct_graph_shapes(self):
        cases=[(pitch_review_fixture(),{}),(run_fixture(),{}),
            (progress_fixture(),dict(batting_admission=PROOF,runner_resolution_admission=PROOF)),
            (defense_fixture(),dict(defensive_admission=DEFENSE_PROOF,scoring_run_admission=PROOF))]
        for source,proofs in cases:
            with self.subTest(proofs=proofs),database() as conn:
                M.materialize_game(conn,G1,bindings(source,[G1]),**proofs)
                M.materialize_game(conn,G2,bindings(fixture(graph=G2),[G2]))
                schedule(conn);schedule(conn,'2026-08-02','102')
                for scope in (SCOPE,dict(SCOPE,endDate='2026-08-02')):
                    old=M.query_sql(conn,{'view':'dashboard'},scope,_use_blocks=False)
                    new=M.query_sql(conn,{'view':'dashboard'},scope)
                    self.assertEqual(scores(new),scores(old))
                    self.assertEqual(set(new['buildingBlockCoverage']),{'contribution','defense','paq21','progress','recovery'})

    def test_request_reads_no_raw_evidence_or_whole_game_result_and_runs_no_graph_kernels(self):
        with database() as conn:
            M.materialize_game(conn,G1,bindings(progress_fixture(),[G1]),
                batting_admission=PROOF,runner_resolution_admission=PROOF)
            schedule(conn)
            def authorize(operation, table, column, database_name, trigger):
                if operation==sqlite3.SQLITE_READ and table in {'metric_suite_evidence','metric_suite_result'}:
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            conn.set_authorizer(authorize)
            with ExitStack() as stack:
                for name in ('run_kernel','batting_progress_evidence','runner_boundary_states',
                             'run_construction_evidence','loaded_award_consequences','recovery_histories'):
                    stack.enter_context(patch.object(M,name,side_effect=AssertionError('request repeated '+name)))
                result=M.query_sql(conn,{'view':'dashboard'},SCOPE)
            self.assertTrue(next(r for r in result['metrics'] if r['metricId']=='offensive-reach')['playerPopulationComplete'])

    def test_missing_or_modified_inputs_never_reduce_the_population_silently(self):
        for change in (
            "DELETE FROM metric_suite_input_row WHERE family='progress' AND rowid=(SELECT MIN(rowid) FROM metric_suite_input_row WHERE family='progress')",
            "UPDATE metric_suite_input_row SET eligible=0 WHERE family='progress'",
            "UPDATE metric_suite_scope_fact SET record_sha256='bad'",
            "DELETE FROM metric_suite_scope_fact WHERE rowid=(SELECT MIN(rowid) FROM metric_suite_scope_fact)",
            "UPDATE metric_suite_evidence SET binding_sha256='bad' WHERE rowid=(SELECT MIN(rowid) FROM metric_suite_evidence)",
        ):
            with self.subTest(change=change),database() as conn:
                M.materialize_game(conn,G1,bindings(progress_fixture(),[G1]),
                    batting_admission=PROOF,runner_resolution_admission=PROOF)
                schedule(conn);conn.execute(change)
                with self.assertRaises(M.EvidenceError):M.query_sql(conn,{'view':'dashboard'},SCOPE)

    def test_individual_progress_cards_keep_the_dashboard_contribution_dependencies(self):
        from test_batting_progress_players import continuation_fixture
        with database() as conn:
            M.materialize_game(conn,G1,bindings(continuation_fixture(),[G1]),
                batting_admission=PROOF,runner_resolution_admission=PROOF)
            schedule(conn)
            dashboard=M.query_sql(conn,{'view':'dashboard'},SCOPE)
            for metric_id in ('offensive-reach','hidden-help-rate'):
                with self.subTest(metric=metric_id):
                    card=next(r for r in dashboard['metrics'] if r['metricId']==metric_id)
                    self.assertEqual(M.query_sql(conn,{'metricId':metric_id},SCOPE)['metric'],card)

    def test_nifi_prepares_reference_ranks_and_historical_cutoffs_keep_their_own_population(self):
        samples=[sample(101,0),sample(102,2),sample(103,4)]
        with season_database(samples) as conn:
            expected=M.query_sql(conn,{'metricId':'recovery-quality'},SEASON_SCOPE,_use_blocks=False)
            proofs=M.materialize_reference_ranks(conn)
            self.assertTrue(next(r for r in proofs if r['metricId']=='recovery-quality')['populationComplete'])
            with patch.object(M,'percentiles',side_effect=AssertionError('already ranked')):
                self.assertEqual(scores(M.query_sql(conn,{'metricId':'recovery-quality'},SEASON_SCOPE)),scores(expected))
            past=dict(SEASON_SCOPE,endDate='2026-08-02')
            with patch.object(M,'percentiles',wraps=M.percentiles) as compute:
                result=M.query_sql(conn,{'metricId':'recovery-quality'},past)
                self.assertEqual(compute.call_count,1)
                self.assertEqual(result['metric']['referencePopulations'][0]['games'],2)
                self.assertEqual(scores(result),scores(M.query_sql(conn,{'metricId':'recovery-quality'},past,_use_blocks=False)))
            record,=M.read_results(conn,G1,'recovery-quality')
            M.store_result(conn,G1,'recovery-quality','game-scope',record)
            self.assertEqual(conn.execute('SELECT count(*) FROM metric_suite_reference').fetchone()[0],0)
            with patch.object(M,'percentiles',wraps=M.percentiles) as compute:
                M.query_sql(conn,{'metricId':'recovery-quality'},SEASON_SCOPE)
                self.assertEqual(compute.call_count,1)

    def test_rank_checksum_and_independent_schedule_still_apply_after_preparation(self):
        samples=[sample(101,0),sample(102,2),sample(103,4)]
        with season_database(samples) as conn:
            M.materialize_reference_ranks(conn)
            conn.execute("UPDATE metric_suite_reference_rank SET rank_sha256='bad' WHERE metric_id='recovery-quality'")
            with self.assertRaisesRegex(M.EvidenceError,'checksum'):
                M.query_sql(conn,{'metricId':'recovery-quality'},SEASON_SCOPE)
        with season_database(samples) as conn:
            M.materialize_reference_ranks(conn)
            conn.execute("DELETE FROM metric_suite_schedule_coverage WHERE official_date='2026-07-01'")
            result=M.query_sql(conn,{'metricId':'recovery-quality'},SEASON_SCOPE)['metric']
            self.assertEqual(result['gaps'],['REFERENCE_POPULATION_INCOMPLETE'])

    def test_paq21_reuses_both_season_rank_passes_without_changing_the_selected_mean(self):
        from test_paq21_serving import prepared
        with prepared([sample(101,2),sample(102,2),sample(103,2)]) as conn:
            expected=M.query_sql(conn,{'metricId':'paq-2.1'},SEASON_SCOPE,_use_blocks=False)
            proofs=M.materialize_reference_ranks(conn)
            self.assertTrue(next(r for r in proofs if r['metricId']=='paq-2.1')['populationComplete'])
            with patch.object(M,'percentiles',side_effect=AssertionError('already ranked')), patch.object(
                    M,'paq21_population',side_effect=AssertionError('already ranked')):
                result=M.query_sql(conn,{'metricId':'paq-2.1'},SEASON_SCOPE)
            self.assertEqual(scores(result),scores(expected))
            self.assertEqual(result['metric']['playerResults'][0]['value'],M.exact(75))


if __name__=='__main__':unittest.main()
