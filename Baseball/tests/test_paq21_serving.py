"""Admitted dimension joins and complete-season SQL routing for PAQ-2.1."""
import copy
import unittest

from test_metric_suite_serving import M,G1
from test_recovery_players import sample,database,SCOPE,PROOF


def joined(pa,depth):
    contribution=dict(complete=True,plateAppearances=[dict(pa,score=dict(value=M.exact(1)))])
    recovery=dict(complete=True,plateAppearances=[pa])
    defense=dict(complete=True,resolutions=[dict(graph=pa['graph'],game=pa['game'],
        plateAppearance=pa['plateAppearance'],resolution=pa['plateAppearance']+'/contact',orderComplete=True,
        acts=[dict(act=str(i),agent='fielder',next=[str(i+1)] if i+1<depth else []) for i in range(depth)])])
    return contribution,recovery,defense


def prepared(samples):
    """Consumer fixture: proof-authorized inputs, never a production admission."""
    conn=database(samples)
    for depth,(graph,_) in enumerate(samples,1):
        recovery,=M.read_results(conn,graph,'recovery-quality');pa,=recovery['recoveryInputs']['plateAppearances']
        result,=M.read_results(conn,graph,'paq-2.1')
        result['paq21Inputs']=M.paq21_game_inputs(*joined(pa,depth))
        M.store_result(conn,graph,'paq-2.1','game-scope',result)
        proof=M._json(PROOF)
        for table in ('metric_suite_boundary_admission','metric_suite_runner_resolution_admission','metric_suite_defensive_admission'):
            conn.execute(f'UPDATE {table} SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(proof,M._hash(proof),graph))
    return conn


class Paq21Serving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.samples=[sample(101,2),sample(102,2),sample(103,2)]

    def query(self,conn):return M.query_sql(conn,dict(metricId='paq-2.1'),SCOPE)['metric']

    def pa(self):
        with database(self.samples) as conn:
            result,=M.read_results(conn,G1,'recovery-quality')
            return result['recoveryInputs']['plateAppearances'][0]

    def test_join_requires_same_pa_person_scope_and_component_admission(self):
        pa=self.pa();components=joined(pa,4)
        result=M.paq21_game_inputs(*components)
        self.assertTrue(result['complete']);row,=result['plateAppearances']
        self.assertEqual(row['depth'],4);self.assertNotIn('recovery',row)
        for index in range(3):
            broken=copy.deepcopy(components);broken[index]['complete']=False
            self.assertFalse(M.paq21_game_inputs(*broken)['complete'])
        broken=copy.deepcopy(components);broken[1]['plateAppearances'][0]['player']='other'
        self.assertEqual(M.paq21_game_inputs(*broken)['gaps'],['PAQ21_COMPONENT_PA_COVERAGE'])
        broken=copy.deepcopy(components);broken[2]['resolutions'][0]['plateAppearance']='other'
        self.assertEqual(M.paq21_game_inputs(*broken)['gaps'],['PAQ21_DEFENSIVE_PA_SCOPE'])

    def test_known_absence_is_not_zero_and_ambiguous_depth_is_not_a_maximum(self):
        components=joined(self.pa(),4);components[2]['resolutions']=[]
        result=M.paq21_game_inputs(*components);row,=result['plateAppearances']
        self.assertTrue(result['complete']);self.assertFalse(row['defensiveApplicable']);self.assertNotIn('depth',row)
        components=joined(self.pa(),4);components[2]['resolutions'][0]['orderComplete']=False
        self.assertEqual(M.paq21_game_inputs(*components)['gaps'],['DEFENSIVE_ORDER'])
        components=joined(self.pa(),4);other=copy.deepcopy(components[2]['resolutions'][0]);other['resolution']='second'
        components[2]['resolutions'].append(other)
        self.assertEqual(M.paq21_game_inputs(*components)['gaps'],['PAQ21_DEFENSIVE_PA_SCOPE'])

    def test_complete_season_depth_ties_rank_before_selected_mean(self):
        with prepared(self.samples) as conn:
            result=self.query(conn);self.assertTrue(result['playerPopulationComplete'],result)
            player,=result['playerResults']
            self.assertEqual(player['value'],M.exact(75))
            self.assertEqual(player['aggregate'],dict(kind='mean',sum=M.exact(150),count=2))
            self.assertEqual(player['plateAppearances'],2);self.assertEqual(player['teamGames'],2)
            ref,=result['referencePopulations'];self.assertEqual(ref['applicablePlateAppearances'],3)
            dashboard=M.query_sql(conn,dict(view='dashboard'),SCOPE)
            self.assertEqual(next(r for r in dashboard['metrics'] if r['metricId']=='paq-2.1'),result)

    def test_recovery_reference_precedes_defensive_applicability_filter(self):
        with prepared(self.samples) as conn:
            result,=M.read_results(conn,G1,'paq-2.1');pa,=result['paq21Inputs']['plateAppearances']
            pa['defensiveApplicable']=False;pa.pop('depth')
            M.store_result(conn,G1,'paq-2.1','game-scope',result)
            result=self.query(conn);ref,=result['referencePopulations']
            self.assertEqual(ref['recoveryEligiblePlateAppearances'],3)
            self.assertEqual(ref['applicablePlateAppearances'],2)
            self.assertEqual(result['playerResults'][0]['value'],M.exact(50))

    def test_missing_preselection_schedule_proof_or_input_never_shrinks_reference(self):
        for fault in ('schedule','proof','input'):
            with self.subTest(fault=fault),prepared(self.samples) as conn:
                if fault=='schedule':conn.execute("DELETE FROM metric_suite_schedule_coverage WHERE official_date='2026-07-01'")
                elif fault=='proof':conn.execute('DELETE FROM metric_suite_defensive_admission WHERE graph_iri=?',(G1,))
                else:
                    result,=M.read_results(conn,G1,'paq-2.1');result['paq21Inputs']['complete']=False
                    M.store_result(conn,G1,'paq-2.1','game-scope',result)
                result=self.query(conn);self.assertFalse(result['playerPopulationComplete']);self.assertEqual(result['playerResults'],[])

    def test_reference_proofs_and_scores_are_checksum_checked(self):
        for table,column in [('metric_suite_defensive_admission','proof_json'),('metric_suite_result','result_json')]:
            with self.subTest(table=table),prepared(self.samples) as conn:
                conn.execute(f'UPDATE {table} SET {column}=? WHERE graph_iri=?',('{}',G1))
                with self.assertRaisesRegex(M.EvidenceError,'checksum'):self.query(conn)

    def test_known_ineligible_selected_pas_have_no_invented_score(self):
        with prepared(self.samples) as conn:
            for graph,_ in self.samples[1:]:
                result,=M.read_results(conn,graph,'paq-2.1');pa,=result['paq21Inputs']['plateAppearances']
                pa['twoStrikeEligible']=False
                M.store_result(conn,graph,'paq-2.1','game-scope',result)
            # Keep two recovery-eligible reference observations; otherwise the
            # reference correctly has too few peers to assign a percentile.
            scope=dict(SCOPE,startDate='2026-08-03')
            graph=self.samples[1][0];result,=M.read_results(conn,graph,'paq-2.1')
            result['paq21Inputs']['plateAppearances'][0]['twoStrikeEligible']=True
            M.store_result(conn,graph,'paq-2.1','game-scope',result)
            result=M.query_sql(conn,dict(metricId='paq-2.1'),scope)['metric']
            self.assertTrue(result['playerPopulationComplete']);self.assertEqual(result['playerResults'],[])
            self.assertEqual(result['gaps'],['EMPTY_DENOMINATOR'])


if __name__=='__main__':unittest.main()
