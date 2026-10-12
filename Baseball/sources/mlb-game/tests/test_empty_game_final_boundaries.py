"""EG6 selectors over the reviewed source examples, with conflicting variants."""
import copy
import json
from pathlib import Path
import unittest
from test_empty_game_addition import E

C=E.C
WITNESSES=json.loads((E.ROOT/'archive/design-records/mlb-game-empty-game-final-boundaries/evidence.json').read_text())['witnesses']


def play(pk,pa):
    row=next(p for w in WITNESSES if w['gamePk']==str(pk) for p in w['plays']
             if p.get('atBatIndex',p['about']['atBatIndex'])==pa)
    row=copy.deepcopy(row);row['atBatIndex']=pa
    return row


def history(p):
    # Unit tests supply the C1 interface; the owning integration stage proves
    # these memberships against the full original input and the promoted RDF.
    members=[dict(atBatIndex=str(p['atBatIndex']),runnerIndex=str(i),runnerId=str(r['details']['runner']['id']),
                  lifetimeKey='runner-'+str(r['details']['runner']['id'])) for i,r in enumerate(p['runners'])
             if r['movement'].get('start') is not None or r['movement'].get('isOut') is False]
    return dict(sourceConsistency='consistent',episodeMembership=members)


class FinalBoundaries(unittest.TestCase):
    def test_existing_rml_maps_primary_error_and_sacrifice_compound_without_a_bunt(self):
        from test_official_scoring import mapped, S, Graph, BASE, RDF, URIRef, validate
        error=C.secondary_error_rows(play(822934,26),'822934',True)
        graph=mapped(dict(secondaryErrors=error))
        for row in error:
            graph.add((URIRef(row['resolution']),RDF.type,BASE.RunnerResolutionProcess))
            graph.add((URIRef(row['contactPlay']),RDF.type,BASE.BattedBallPlayProcess))
        self.assertTrue(validate(graph,shacl_graph=Graph().parse(data=S.shapes(dict(secondaryErrors=error)),format='turtle'),advanced=True)[0])
        p=play(824622,54);p['_baseballO']=dict(hasCompletedPlateAppearanceResult=True,hasSacFlyDoublePlay=True)
        document=dict(gamePk=824622,liveData=dict(plays=dict(allPlays=[p])),_baseballO={})
        graph=mapped(dict(compoundDoublePlayParts=C.compound_double_play_parts(p)),document=document,
            maps=('ResultType_sac_fly','ResultType_sac_bunt','CompoundDoublePlayMap'))
        result=URIRef('https://baseballontology.org/data/game/824622/plate-appearance/54/result')
        self.assertEqual(set(graph.objects(result,RDF.type)),{BASE.SacrificeFlyProcess,BASE.DoublePlayProcess})

    def test_two_step_indifference_requires_a_complete_contiguous_history(self):
        p=play(823894,78);h=history(p)
        self.assertEqual([r['runnerIndex'] for r in C.defensive_indifference_evidence(p,h)],['0','1'])
        h['episodeMembership'].pop()
        self.assertEqual(C.defensive_indifference_evidence(p,h),[])
        h=history(p);p['runners'][1]['movement']['start']='1B'
        self.assertEqual(C.defensive_indifference_evidence(p,h),[])

    def test_pickoff_and_blocked_strike_do_not_credit_the_batter_or_caught_runner(self):
        for pk,pa in ((823134,48),(825010,27),(824105,69)):
            with self.subTest(pk=pk):
                p=play(pk,pa);h=history(p)
                self.assertEqual([r['runnerIndex'] for r in C.defensive_indifference_evidence(p,h)],['1'])
                self.assertEqual(C.defensive_indifference_evidence(p),[])
                p['runners'][1]['credits']=[dict(credit='f_throwing_error',player=dict(id=1))]
                self.assertEqual(C.defensive_indifference_evidence(p,h),[])

    def test_mixed_error_contact_keeps_all_terminal_outs(self):
        for pk,pa in ((823208,29),(823988,6),(824622,66)):
            with self.subTest(pk=pk):
                p=play(pk,pa);h=history(p)
                links=C.batted_runner_resolution_links(p,str(pa),h)
                self.assertEqual(len(links),len(p['runners']))
                h['episodeMembership'].pop()
                self.assertEqual(C.batted_runner_resolution_links(p,str(pa),h),[])

    def test_error_continuation_reuses_the_primary_error_identity(self):
        p=play(822934,26);rows=C.secondary_error_rows(p,'822934',True)
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]['error'].endswith('/plate-appearance/26/result'))
        self.assertTrue(rows[0]['judgment'].endswith('/judgment/result'))
        p['runners'][1]['credits']=[]
        self.assertEqual(C.secondary_error_rows(p,'822934',True),[])
        p=play(823373,17)
        self.assertEqual(len(C.secondary_error_rows(p,'823373',True)),1)
        self.assertEqual(C.secondary_error_rows(p,'823373',False),[])

    def test_sacrifice_double_play_requires_counted_run_and_distinct_numbered_outs(self):
        p=play(824622,54)
        self.assertEqual([r['runnerIndex'] for r in C.compound_double_play_parts(p)],['0','1'])
        p['runners'][1]['movement']['outNumber']=2
        self.assertEqual(C.compound_double_play_parts(p),[])
        p=play(824622,54);p['runners'].pop()
        self.assertEqual(C.compound_double_play_parts(p),[])

    def test_interference_requires_the_complete_observed_force_chain(self):
        p=play(823003,88);h=history(p);pr=p['playEvents'][0]
        # The reviewed excerpt omits this field; the retained original contains it.
        p['reviewDetails']=dict(isOverturned=True,inProgress=False,reviewType='MV',challengeTeamId=120)
        previous=dict(atBatIndex=87,about=dict(p['about']),matchup=dict(
            postOnFirst=dict(id=683083),postOnSecond=dict(id=pr['replacedPlayer']['id']),postOnThird=dict(id=691002)))
        doc=dict(liveData=dict(plays=dict(allPlays=[previous,p])),_baseballO=dict(runnerHistoryReconciliation=h))
        result=C.runner_metric_evidence(p,'88','2026',document=doc)
        self.assertEqual(len(result['awardAdvances']),4)
        p['matchup']['postOnSecond']['id']=999
        self.assertEqual(C.runner_metric_evidence(p,'88','2026',document=doc)['awardAdvances'],[])

    def test_placement_prefix_requires_the_existing_adjudication(self):
        p=play(824158,76);h=history(p)
        p['reviewDetails']=dict(isOverturned=False,inProgress=False,reviewType='MA',challengeTeamId=117)
        event=next(e for e in p['playEvents'] if e.get('details',{}).get('eventType')=='runner_placed')
        event['base']=2  # Explicit base from the retained original, omitted in the review excerpt.
        runner=str(event['player']['id']);about=p['about']
        h['boundaryAnchorCensus']=[dict(anchor=f"placement/{about['inning']}/{about['halfInning']}/{runner}",
            atBatIndex=p['atBatIndex'],eventIndex=event['index'],base=2)]
        h['placementAdjudications']=[dict(runnerId=runner,inning=about['inning'],half=about['halfInning'])]
        self.assertEqual(len(C.batted_runner_resolution_links(p,'76',h)),len(p['runners']))
        h['placementAdjudications']=[]
        self.assertEqual(C.batted_runner_resolution_links(p,'76',h),[])


if __name__=='__main__':unittest.main()
