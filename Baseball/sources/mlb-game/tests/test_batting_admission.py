"""B1 source counterexamples and exact graph conformance, independently tested."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('b1',ROOT/'sources/mlb-game/pipeline/batting-admission.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
BASE=Namespace(B.BASE); OBO=Namespace('http://purl.obolibrary.org/obo/')
CCO=Namespace('https://www.commoncoreontologies.org/')


def raw(game='824315',date='2026-08-23'):
    return json.loads((ROOT/f'data/raw/samples/{date}/{game}.json').read_bytes())


def census(doc):
    return B.census(json.dumps(doc).encode(),str(doc['gamePk']))


def fixture():
    game=B.BASE+'data/game/1'; player=B.BASE+'data/player/1'; team=B.BASE+'data/team/1'
    source=dict(game=game,members=[dict(pa=game+'/plate-appearance/0',player=player,
                                      resultType=B.BASE+'WalkProcess')],
                roster=[dict(player=player,team=team,side='home',officialPA=1),
                        dict(player=B.BASE+'data/player/2',team=team,side='home',officialPA=0)])
    graph=Graph()
    def add(s,p,o):graph.add((URIRef(s),p,URIRef(o)))
    pa=source['members'][0]['pa']; act=pa+'/batter-act'; role=player+'/role/batter'
    add(game,RDF.type,BASE.BaseballGame);add(pa,RDF.type,BASE.PlateAppearance)
    add(pa,OBO.BFO_0000132,game+'/half');add(game+'/half',OBO.BFO_0000132,game+'/inning')
    add(game+'/inning',OBO.BFO_0000132,game)
    add(act,RDF.type,BASE.BatterAct);add(act,OBO.BFO_0000132,pa);add(act,OBO.BFO_0000055,role)
    add(role,RDF.type,BASE.BatterRole);add(role,OBO.BFO_0000197,player)
    add(pa+'/result',RDF.type,BASE.BaseballInstitutionalProcess);add(pa+'/result',RDF.type,BASE.WalkProcess)
    add(pa+'/result',OBO.BFO_0000132,pa)
    add(pa+'/judgment/result',RDF.type,BASE.BaseballAdjudicationAct)
    add(pa+'/judgment/result',OBO.BFO_0000132,pa+'/result')
    add(pa+'/judgment/result',CCO.ont00001986,pa+'/decision/result')
    add(pa+'/decision/result',RDF.type,BASE.BaseballDecisionICE)
    add(pa+'/decision/result',CCO.ont00001808,pa+'/result')
    add(pa+'/event-record/result',RDF.type,BASE.BaseballEventRecord)
    for suffix in ('/result','/judgment/result','/decision/result'):
        add(pa+'/event-record/result',CCO.ont00001808,pa+suffix)
    for row in source['roster']:
        role=row['player']+'/team/1/role/player'
        add(game,OBO.BFO_0000055,role);add(role,RDF.type,BASE.PlayerRole)
        add(role,OBO.BFO_0000197,row['player']);add(role,CCO.ont00001992,team)
    add(game+'/team-role',RDF.type,BASE.HomeTeamRole)
    add(game+'/team-role',OBO.BFO_0000197,team);add(game+'/team-role',OBO.BFO_0000054,game)
    return source,graph


class SourceAdmission(unittest.TestCase):
    def test_positive_real_source_and_interrupted_turn(self):
        source=census(raw());self.assertEqual(source['issues'],[])
        self.assertEqual(sum(p['officialPA'] for p in source['roster']),77)
        self.assertEqual(len(source['roster']),52)
        counter=census(raw('822693','2026-08-25'));self.assertEqual(counter['issues'],[])
        self.assertEqual(len(counter['interrupted']),1)
        ford=next(r for r in counter['roster'] if r['player'].endswith('/695670'))
        self.assertEqual(ford['officialPA'],4)

    def test_equal_team_totals_do_not_hide_wrong_player_credit(self):
        doc=raw();people=[p for p in doc['liveData']['boxscore']['teams']['away']['players'].values()
                          if p['stats']['batting'].get('plateAppearances',0)>0]
        people[0]['stats']['batting']['plateAppearances']+=1
        people[1]['stats']['batting']['plateAppearances']-=1
        self.assertIn('PLAYER_PA_MISMATCH',{i['code'] for i in census(doc)['issues']})

    def test_empty_stat_block_requires_zero_residual(self):
        doc=raw();doc['liveData']['boxscore']['teams']['away']['teamStats']['batting']['plateAppearances']+=1
        self.assertIn('UNRECONCILED_TEAM_PA_TOTAL',{i['code'] for i in census(doc)['issues']})

    def test_mid_turn_replacement_and_unknown_result_block(self):
        doc=raw();doc['liveData']['plays']['allPlays'][53]['playEvents'][0]['count']['strikes']=2
        self.assertIn('OFFENSIVE_REPLACEMENT_WITHIN_TURN',{i['code'] for i in census(doc)['issues']})
        doc=raw();doc['liveData']['plays']['allPlays'][0]['result']['eventType']='unknown'
        self.assertIn('UNRESOLVED_COMPLETED_RESULT',{i['code'] for i in census(doc)['issues']})

    def test_missing_unfiltered_play_blocks(self):
        doc=raw();doc['liveData']['plays']['allPlays'].pop()
        self.assertEqual(census(doc)['status'],'withheld')

    def test_explicit_other_players_pinch_run_does_not_transfer_this_batters_pa(self):
        doc=raw('824087','2026-07-20');source=census(doc)
        self.assertEqual(source['status'],'reconciled',source['issues'])
        self.assertEqual(sum(r['officialPA'] for r in source['roster']),73)
        for fault in ('batter','unknown-player','same-player','base','substitution'):
            changed=copy.deepcopy(doc);pa=changed['liveData']['plays']['allPlays'][53];event=pa['playEvents'][0]
            if fault=='batter':event['player']['id']=pa['matchup']['batter']['id']
            elif fault=='unknown-player':event['player']['id']=999999999
            elif fault=='same-player':event['player']['id']=event['replacedPlayer']['id']
            elif fault=='base':event.pop('base')
            else:event['isSubstitution']=False
            self.assertIn('OFFENSIVE_REPLACEMENT_WITHIN_TURN',{i['code'] for i in census(changed)['issues']},fault)


class GraphAdmission(unittest.TestCase):
    def conforms(self,source,graph):
        return validate(graph,shacl_graph=Graph().parse(data=B.shape_text(source),format='turtle'),
                        inference='none',advanced=True)[0]

    def test_complete_graph_and_zero_pa_roster_member(self):
        source,graph=fixture();self.assertTrue(self.conforms(source,graph))

    def test_interrupted_turn_remains_in_graph_without_extra_official_pa(self):
        source,graph=fixture()
        pa=source['game']+'/plate-appearance/1'
        player=source['members'][0]['player']
        source['members'].append(dict(pa=pa,player=player,resultType=None))
        graph.add((URIRef(pa),RDF.type,BASE.PlateAppearance))
        graph.add((URIRef(pa),OBO.BFO_0000132,URIRef(source['game']+'/half')))
        graph.add((URIRef(pa+'/batter-act'),RDF.type,BASE.BatterAct))
        graph.add((URIRef(pa+'/batter-act'),OBO.BFO_0000132,URIRef(pa)))
        graph.add((URIRef(pa+'/batter-act'),OBO.BFO_0000055,URIRef(player+'/role/batter')))
        # A broad result record cannot manufacture completed batting credit.
        graph.add((URIRef(pa+'/result'),RDF.type,BASE.BaseballInstitutionalProcess))
        graph.add((URIRef(pa+'/result'),OBO.BFO_0000132,URIRef(pa)))
        self.assertTrue(self.conforms(source,graph))

    def test_missing_decision_extra_batter_and_wrong_count_fail(self):
        source,graph=fixture()
        graph.remove((URIRef(source['members'][0]['pa']+'/decision/result'),RDF.type,BASE.BaseballDecisionICE))
        self.assertFalse(self.conforms(source,graph))
        source,graph=fixture()
        graph.add((URIRef(source['members'][0]['player']+'/role/batter'),OBO.BFO_0000197,URIRef(B.BASE+'data/player/2')))
        self.assertFalse(self.conforms(source,graph))
        source,graph=fixture();source['roster'][0]['officialPA']=2
        self.assertFalse(self.conforms(source,graph))

    def test_missing_nonbatting_roster_exposure_fails(self):
        source,graph=fixture()
        graph.remove((URIRef(source['game']),OBO.BFO_0000055,URIRef(B.BASE+'data/player/2/team/1/role/player')))
        self.assertFalse(self.conforms(source,graph))

    def test_unexpected_pa_and_conflicting_result_fail(self):
        source,graph=fixture()
        extra=URIRef(source['game']+'/plate-appearance/99')
        graph.add((extra,RDF.type,BASE.PlateAppearance));graph.add((extra,OBO.BFO_0000132,URIRef(source['game']+'/half')))
        self.assertFalse(self.conforms(source,graph))
        source,graph=fixture()
        graph.add((URIRef(source['members'][0]['pa']+'/result'),RDF.type,BASE.SingleProcess))
        self.assertFalse(self.conforms(source,graph))


if __name__=='__main__':unittest.main()
