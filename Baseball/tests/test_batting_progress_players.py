"""Complete RDF progress, exact selected-range player aggregation and negative cases."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Dataset, RDF, Literal, URIRef
from pyshacl import validate
from test_metric_suite_serving import M, G1, bindings, database
from runner_pattern_fixture import movement, BASE, BFO, CCO

spec=importlib.util.spec_from_file_location('progress_admission',M.ROOT/'sources/mlb-game/pipeline/runner-resolution-admission.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
GAME=URIRef('https://baseballontology.org/data/game/101')
P1=URIRef('https://baseballontology.org/data/player/1')
P2=URIRef('https://baseballontology.org/data/player/2')
SCOPE=dict(startDate='2026-08-01',endDate='2026-08-01',gameSet='regular_season')
PROOF=dict(status='admitted',sourceReconciled=True,graphConforms=True)


def fixture():
    data=Dataset();g=data.graph(G1)
    def iri(s):return URIRef(str(GAME)+'/'+s)
    g.add((GAME,RDF.type,BASE.BaseballGame));g.add((iri('inning'),BFO.BFO_0000132,GAME))
    g.add((iri('half'),BFO.BFO_0000132,iri('inning')))
    for p in (P1,P2):
        role=URIRef(str(p)+'/role/batter')
        g.add((role,RDF.type,BASE.BatterRole));g.add((role,BFO.BFO_0000197,p))
        team=iri('team');teamrole=URIRef(str(p)+'/role/team')
        g.add((GAME,BFO.BFO_0000055,teamrole));g.add((teamrole,RDF.type,BASE.PlayerRole))
        g.add((teamrole,BFO.BFO_0000197,p));g.add((teamrole,CCO.ont00001992,team))
        g.add((iri('home'),RDF.type,BASE.HomeTeamRole));g.add((iri('home'),BFO.BFO_0000197,team))
        g.add((iri('home'),BFO.BFO_0000054,GAME))
    for i,(player,result) in enumerate([(P1,BASE.SingleProcess),(P1,BASE.SacrificeFlyProcess),
                                       (P1,BASE.StrikeoutProcess),(P2,BASE.StrikeoutProcess)]):
        pa=iri('plate-appearance/'+str(i));act=URIRef(str(pa)+'/batter-act')
        g.add((pa,RDF.type,BASE.PlateAppearance));g.add((pa,BFO.BFO_0000132,iri('half')))
        g.add((act,RDF.type,BASE.BatterAct));g.add((act,BFO.BFO_0000132,pa))
        g.add((act,BFO.BFO_0000055,URIRef(str(player)+'/role/batter')))
        resultiri=URIRef(str(pa)+'/result');judgment=URIRef(str(pa)+'/judgment');decision=URIRef(str(pa)+'/decision')
        record=URIRef(str(pa)+'/record')
        g.add((resultiri,RDF.type,BASE.BaseballInstitutionalProcess));g.add((resultiri,RDF.type,result))
        g.add((resultiri,BFO.BFO_0000132,pa));g.add((judgment,RDF.type,BASE.BaseballAdjudicationAct))
        g.add((judgment,BFO.BFO_0000132,resultiri));g.add((judgment,CCO.ont00001986,decision))
        g.add((decision,RDF.type,BASE.BaseballDecisionICE));g.add((decision,CCO.ont00001808,resultiri))
        g.add((record,RDF.type,BASE.BaseballEventRecord))
        for entity in (resultiri,judgment,decision):g.add((record,CCO.ont00001808,entity))
        rr=URIRef(str(pa)+'/resolution');runact=URIRef(str(pa)+'/run-act')
        movement(g,rr,runact,pa,player,destination=iri('base/1') if i==0 else None)
        if i: g.add((rr,RDF.type,BASE.OutProcess))
        if i<2:
            contact=URIRef(str(pa)+'/contact');g.add((contact,RDF.type,BASE.BattedBallPlayProcess))
            g.add((contact,BFO.BFO_0000132,pa));g.add((contact,BFO.BFO_0000117,rr))
        if i==1:
            rr=URIRef(str(pa)+'/runner2');runact=URIRef(str(pa)+'/runner2-act')
            movement(g,rr,runact,pa,P2,origin=iri('base/3'))
            g.add((rr,RDF.type,BASE.RunProcess));g.add((contact,BFO.BFO_0000117,rr))
        if i==2:
            rr=URIRef(str(pa)+'/steal');runact=URIRef(str(pa)+'/steal-act')
            movement(g,rr,runact,pa,P2,origin=iri('base/1'),destination=iri('base/2'))
            g.add((runact,RDF.type,BASE.StealAttemptAct))
    for n in (1,2,3):
        g.add((iri('base-id/'+str(n)),RDF.type,CCO.ont00000649))
        g.add((iri('base-id/'+str(n)),CCO.ont00001916,iri('base/'+str(n))))
        g.add((iri('base-id/'+str(n)),CCO.ont00001765,Literal(str(n)+'B')))
    return data


def score(data,metric,**changes):
    rows=M.normalize_bindings(bindings(data,[G1]),[G1])
    q=M.batting_qualification(rows,graphs=[G1],admissions={G1:PROOF},date_scope=SCOPE,selected_games_complete=True)
    args=dict(graphs=[G1],admissions={G1:PROOF},qualification=q,date_scope=SCOPE);args.update(changes)
    return M.batting_progress_players(metric,rows,**args)


class ProgressPlayers(unittest.TestCase):
    def test_exact_reach_help_and_empty_games_include_independent_positive_running(self):
        data=fixture()
        reach=score(data,'offensive-reach');self.assertTrue(reach['playerPopulationComplete'])
        self.assertEqual(reach['playerResults'][0]['value'],M.exact(M.Fraction(2,3)))
        help=score(data,'hidden-help-rate')
        self.assertEqual(help['playerResults'][0]['value'],M.exact(M.Fraction(1,2)))
        empty=score(data,'empty-game-rate')
        self.assertEqual([r['value'] for r in empty['playerResults']],[M.exact(0),M.exact(0)])
        # The other runner's teammate-driven Run did not benefit their batting.
        self.assertEqual(reach['playerResults'][1]['value'],M.exact(0))
        g=data.graph(G1);g.remove((URIRef(str(GAME)+'/plate-appearance/2/steal-act'),RDF.type,BASE.StealAttemptAct))
        self.assertFalse(score(data,'empty-game-rate')['playerPopulationComplete'])

    def test_counted_empty_game_and_batting_exclusion(self):
        data=fixture();g=data.graph(G1)
        rr=URIRef(str(GAME)+'/plate-appearance/2/steal')
        # An out is positively typed, not inferred from missing safe evidence.
        g.remove((rr,RDF.type,BASE.SafeProcess));g.add((rr,RDF.type,BASE.OutProcess))
        empty=score(data,'empty-game-rate')
        self.assertEqual(empty['playerResults'][1]['aggregate'],dict(kind='count',count=1,eligibleGames=1))
        result=URIRef(str(GAME)+'/plate-appearance/0/result')
        g.remove((result,RDF.type,BASE.SingleProcess));g.add((result,RDF.type,BASE.ErrorProcess))
        self.assertEqual(score(data,'offensive-reach')['playerResults'][0]['value'],M.exact(M.Fraction(1,3)))

    def test_missing_admission_or_schedule_never_ranks_a_subset(self):
        data=fixture()
        self.assertFalse(score(data,'offensive-reach',admissions={})['playerPopulationComplete'])
        rows=M.normalize_bindings(bindings(data,[G1]),[G1])
        q=M.batting_qualification(rows,graphs=[G1],admissions={G1:PROOF},date_scope=SCOPE)
        self.assertEqual(score(data,'offensive-reach',qualification=q)['playerSummaryGaps'],['COMPLETE_SELECTED_SCHEDULE'])

    def test_safe_then_out_does_not_keep_partial_contact_credit(self):
        data=fixture();g=data.graph(G1);pa=URIRef(str(GAME)+'/plate-appearance/0')
        rr=URIRef(str(pa)+'/later-out');act=URIRef(str(pa)+'/later-out-act')
        movement(g,rr,act,pa,P1,origin=URIRef(str(GAME)+'/base/1'));g.add((rr,RDF.type,BASE.OutProcess))
        for linked in (False,True):
            if linked:g.add((URIRef(str(pa)+'/contact'),BFO.BFO_0000117,rr))
            result=score(data,'offensive-reach')
            self.assertFalse(result['playerPopulationComplete'])
            self.assertIn('COMPLETE_CONSEQUENCE_COALESCENCE',result['progressEvidence']['unresolvedPlateAppearances'][0]['gaps'])

    def test_sql_keeps_admissions_separate_and_rejects_corruption(self):
        data=fixture();raw=bindings(data,[G1]);connection=database()
        M.materialize_game(connection,G1,raw,batting_admission=PROOF,runner_resolution_admission=PROOF)
        proof=dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)])
        text=M._json(proof);connection.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(SCOPE['startDate'],text,M._hash(text)))
        for metric in M.PROGRESS_METRICS:
            result=M.query_sql(connection,{'metricId':metric},SCOPE)['metric']
            self.assertEqual(result['playerResults'],score(data,metric)['playerResults'])
        connection.execute("UPDATE metric_suite_runner_resolution_admission SET proof_json='{}'")
        with self.assertRaisesRegex(M.EvidenceError,'checksum'):M.query_sql(connection,{'metricId':'offensive-reach'},SCOPE)


class ResolutionCensus(unittest.TestCase):
    def test_shape_checks_complete_membership_runner_and_destination(self):
        data=fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
        source=dict(game=str(GAME),resolutions=[dict(resolution=pa+'/resolution',act=pa+'/run-act',
            episode=pa+'/resolution/episode',pa=pa,player=str(P1),outcome='SafeProcess',destination='1B')])
        # Keep just the one declared PA and its supporting fixture nodes.
        for n in (1,2,3):
            other=URIRef(str(GAME)+'/plate-appearance/'+str(n));g.remove((other,BFO.BFO_0000132,None))
        check=lambda:validate(g,shacl_graph=A.shape_text(source),shacl_graph_format='turtle',advanced=True)[0]
        self.assertTrue(check())
        g.add((URIRef(pa+'/run-act'),CCO.ont00001833,P2));self.assertFalse(check())
        g.remove((URIRef(pa+'/run-act'),CCO.ont00001833,P2))
        source['resolutions'][0]['destination']='2B';self.assertFalse(check())
        source['resolutions']=[];self.assertFalse(check())


if __name__=='__main__':unittest.main()
