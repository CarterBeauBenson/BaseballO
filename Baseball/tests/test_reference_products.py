import importlib.util
from contextlib import ExitStack
from pathlib import Path
import unittest
from unittest.mock import patch
from test_metric_blocks import M, sample, season_database, SEASON_SCOPE, scores
from test_paq21_serving import prepared
from test_player_ranges import Q

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('references',ROOT/'serving/reference_products.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


class References(unittest.TestCase):
    def complete_database(self):
        db=prepared([sample(101,0),sample(102,2),sample(103,4)])
        self.addCleanup(db.close)
        # Consumer fixture with admitted contribution/state inputs. The
        # independent legacy reducers remain the numerical oracle.
        for index,(graph,) in enumerate(db.execute('SELECT graph_iri FROM game_dimension ORDER BY graph_iri')):
            recovery,=M.read_results(db,graph,'recovery-quality')
            pa,=recovery['recoveryInputs']['plateAppearances']
            contribution,=M.read_results(db,graph,'tfs')
            contribution['contributionInputs']=dict(complete=True,plateAppearances=[dict(pa,
                score=M.available(index),comparisonState=dict(boundary=M.policies()['paqAComparisonBoundary'],
                occupiedBases=[],outs=0,evidence=['fixture']))])
            M.store_result(db,graph,'tfs','game-scope',contribution)
        return db

    def assert_same_player_scores(self,actual,expected):
        for field in ('status','value','gaps','playerPopulationComplete','playerSummaryGaps','referencePopulations'):
            self.assertEqual(actual.get(field),expected.get(field),field)
        fields=('player','metricId','status','value','dateScope','completeParticipation',
                'plateAppearances','teamGames','graphs','aggregate')
        self.assertEqual([{k:p[k] for k in fields} for p in actual['playerResults']],
                         [{k:p[k] for k in fields} for p in expected['playerResults']])

    def test_prepared_player_ranges_match_all_four_existing_reducers_without_reading_pa_inputs(self):
        db=self.complete_database()
        cases=[]
        for metric in ('paq-2','paq-a','recovery-quality','paq-2.1'):
            for start,end in [('2026-08-01','2026-08-02'),('2026-08-02','2026-08-03'),('2026-08-03','2026-08-03')]:
                scope=dict(SEASON_SCOPE,startDate=start,endDate=end)
                expected=M.query_sql(db,{'metricId':metric},scope,_use_blocks=False)['metric']
                self.assertTrue(expected['playerPopulationComplete'],expected)
                cases.append((metric,scope,expected))
        R.prepare(M,db)
        with ExitStack() as stack:
            for obj,name in [(M,'query_sql'),(M,'percentiles'),(M,'read_results'),
                             (M._blocks,'read_scope'),(M._blocks,'read_inputs')]:
                stack.enter_context(patch.object(obj,name,side_effect=AssertionError('request reconstruction')))
            for metric,scope,expected in cases:
                with self.subTest(metric=metric,scope=scope):
                    graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE official_date BETWEEN ? AND ?',
                        (scope['startDate'],scope['endDate']))]
                    self.assertTrue(Q.reference_available(M,db,metric,scope))
                    actual=Q.reference_players(M,db,metric,scope,graphs)
                    self.assert_same_player_scores(actual,expected)

    def test_known_ineligible_selection_stays_empty_and_unprepared_reference_stays_withheld(self):
        db=self.complete_database()
        graph='https://w3id.org/baseball/graph/game/103'
        for metric,field in [('recovery-quality','recoveryInputs'),('paq-2.1','paq21Inputs')]:
            stored,=M.read_results(db,graph,metric)
            stored[field]['plateAppearances'][0]['twoStrikeEligible']=False
            M.store_result(db,graph,metric,'game-scope',stored)
        scope=dict(SEASON_SCOPE,startDate='2026-08-03')
        expected={metric:M.query_sql(db,{'metricId':metric},scope,_use_blocks=False)['metric']
                  for metric in ('recovery-quality','paq-2.1')}
        R.prepare(M,db)
        for metric,wanted in expected.items():
            actual=Q.reference_players(M,db,metric,scope,[graph])
            self.assert_same_player_scores(actual,wanted)
            self.assertTrue(actual['playerPopulationComplete']);self.assertEqual(actual['playerResults'],[])
        db.execute('DELETE FROM dashboard_reference_players')
        actual=Q.reference_players(M,db,'recovery-quality',scope,[graph])
        self.assertEqual(actual['playerSummaryGaps'],['SEASON_REFERENCE_UNAVAILABLE'])

    def test_player_product_and_reference_schedule_remain_checked(self):
        db=self.complete_database();R.prepare(M,db)
        graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE official_date>=?',(SEASON_SCOPE['startDate'],))]
        db.execute("UPDATE dashboard_reference_players SET payload_sha256='bad'")
        with self.assertRaisesRegex(M.EvidenceError,'checksum'):
            Q.reference_players(M,db,'recovery-quality',SEASON_SCOPE,graphs)
        db.execute("DELETE FROM metric_suite_schedule_coverage WHERE official_date='2026-07-01'")
        result=Q.reference_players(M,db,'recovery-quality',SEASON_SCOPE,graphs)
        self.assertEqual(result['playerSummaryGaps'],['REFERENCE_POPULATION_INCOMPLETE'])

    def test_unrankable_state_cohort_only_blocks_ranges_containing_its_pas(self):
        db=self.complete_database();graph='https://w3id.org/baseball/graph/game/101'
        stored,=M.read_results(db,graph,'tfs')
        stored['contributionInputs']['plateAppearances'][0]['comparisonState']['outs']=1
        M.store_result(db,graph,'tfs','game-scope',stored)
        scopes=[SEASON_SCOPE,dict(SEASON_SCOPE,startDate='2026-08-01')]
        expected=[M.query_sql(db,{'metricId':'paq-a'},scope,_use_blocks=False)['metric'] for scope in scopes]
        self.assertTrue(expected[0]['playerPopulationComplete'])
        self.assertFalse(expected[1]['playerPopulationComplete'])
        R.prepare(M,db)
        for scope,wanted in zip(scopes,expected):
            graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE official_date BETWEEN ? AND ?',
                (scope['startDate'],scope['endDate']))]
            self.assert_same_player_scores(Q.reference_players(M,db,'paq-a',scope,graphs),wanted)

    def test_every_historical_cutoff_matches_exact_existing_math_without_request_ranking(self):
        with season_database([sample(101,0),sample(102,2),sample(103,4)]) as db:
            scopes=[dict(SEASON_SCOPE,endDate=day) for day in ('2026-08-02','2026-08-03','2026-08-04')]
            expected=[scores(M.query_sql(db,{'metricId':'recovery-quality'},scope,_use_blocks=False)) for scope in scopes]
            R.prepare(M,db)
            with R.prepared_ranks(M,db),patch.object(M,'percentiles',side_effect=AssertionError('HTTP rank calculation')):
                for scope,wanted in zip(scopes,expected):
                    self.assertEqual(scores(M.query_sql(db,{'metricId':'recovery-quality'},scope)),wanted)
            db.execute("UPDATE dashboard_reference SET payload_sha256='bad'")
            with R.prepared_ranks(M,db),self.assertRaisesRegex(M.EvidenceError,'checksum'):
                M.query_sql(db,{'metricId':'recovery-quality'},scopes[0])

    def test_missing_preparation_does_not_run_expensive_math_on_request(self):
        with season_database([sample(101,0),sample(102,2)]) as db:
            R.initialize(db)
            with R.prepared_ranks(M,db),patch.object(M,'percentiles',side_effect=AssertionError('request calculation')):
                with self.assertRaisesRegex(M.EvidenceError,'NiFi preparation'):
                    M.query_sql(db,{'metricId':'recovery-quality'},dict(SEASON_SCOPE,endDate='2026-08-02'))

    def test_withheld_admission_short_circuits_historical_row_decoding(self):
        with season_database([sample(101,0),sample(102,2)]) as db:
            text=M._json(dict(status='withheld',issues=[dict(code='ORIGINAL_SOURCE_ISSUE')]))
            db.execute('UPDATE metric_suite_admission SET proof_json=?,proof_sha256=?',(text,M._hash(text)))
            with patch.object(M._blocks,'read_scope',side_effect=AssertionError('decoding a rejected population')):
                results=R.prepare(M,db)
            self.assertTrue(results)
            self.assertTrue(all(not r['populationComplete'] and r['gaps']==['COMPLETE_BATTING_QUALIFICATION'] for r in results))
            self.assertEqual(db.execute('SELECT count(*) FROM dashboard_reference').fetchone()[0],0)


if __name__=='__main__':unittest.main()
