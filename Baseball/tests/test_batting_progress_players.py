"""Complete RDF progress, exact selected-range player aggregation and negative cases."""
import copy
import importlib.util
import json
import math
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


def continuation_fixture():
    """B2's six-segment structure with the existing C1 whole pattern."""
    data=fixture();g=data.graph(G1);pa=URIRef(str(GAME)+'/plate-appearance/0')
    contact=URIRef(str(pa)+'/contact');half=URIRef(str(GAME)+'/half')
    g.add((half,RDF.type,BASE.HalfInning))
    p3=URIRef('https://baseballontology.org/data/player/3')
    def base(n):return URIRef(str(GAME)+'/base/'+str(n))
    original=URIRef(str(pa)+'/resolution')
    episodes={P1:[URIRef(str(original)+'/episode')],P2:[],p3:[]}
    for suffix,player,start,end,out in [('batter-out',P1,1,None,True),
            ('first-second',P2,1,2,False),('second-third',P2,2,3,False),
            ('third-safe',p3,2,3,False),('scored',p3,3,None,False)]:
        rr=URIRef(str(pa)+'/'+suffix);act=URIRef(str(rr)+'/act')
        episode,_,_=movement(g,rr,act,pa,player,origin=base(start),destination=base(end) if end else None)
        if not end:g.add((rr,RDF.type,BASE.OutProcess if out else BASE.RunProcess))
        g.add((contact,BFO.BFO_0000117,rr));episodes[player].append(episode)
    for player,members in episodes.items():
        whole=URIRef(str(GAME)+'/runner-trajectory/'+str(player).rsplit('/',1)[-1])
        interval=URIRef(str(whole)+'/interval')
        g.add((whole,RDF.type,BFO.BFO_0000015));g.add((whole,BFO.BFO_0000057,player))
        g.add((whole,BFO.BFO_0000132,half));g.add((whole,BFO.BFO_0000199,interval))
        g.add((interval,RDF.type,BFO.BFO_0000038))
        for episode in members:g.add((whole,BFO.BFO_0000117,episode))
    return data


class ProgressPlayers(unittest.TestCase):
    def test_known_contact_progress_survives_an_unknown_safe_prefix_or_suffix(self):
        for unknown in ('first-second','second-third'):
            data=continuation_fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
            g.remove((URIRef(pa+'/contact'),BFO.BFO_0000117,URIRef(pa+'/'+unknown)))
            reach=score(data,'offensive-reach')
            self.assertTrue(reach['playerPopulationComplete'],reach)
            item=reach['progressEvidence']['plateAppearances'][0]
            self.assertEqual(item['reach'],2)
            self.assertEqual(item['independentPositiveGaps'],['UNRESOLVED_RUNNING_EPISODE_ATTRIBUTION'])
            self.assertFalse(any(r['player']==str(P2) for r in item['independentPositive']))
            self.assertTrue(score(data,'hidden-help-rate')['playerPopulationComplete'])
            # Both eligible players already have certain positives elsewhere
            # in this game. Unknown extra credit cannot make either game empty.
            empty=score(data,'empty-game-rate')
            self.assertTrue(empty['playerPopulationComplete'])
            self.assertEqual([p['value'] for p in empty['playerResults']],[M.exact(0),M.exact(0)])
            mix=score(data,'contribution-path-diversity')
            self.assertFalse(mix['playerPopulationComplete'])
            self.assertEqual(mix['playerSummaryGaps'],['UNRESOLVED_RUNNING_EPISODE_ATTRIBUTION'])
            rows=M.normalize_bindings(bindings(data,[G1]),[G1])
            first=M.batting_progress_evidence(rows);second=M.batting_progress_evidence(list(reversed(rows)))
            for result in (first,second):
                for entry in result['plateAppearances']:entry['coalescedContactPaths'].sort(key=lambda r:r['player'])
            self.assertEqual(first,second)

    def test_unknown_safe_steps_cannot_hide_outs_or_incomplete_paths(self):
        for change in ('out','missing_member','branch','no_known_positive'):
            data=continuation_fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
            contact=URIRef(pa+'/contact');unknown=URIRef(pa+'/second-third')
            g.remove((contact,BFO.BFO_0000117,unknown))
            if change=='out':
                g.remove((unknown,RDF.type,BASE.SafeProcess));g.add((unknown,RDF.type,BASE.OutProcess))
            elif change=='missing_member':
                g.remove((URIRef(str(GAME)+'/runner-trajectory/2'),BFO.BFO_0000117,URIRef(str(unknown)+'/episode')))
            elif change=='branch':
                rr=URIRef(pa+'/branch')
                episode,_,_=movement(g,rr,URIRef(str(rr)+'/act'),URIRef(pa),P2,
                    origin=URIRef(str(GAME)+'/base/1'),destination=URIRef(str(GAME)+'/base/3'))
                g.add((URIRef(str(GAME)+'/runner-trajectory/2'),BFO.BFO_0000117,episode))
            else:g.remove((contact,BFO.BFO_0000117,URIRef(pa+'/first-second')))
            self.assertFalse(score(data,'offensive-reach')['playerPopulationComplete'],change)

    def test_excluded_batting_progress_and_unknown_running_remain_separate_in_sql(self):
        data=continuation_fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
        result=URIRef(pa+'/result')
        g.remove((result,RDF.type,BASE.SingleProcess));g.add((result,RDF.type,BASE.FieldersChoiceProcess))
        g.remove((URIRef(pa+'/contact'),BFO.BFO_0000117,URIRef(pa+'/second-third')))
        raw=bindings(data,[G1])
        with database() as connection:
            M.materialize_game(connection,G1,raw,batting_admission=PROOF,runner_resolution_admission=PROOF)
            proof=dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)])
            text=M._json(proof)
            connection.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(SCOPE['startDate'],text,M._hash(text)))
            for metric in M.PROGRESS_METRICS:
                direct=score(data,metric)
                stored=M.query_sql(connection,{'metricId':metric},SCOPE)['metric']
                self.assertEqual(stored['playerResults'],direct['playerResults'])
                self.assertEqual(stored['playerPopulationComplete'],direct['playerPopulationComplete'])
                self.assertEqual(stored['playerSummaryGaps'],direct['playerSummaryGaps'])
                if metric in ('offensive-reach','hidden-help-rate'):
                    self.assertTrue(direct['playerPopulationComplete'])
                    self.assertEqual(direct['progressEvidence']['plateAppearances'][0]['reach'],0)
                elif metric=='empty-game-rate':self.assertTrue(direct['playerPopulationComplete'])
                else:self.assertFalse(direct['playerPopulationComplete'])

    def test_empty_classification_keeps_unknown_pas_but_uses_certain_other_positives(self):
        data=fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
        g.remove((URIRef(pa+'/contact'),BFO.BFO_0000117,URIRef(pa+'/resolution')))
        self.assertFalse(score(data,'offensive-reach')['playerPopulationComplete'])
        empty=score(data,'empty-game-rate')
        self.assertTrue(empty['playerPopulationComplete'])
        self.assertEqual([p['plateAppearances'] for p in empty['playerResults']],[3,1])
        self.assertEqual([p['value'] for p in empty['playerResults']],[M.exact(0),M.exact(0)])
        self.assertEqual(len(empty['progressEvidence']['unresolvedPlateAppearances']),1)
        pa=str(GAME)+'/plate-appearance/1'
        g.remove((URIRef(pa+'/contact'),BFO.BFO_0000117,URIRef(pa+'/runner2')))
        empty=score(data,'empty-game-rate')
        self.assertFalse(empty['playerPopulationComplete'])
        self.assertEqual(empty['playerResults'],[])
        self.assertEqual([r['player'] for r in empty['unresolvedEmptyGames']],[str(P1)])

    def test_empty_game_certainty_does_not_cross_game_boundaries(self):
        data=fixture();rows=M.normalize_bindings(bindings(data,[G1]),[G1])
        evidence=M.batting_progress_evidence(rows)
        q=M.batting_qualification(rows,graphs=[G1],admissions={G1:PROOF},date_scope=SCOPE,selected_games_complete=True)
        other_graph='urn:game:other';other_game='urn:game:other:identity';pa='urn:game:other:pa'
        evidence['unresolvedPlateAppearances'].append(dict(graph=other_graph,game=other_game,plateAppearance=pa,
            player=str(P1),officialResult=True,possiblePositivePlayers=[str(P1)],gaps=['UNRESOLVED_PROGRESS_ATTRIBUTION']))
        q['expectedObservations'].append(dict(graph=other_graph,game=other_game,plateAppearance=pa,player=str(P1)))
        person=next(p for p in q['participation'] if p['player']==str(P1));person['plateAppearances']+=1
        person['teamGameExposure'].append(dict(game=other_game,team='urn:team'))
        empty=M.empty_game_players(evidence,qualification=q,date_scope=SCOPE)
        self.assertFalse(empty['playerPopulationComplete'])
        self.assertEqual(empty['unresolvedEmptyGames'],[dict(graph=other_graph,game=other_game,player=str(P1))])

    def test_certain_batter_reach_is_not_lost_to_another_runners_unknown_credit(self):
        data=fixture();g=data.graph(G1);pa=URIRef(str(GAME)+'/plate-appearance/0')
        rr=URIRef(str(pa)+'/unknown-runner')
        movement(g,rr,URIRef(str(rr)+'/act'),pa,P2,origin=URIRef(str(GAME)+'/base/1'),destination=URIRef(str(GAME)+'/base/2'))
        # Leave no other positive batting PA to settle this batter's game.
        other=str(GAME)+'/plate-appearance/1'
        g.remove((URIRef(other+'/contact'),BFO.BFO_0000117,URIRef(other+'/runner2')))
        reach=score(data,'offensive-reach');self.assertFalse(reach['playerPopulationComplete'])
        empty=score(data,'empty-game-rate');self.assertTrue(empty['playerPopulationComplete'])
        self.assertEqual([p['value'] for p in empty['playerResults']],[M.exact(0),M.exact(0)])
        held=next(p for p in empty['progressEvidence']['unresolvedPlateAppearances'] if p['plateAppearance']==str(pa))
        self.assertEqual(held['confirmedPositivePlayers'],[str(P1)])
        out=URIRef(str(pa)+'/later-out')
        movement(g,out,URIRef(str(out)+'/act'),pa,P1,origin=URIRef(str(GAME)+'/base/1'))
        g.add((out,RDF.type,BASE.OutProcess));g.add((URIRef(str(pa)+'/contact'),BFO.BFO_0000117,out))
        empty=score(data,'empty-game-rate');self.assertFalse(empty['playerPopulationComplete'])
        self.assertEqual([r['player'] for r in empty['unresolvedEmptyGames']],[str(P1)])

    def test_reviewed_contact_continuation_reaches_all_four_player_producers(self):
        data=continuation_fixture()
        reach=score(data,'offensive-reach')
        self.assertTrue(reach['playerPopulationComplete'])
        pa=reach['progressEvidence']['plateAppearances'][0]
        self.assertEqual(pa['reach'],2)
        self.assertFalse(pa['batterPositive'])
        self.assertEqual(len(pa['coalescedContactPaths']),3)
        batter=next(p for p in pa['coalescedContactPaths'] if p['player']==str(P1))
        self.assertEqual((batter['start'],batter['end'],batter['positive']),(0,None,False))
        self.assertEqual(reach['playerResults'][0]['value'],M.exact(1))
        self.assertEqual(score(data,'hidden-help-rate')['playerResults'][0]['value'],M.exact(M.Fraction(2,3)))
        self.assertEqual(score(data,'empty-game-rate')['playerResults'][0]['value'],M.exact(0))
        self.assertEqual(score(data,'contribution-path-diversity')['playerResults'][0]['aggregate']['channelCounts'],[0,2,0])

    def test_continuation_needs_exact_c1_membership_not_just_contact_or_person(self):
        for change in ('missing_member','missing_resolution','different_whole','independent'):
            with self.subTest(change=change):
                data=continuation_fixture();g=data.graph(G1);pa=str(GAME)+'/plate-appearance/0'
                out=URIRef(pa+'/batter-out');whole=URIRef(str(GAME)+'/runner-trajectory/1')
                if change=='missing_member':g.remove((whole,BFO.BFO_0000117,URIRef(str(out)+'/episode')))
                elif change=='missing_resolution':g.remove((out,BFO.BFO_0000062,None))
                elif change=='different_whole':
                    other=URIRef(str(whole)+'-other')
                    for _,p,o in list(g.triples((whole,None,None))):g.add((other,p,o))
                else:g.add((URIRef(str(out)+'/act'),RDF.type,BASE.StealAttemptAct))
                self.assertFalse(score(data,'offensive-reach')['playerPopulationComplete'])

    def test_continuation_rejects_branch_reverse_and_disconnected_progress(self):
        for start,end in ((1,3),(3,2),(3,3)):
            with self.subTest(start=start,end=end):
                data=continuation_fixture();g=data.graph(G1);pa=URIRef(str(GAME)+'/plate-appearance/0')
                rr=URIRef(str(pa)+'/extra');act=URIRef(str(rr)+'/act')
                episode,_,_=movement(g,rr,act,pa,P1,origin=URIRef(str(GAME)+'/base/'+str(start)),
                                     destination=URIRef(str(GAME)+'/base/'+str(end)))
                g.add((URIRef(str(pa)+'/contact'),BFO.BFO_0000117,rr))
                g.add((URIRef(str(GAME)+'/runner-trajectory/1'),BFO.BFO_0000117,episode))
                self.assertFalse(score(data,'offensive-reach')['playerPopulationComplete'])

    def test_continuation_is_independent_of_binding_order_and_keeps_sql_equivalence(self):
        data=continuation_fixture();raw=bindings(data,[G1]);rows=M.normalize_bindings(raw,[G1])
        first=M.batting_progress_evidence(rows)
        other=M.batting_progress_evidence(list(reversed(rows)))
        canonical=lambda result:{p['plateAppearance']:(p['reach'],p['batterPositive'],p['otherPositivePlayers'],
                                  sorted(p['coalescedContactPaths'],key=lambda r:r['player'])) for p in result['plateAppearances']}
        self.assertEqual(canonical(first),canonical(other))
        with database() as connection:
            M.materialize_game(connection,G1,raw,batting_admission=PROOF,runner_resolution_admission=PROOF)
            proof=dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)])
            text=M._json(proof)
            connection.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(SCOPE['startDate'],text,M._hash(text)))
            for metric in M.PROGRESS_METRICS:
                result=M.query_sql(connection,{'metricId':metric},SCOPE)['metric']
                self.assertEqual(result['playerResults'],score(data,metric)['playerResults'])

    def test_contribution_mix_counts_channels_not_beneficiaries(self):
        data=fixture();result=score(data,'contribution-path-diversity')
        self.assertTrue(result['playerPopulationComplete'])
        self.assertEqual([p['aggregate']['channelCounts'] for p in result['playerResults']],[[1,1,0],[0,0,1]])
        self.assertAlmostEqual(result['playerResults'][0]['approximateValue'],math.log(2)/math.log(3))
        self.assertEqual(result['playerResults'][1]['independentRunningEpisodes'],1)
        # Another beneficiary on the same contact remains one batter-other play.
        g=data.graph(G1);pa=URIRef(str(GAME)+'/plate-appearance/1');runner=URIRef('https://baseballontology.org/data/player/3')
        rr=URIRef(str(pa)+'/runner3');act=URIRef(str(pa)+'/runner3-act')
        movement(g,rr,act,pa,runner,origin=URIRef(str(GAME)+'/base/2'),destination=URIRef(str(GAME)+'/base/3'))
        g.add((URIRef(str(pa)+'/contact'),BFO.BFO_0000117,rr))
        self.assertEqual(score(data,'contribution-path-diversity')['playerResults'][0]['aggregate']['channelCounts'],[1,1,0])

    def test_contribution_mix_does_not_infer_strategy_from_strikeout_and_caught_stealing(self):
        data=fixture();g=data.graph(G1);rr=URIRef(str(GAME)+'/plate-appearance/2/steal')
        g.remove((rr,RDF.type,BASE.SafeProcess));g.add((rr,RDF.type,BASE.OutProcess))
        result=score(data,'contribution-path-diversity')
        self.assertFalse(result['playerPopulationComplete'])
        self.assertEqual(result['playerSummaryGaps'],['STRIKEOUT_RUNNING_OUT_STRATEGY_UNRESOLVED'])

    def test_contribution_mix_keeps_nonpositive_attempts_and_zero_pa_participants(self):
        data=fixture();rows=M.normalize_bindings(bindings(data,[G1]),[G1])
        evidence=M.batting_progress_evidence(rows)
        q=M.batting_qualification(rows,graphs=[G1],admissions={G1:PROOF},date_scope=SCOPE,selected_games_complete=True)
        # Exercise the pure aggregate with separately admitted participation.
        # Only positive occurrences enter entropy; all three distinct attempts
        # enter the independently supplied running participation inventory.
        evidence['plateAppearances']=[p for p in evidence['plateAppearances'] if p['player']!=str(P2)]
        running=evidence['plateAppearances'][-1]
        original=running['independentEpisodes'][0]
        running['independentEpisodes'].extend([{**original,'episode':original['episode']+'/missed1'},
                                               {**original,'episode':original['episode']+'/missed2'}])
        next(p for p in q['participation'] if p['player']==str(P2))['plateAppearances']=0
        result=M.contribution_mix_players(evidence,qualification=q,date_scope=SCOPE)
        runner=next(p for p in result['playerResults'] if p['player']==str(P2))
        self.assertEqual(runner['plateAppearances'],0)
        self.assertEqual(runner['independentRunningEpisodes'],3)
        self.assertEqual(runner['aggregate']['channelCounts'],[0,0,1])

    def test_contribution_mix_pools_period_channels_and_omits_known_empty_denominators(self):
        data=fixture();rows=M.normalize_bindings(bindings(data,[G1]),[G1])
        evidence=M.batting_progress_evidence(rows)
        q=M.batting_qualification(rows,graphs=[G1],admissions={G1:PROOF},date_scope=SCOPE,selected_games_complete=True)
        for pa in evidence['plateAppearances']:
            pa['positiveChannels']=[c for c in pa['positiveChannels'] if c['player']==str(P1)]
        result=M.contribution_mix_players(evidence,qualification=q,date_scope=SCOPE)
        self.assertEqual(len(result['playerResults']),1)
        self.assertEqual(result['playerResults'][0]['aggregate']['channelCounts'],[1,1,0])
        # Each separate play has entropy zero; their pooled channels do not.
        self.assertGreater(result['playerResults'][0]['approximateValue'],0)

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
        g.add((URIRef(pa+'/run-act'),RDF.type,BASE.StealAttemptAct));self.assertFalse(check())
        source['resolutions'][0]['stealAttempt']=True;self.assertTrue(check())
        g.remove((URIRef(pa+'/run-act'),RDF.type,BASE.StealAttemptAct));self.assertFalse(check())
        source['resolutions'][0]['stealAttempt']=False
        source['resolutions'][0]['destination']='2B';self.assertFalse(check())
        source['resolutions']=[];self.assertFalse(check())


if __name__=='__main__':unittest.main()
