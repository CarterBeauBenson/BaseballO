import importlib.util
import copy
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
    def test_combined_refresh_rebuilds_internal_recovery_ranks_and_preserves_offense(self):
        db=self.complete_database()
        R.prepare(M,db)
        scope=dict(SEASON_SCOPE,startDate='2026-08-03',endDate='2026-08-03')
        graph='https://w3id.org/baseball/graph/game/103'
        before=Q.reference_players(M,db,'paq-2.1',scope,[graph])
        offensive=db.execute("SELECT * FROM dashboard_reference_players WHERE metric_id!='paq-2.1' ORDER BY metric_id,season,graph_set_sha256").fetchall()
        retained,=M.read_results(db,graph,'paq-2.1')
        retained['paq21Inputs']['plateAppearances'][0]['recoveryInput']=M.exact(-1)
        M.store_result(db,graph,'paq-2.1','game-scope',retained)
        expected=M.query_sql(db,{'metricId':'paq-2.1'},scope,_use_blocks=False)['metric']
        self.assertNotEqual(before['value'],expected['value'])
        R.prepare(M,db,metric_ids={'paq-2.1'})
        actual=Q.reference_players(M,db,'paq-2.1',scope,[graph])
        self.assert_same_player_scores(actual,expected)
        self.assertEqual(db.execute("SELECT * FROM dashboard_reference_players WHERE metric_id!='paq-2.1' ORDER BY metric_id,season,graph_set_sha256").fetchall(),offensive)

    def individual(self,db,graph):
        rows=M._blocks.read_scope(M._block_api(),db,[graph])
        return dict(rosterComplete=True,plateAppearanceInventoryComplete=True,
            players=[dict(player=p,status='admitted') for p in sorted(
                {r['player'] for r in rows if r['kind']=='player_team_game'})])

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

    def test_complete_individual_batting_population_preserves_all_four_reference_results(self):
        db=self.complete_database()
        graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension ORDER BY graph_iri')]
        metrics=('paq-2','paq-a','recovery-quality','paq-2.1')
        expected={metric:M.query_sql(db,{'metricId':metric},SEASON_SCOPE,_use_blocks=False)['metric'] for metric in metrics}
        graph=graphs[0];individual=self.individual(db,graph)
        text=M._json(dict(status='withheld',issues=[dict(code='ORIGINAL_WHOLE_GAME_FAILURE')]))
        db.execute('UPDATE metric_suite_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),graph))
        R.prepare(M,db,player_admissions={graph:individual})
        selected=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE official_date BETWEEN ? AND ?',
            (SEASON_SCOPE['startDate'],SEASON_SCOPE['endDate']))]
        for metric,wanted in expected.items():
            self.assert_same_player_scores(Q.reference_players(M,db,metric,SEASON_SCOPE,selected),wanted)
        # An individual census is not a fabricated replacement whole-game proof.
        self.assertEqual(db.execute('SELECT proof_json FROM metric_suite_admission WHERE graph_iri=?',(graph,)).fetchone()[0],text)

    def test_individual_reference_requires_every_player_inventory_and_exact_rdf_roster(self):
        for fault in ('player','inventory','roster','missing'):
            with self.subTest(fault=fault):
                db=self.complete_database();graph=db.execute('SELECT graph_iri FROM game_dimension LIMIT 1').fetchone()[0]
                individual=self.individual(db,graph)
                if fault=='player':individual['players'][0]['status']='withheld'
                elif fault=='inventory':individual['plateAppearanceInventoryComplete']=False
                elif fault=='roster':individual['rosterComplete']=False
                else:individual={}
                text=M._json(dict(status='withheld'))
                db.execute('UPDATE metric_suite_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),graph))
                results=R.prepare(M,db,player_admissions={graph:individual})
                self.assertTrue(all(not r['populationComplete'] for r in results))
        db=self.complete_database();graph=db.execute('SELECT graph_iri FROM game_dimension LIMIT 1').fetchone()[0]
        individual=self.individual(db,graph)
        individual['players'].append(dict(player='urn:absent-player',status='admitted'))
        rows=M._blocks.read_scope(M._block_api(),db,[graph])
        with self.assertRaisesRegex(M.EvidenceError,'complete RDF roster'):
            M.batting_qualification(rows,graphs=[graph],admissions={},date_scope=SEASON_SCOPE,
                player_admissions={graph:individual})

    def test_recovery_inputs_recover_from_retained_sql_without_replacing_count_requirements(self):
        with season_database([sample(101,0),sample(102,2),sample(103,4)]) as db:
            graph=db.execute('SELECT graph_iri FROM game_dimension ORDER BY graph_iri LIMIT 1').fetchone()[0]
            expected=M.query_sql(db,{'metricId':'recovery-quality'},SEASON_SCOPE,_use_blocks=False)['metric']
            individual=self.individual(db,graph)
            original,=M.read_results(db,graph,'recovery-quality')
            broken=copy.deepcopy(original)
            broken['recoveryInputs']=dict(complete=False,plateAppearances=[],gaps=['OFFICIAL_PA_ADMISSION'])
            M.store_result(db,graph,'recovery-quality','game-scope',broken)
            text=M._json(dict(status='withheld'))
            db.execute('UPDATE metric_suite_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),graph))
            R.prepare(M,db,player_admissions={graph:individual})
            recovered,=M.read_results(db,graph,'recovery-quality')
            self.assertEqual(recovered['recoveryInputs'],original['recoveryInputs'])
            graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE official_date BETWEEN ? AND ?',
                (SEASON_SCOPE['startDate'],SEASON_SCOPE['endDate']))]
            self.assert_same_player_scores(Q.reference_players(M,db,'recovery-quality',SEASON_SCOPE,graphs),expected)
            db.execute('UPDATE metric_suite_count_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),graph))
            R.prepare(M,db,player_admissions={graph:individual})
            self.assertFalse(Q.reference_available(M,db,'recovery-quality',SEASON_SCOPE))

    def test_contribution_input_refresh_invalidates_only_its_player_partition(self):
        from test_contribution_sql import database,SCOPE
        with database() as db:
            graph=db.execute('SELECT graph_iri FROM game_dimension ORDER BY graph_iri LIMIT 1').fetchone()[0]
            individual=self.individual(db,graph)
            original,=M.read_results(db,graph,'tfs')
            expected=M.query_sql(db,{'metricId':'paq-2'},SCOPE,_use_blocks=False)['metric']
            broken=copy.deepcopy(original)
            broken['contributionInputs']=dict(complete=False,plateAppearances=[],gaps=['OFFICIAL_PA_POPULATION'])
            M.store_result(db,graph,'tfs','game-scope',broken)
            text=M._json(dict(status='withheld'))
            db.execute('UPDATE metric_suite_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),graph))
            db.execute('CREATE TABLE dashboard_player_partition(graph_iri TEXT PRIMARY KEY,input_sha256 TEXT)')
            db.executemany('INSERT INTO dashboard_player_partition VALUES (?,?)',[(graph,'old'),('other','unchanged')])
            R.prepare(M,db,player_admissions={graph:individual})
            recovered,=M.read_results(db,graph,'tfs')
            self.assertEqual(recovered['contributionInputs'],original['contributionInputs'])
            self.assertEqual(db.execute('SELECT * FROM dashboard_player_partition').fetchall(),[('other','unchanged')])
            graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE official_date BETWEEN ? AND ?',
                (SCOPE['startDate'],SCOPE['endDate']))]
            self.assert_same_player_scores(Q.reference_players(M,db,'paq-2',SCOPE,graphs),expected)
            db.execute('UPDATE metric_suite_boundary_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),graph))
            R.prepare(M,db,player_admissions={graph:individual})
            self.assertFalse(Q.reference_available(M,db,'paq-2',SCOPE))


if __name__=='__main__':unittest.main()
