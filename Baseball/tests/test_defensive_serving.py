"""Existing-term defensive evidence and exact SQL; no source admission claims."""
import unittest

from rdflib import Namespace, RDF, URIRef

from test_metric_suite_serving import M, G1, G2, fixture, bindings, database

BASE=Namespace('https://baseballontology.org/')
BFO=Namespace('http://purl.obolibrary.org/obo/')
CCO=Namespace('https://www.commoncoreontologies.org/')
EX=Namespace('urn:test:101:')
P1=URIRef('https://baseballontology.org/data/player/1')
P2=URIRef('https://baseballontology.org/data/player/2')
SCOPE=dict(startDate='2026-08-01',endDate='2026-08-01',gameSet='regular_season')
PROOF=dict(status='admitted',sourceReconciled=True,graphConforms=True,orderComplete=True)


def defense_fixture():
    data=fixture(decisions=());g=data.graph(G1)
    for player in (P1,P2):
        role=URIRef(str(player)+'/role/fielder');teamrole=URIRef(str(player)+'/team/1/role/player')
        for triple in [(role,RDF.type,BASE.FielderRole),(role,BFO.BFO_0000197,player),
            (EX.game,BFO.BFO_0000055,teamrole),(teamrole,RDF.type,BASE.PlayerRole),
            (teamrole,BFO.BFO_0000197,player),(teamrole,CCO.ont00001992,EX.team),
            (EX.teamRole,RDF.type,BASE.HomeTeamRole),(EX.teamRole,BFO.BFO_0000197,EX.team),
            (EX.teamRole,BFO.BFO_0000054,EX.game)]:g.add(triple)
    acts=[('field',BASE.FieldingAttemptAct,P1,'throw'),('throw',BASE.ThrowAct,P1,'catch'),
          ('catch',BASE.CatchAttemptAct,P2,'tag'),('tag',BASE.TagAttemptAct,P2,None)]
    for key,kind,player,successor in acts:
        for triple in [(EX[key],RDF.type,kind),(EX[key],BFO.BFO_0000132,EX.play),
            (EX[key],CCO.ont00001833,player),
            (EX[key],BFO.BFO_0000055,URIRef(str(player)+'/role/fielder'))]:g.add(triple)
        if successor:g.add((EX[key],BFO.BFO_0000063,EX[successor]))
    # Optional inferred superclass typing represents the same performance.
    g.add((EX.catch,RDF.type,BASE.FieldingAttemptAct))
    g.add((EX.second,RDF.type,BASE.BattedBallPlayProcess));g.add((EX.second,BFO.BFO_0000132,EX.pa))
    for triple in [(EX.catch2,RDF.type,BASE.CatchAttemptAct),(EX.catch2,BFO.BFO_0000132,EX.second),
        (EX.catch2,CCO.ont00001833,P1),(EX.catch2,BFO.BFO_0000055,URIRef(str(P1)+'/role/fielder'))]:g.add(triple)
    return data


def rows(data):return M.normalize_bindings(bindings(data,[G1]),[G1])


def summary(source,metric='resolution-depth',proof=None,**changes):
    proof=PROOF if proof is None else proof
    inputs=M.defensive_game_inputs(source,graph=G1,admission=proof)
    args=dict(graphs=[G1],date_scope=SCOPE,schedule=dict(complete=True),roster_admissions={G1:[PROOF]})
    args.update(changes)
    return M.defensive_players(metric,[inputs],source,**args)


class DefensiveServing(unittest.TestCase):
    def test_query_preserves_complete_plays_distinct_acts_and_actual_agents(self):
        source=rows(defense_fixture())
        inputs=M.defensive_game_inputs(source,graph=G1,admission=PROOF)
        self.assertTrue(inputs['complete']);self.assertTrue(inputs['orderComplete'])
        self.assertEqual(sorted(len(r['acts']) for r in inputs['resolutions']),[1,4])
        first,second=summary(source)['playerResults']
        self.assertEqual((first['player'],first['value']),(str(P1),M.exact(M.Fraction(5,2))))
        self.assertEqual((second['player'],second['value']),(str(P2),M.exact(4)))
        self.assertNotIn('plateAppearances',second)
        self.assertEqual(summary(source,'defender-breadth')['playerResults'][0]['value'],M.exact(M.Fraction(3,2)))

    def test_repeated_performance_does_not_collapse_to_fielder_credit(self):
        data=defense_fixture();g=data.graph(G1)
        for triple in [(EX.throwAgain,RDF.type,BASE.ThrowAct),(EX.throwAgain,BFO.BFO_0000132,EX.play),
            (EX.throwAgain,CCO.ont00001833,P2),(EX.throwAgain,BFO.BFO_0000055,URIRef(str(P2)+'/role/fielder')),
            (EX.tag,BFO.BFO_0000063,EX.throwAgain)]:g.add(triple)
        source=rows(data)
        self.assertEqual(summary(source)['playerResults'][1]['value'],M.exact(5))
        self.assertEqual(summary(source,'defender-breadth')['playerResults'][1]['value'],M.exact(2))

    def test_missing_acts_agent_or_role_never_shrinks_complete_population(self):
        for fault in ('acts','agent','role','conflicting-agent'):
            data=defense_fixture();g=data.graph(G1)
            if fault=='acts':g.remove((EX.catch2,RDF.type,None))
            elif fault=='agent':g.remove((EX.catch,CCO.ont00001833,None))
            elif fault=='role':g.remove((EX.catch,BFO.BFO_0000055,None))
            else:g.add((EX.catch,CCO.ont00001833,P1))
            result=summary(rows(data))
            self.assertFalse(result['playerPopulationComplete'],fault)
            self.assertEqual(result['playerResults'],[],fault)

    def test_order_admission_is_independent_of_agent_breadth(self):
        source=rows(defense_fixture())
        self.assertTrue(summary(source,'defender-breadth',proof=dict(PROOF,orderComplete=False))['playerPopulationComplete'])
        self.assertEqual(summary(source,proof=dict(PROOF,orderComplete=False))['playerSummaryGaps'],['DEFENSIVE_ORDER'])
        for successor in (EX.field,EX.outside):
            data=defense_fixture();data.graph(G1).add((EX.tag,BFO.BFO_0000063,successor))
            source=rows(data)
            self.assertTrue(summary(source,'defender-breadth')['playerPopulationComplete'])
            self.assertFalse(summary(source)['playerPopulationComplete'])

    def test_census_schedule_and_independent_roster_admission_required(self):
        source=rows(defense_fixture())
        for changes in (dict(proof={}),dict(schedule=dict(complete=False)),dict(roster_admissions={}),
                        dict(graphs=[G1,G2])):
            self.assertFalse(summary(source,**changes)['playerPopulationComplete'])
        self.assertFalse(summary([r for r in source if r['kind']!='player_team_game'])['playerPopulationComplete'])

    def test_foreign_graph_and_conflicting_game_scope_rejected(self):
        source=rows(defense_fixture());source.append(dict(source[0],graph=G2))
        with self.assertRaisesRegex(M.EvidenceError,'escaped'):summary(source)
        source=rows(defense_fixture());play=next(r for r in source if r['kind']=='batted_play')
        source.append(dict(play,game='urn:wrong:game'))
        with self.assertRaisesRegex(M.EvidenceError,'scope'):summary(source)

    def test_sql_retains_exact_inputs_and_hash_bound_admissions(self):
        data=defense_fixture();source=bindings(data,[G1])
        with database() as conn:
            M.materialize_game(conn,G1,source,defensive_admission=dict(PROOF,depth=999),scoring_run_admission=PROOF)
            payload=M._json(dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)]))
            conn.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',('2026-08-01',payload,M._hash(payload)))
            for metric in ('resolution-depth','defender-breadth'):
                result=M.query_sql(conn,dict(metricId=metric),SCOPE)['metric']
                self.assertTrue(result['playerPopulationComplete'])
                self.assertEqual(result['playerResults'],summary(rows(data),metric)['playerResults'])
                dashboard=M.query_sql(conn,dict(view='dashboard'),SCOPE)
                self.assertEqual(next(r for r in dashboard['metrics'] if r['metricId']==metric),result)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
            conn.execute("UPDATE metric_suite_defensive_admission SET proof_sha256='bad'")
            with self.assertRaisesRegex(M.EvidenceError,'defensive admission checksum'):
                M.query_sql(conn,dict(metricId='resolution-depth'),SCOPE)

    def test_materialization_without_admission_retains_visible_gap(self):
        with database() as conn:
            M.materialize_game(conn,G1,bindings(defense_fixture(),[G1]))
            result=M.read_results(conn,G1,'resolution-depth')[0]
            self.assertFalse(result['defensiveInputs']['complete'])
            self.assertEqual(result['defensiveInputs']['gaps'],['DEFENSIVE_POPULATION'])


if __name__=='__main__':unittest.main()
