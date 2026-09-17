"""PB/WP ownership uses the existing particular runner-record RDF pattern."""
import unittest
from rdflib import RDF, URIRef

from test_metric_suite_serving import M, G1, bindings, database
from test_run_construction_breadth_serving import supported_fixture, evidence, EX, PLAYER, OTHER
from runner_pattern_fixture import BASE, BFO, CCO
from test_batting_progress_players import fixture as progress_fixture, score
from test_contribution_players import fixture as contribution_fixture, inputs, RUNNER, GAME


def classified_running(g, *, act, resolution, pa, kind):
    """Use exactly the already-mapped process/judgment/decision/record links."""
    process=URIRef(str(act)+'/classification');judgment=URIRef(str(process)+'/judgment')
    decision=URIRef(str(process)+'/decision');record=URIRef(str(act)+'/runner-record')
    for triple in ((process,RDF.type,BASE[kind+'Process']),
        (process,BFO.BFO_0000132,pa),(process,BFO.BFO_0000117,judgment),
        (judgment,RDF.type,BASE[kind+'JudgmentAct']),(judgment,BFO.BFO_0000132,process),
        (judgment,CCO.ont00001986,decision),(decision,RDF.type,BASE[kind+'DecisionICE']),
        (decision,CCO.ont00001808,process),(record,RDF.type,BASE.BaseballEventRecord)):
        g.add(triple)
    for entity in (act,resolution,process,judgment,decision):g.add((record,CCO.ont00001808,entity))
    return process,judgment,decision,record


class IndependentRunningServing(unittest.TestCase):
    def runner_fixture(self,kind):
        data=supported_fixture();g=data.graph(G1)
        g.remove((EX.act1,RDF.type,BASE.StealAttemptAct))
        nodes=classified_running(g,act=EX.act1,resolution=EX.resolution1,pa=EX.pa1,kind=kind)
        return data,nodes

    def test_both_classifications_retain_runner_credit_through_query_and_sql(self):
        for kind in ('PassedBall','WildPitch'):
            with self.subTest(kind=kind):
                data,nodes=self.runner_fixture(kind);source,result=evidence(data)
                run,=result['runs'];self.assertEqual(result['unresolvedRuns'],[])
                self.assertEqual(run['contributors'],[str(PLAYER),str(OTHER)])
                self.assertEqual(run['value'],M.exact(2))
                movement=next(r for r in source if r.get('act')==str(EX.act1))
                self.assertEqual(movement['independentRunningProcess'],str(nodes[0]))
                self.assertEqual(M.independent_running_act(movement),str(EX.act1))
                with database() as conn:
                    M.materialize_game(conn,G1,bindings(data,[G1]))
                    retained,=M.read_results(conn,G1,'run-construction-breadth')
                    self.assertEqual(retained['runs'],result['runs'])

    def test_same_pa_other_record_missing_judgment_or_other_pa_never_supply_ownership(self):
        for fault in ('other-record','missing-judgment','other-pa'):
            data,(process,judgment,decision,record)=self.runner_fixture('PassedBall');g=data.graph(G1)
            if fault=='other-record':g.remove((record,CCO.ont00001808,EX.resolution1))
            elif fault=='missing-judgment':g.remove((judgment,CCO.ont00001986,decision))
            else:
                g.remove((process,BFO.BFO_0000132,EX.pa1));g.add((process,BFO.BFO_0000132,EX.pa2))
            _,result=evidence(data)
            self.assertEqual(result['runs'],[])
            self.assertEqual(result['unresolvedRuns'][0]['gaps'],['UNSUPPORTED_RUN_CONTRIBUTOR'])

    def test_conflicting_contact_and_running_channels_remain_unavailable(self):
        data,_=self.runner_fixture('WildPitch');g=data.graph(G1)
        g.add((EX.conflict,RDF.type,BASE.BattedBallPlayProcess))
        g.add((EX.conflict,BFO.BFO_0000132,EX.pa1));g.add((EX.conflict,BFO.BFO_0000117,EX.resolution1))
        self.assertEqual(evidence(data)[1]['runs'],[])

    def test_batter_reaching_on_uncaught_third_strike_is_not_an_existing_runner_advance(self):
        data,_=self.runner_fixture('WildPitch');source,_=evidence(data)
        movement=next(r for r in source if r.get('act')==str(EX.act1))
        for key in ('originDesignation','originBase','originCode'):movement.pop(key,None)
        movement.update(metricOrigin='0',batter=movement['runner'])
        self.assertEqual(M.segment_origin(movement),0)
        self.assertIsNone(M.independent_running_act(movement))

    def test_excluded_batter_entry_needs_no_positive_contact_causation(self):
        for kind in ('FieldersChoiceProcess','ErrorProcess'):
            data=supported_fixture();g=data.graph(G1)
            g.remove((EX.result0,RDF.type,BASE.SingleProcess));g.add((EX.result0,RDF.type,BASE[kind]))
            g.remove((EX.contact0,BFO.BFO_0000117,EX.resolution0))
            _,result=evidence(data)
            self.assertEqual(result['unresolvedRuns'],[])
            self.assertEqual(result['runs'][0]['value'],M.exact(2))
            # Excluding the PA does not make an unrelated runner's advance
            # zero: the scorer is not that later PA's batter.
            g.remove((EX.result2,RDF.type,BASE.SingleProcess));g.add((EX.result2,RDF.type,BASE[kind]))
            g.remove((EX.contact2,BFO.BFO_0000117,EX.resolution2))
            self.assertEqual(evidence(data)[1]['runs'],[])

    def test_independent_running_is_not_batting_help_and_prevents_runner_empty_game(self):
        for kind in ('PassedBall','WildPitch'):
            data=progress_fixture();g=data.graph(G1);pa=URIRef(GAME+'/plate-appearance/2')
            act=URIRef(str(pa)+'/steal-act');rr=URIRef(str(pa)+'/steal')
            g.remove((act,RDF.type,BASE.StealAttemptAct))
            classified_running(g,act=act,resolution=rr,pa=pa,kind=kind)
            result=score(data,'empty-game-rate');self.assertTrue(result['playerPopulationComplete'])
            runner=next(p for p in result['playerResults'] if p['player']==RUNNER)
            self.assertEqual(runner['value'],M.exact(0))
            target=next(p for p in result['progressEvidence']['plateAppearances'] if p['plateAppearance']==str(pa))
            self.assertEqual(target['reach'],0)
            self.assertEqual(target['independentPositive'][0]['player'],RUNNER)

    def test_strikeout_uses_actual_scored_runner_end_without_batting_credit(self):
        rows=contribution_fixture(outs=1,runner_base=3)
        runner=dict(rows[-1],entity='score',resolution='score',runner=RUNNER,act='run',episode='run-episode',
            originDesignation='origin',originBase=GAME+'/base/3',originCode='3B',
            hasOutType='false',hasRunType='true',independentRunningProcess='passed-ball',
            independentRunningType=str(BASE.PassedBallProcess),independentRunningJudgment='pb-judgment',
            independentRunningDecision='pb-decision')
        rows.append(runner);result=inputs(rows)
        self.assertTrue(result['complete'],result)
        pa,=result['plateAppearances']
        self.assertEqual(pa['score']['value'],M.exact(M.Fraction(-1,4)))
        self.assertEqual(pa['independentPositive'][0]['player'],RUNNER)
        self.assertTrue(result['independentDamageComplete'])


if __name__=='__main__':unittest.main()
