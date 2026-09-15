"""Contributor breadth counts supported offensive people once per scored run."""
import unittest

from rdflib import RDF, URIRef

from test_scoring_run_players import fixture, M, G1, PLAYER, TEAM, PROOF, SCOPE, summarize, rows
from test_run_construction_serving import EX
from runner_pattern_fixture import BASE, BFO, CCO

OTHER = URIRef('https://baseballontology.org/data/player/2')


def supported_fixture():
    data, _ = fixture(); graph=data.graph(G1)
    for i in range(3):
        pa=EX[f'pa{i}'];result=EX[f'result{i}'];judgment=EX[f'judgment{i}']
        decision=EX[f'decision{i}'];record=EX[f'record{i}']
        for triple in ((result,RDF.type,BASE.BaseballInstitutionalProcess),(result,RDF.type,BASE.SingleProcess),
            (result,BFO.BFO_0000132,pa),(judgment,RDF.type,BASE.BaseballAdjudicationAct),
            (judgment,BFO.BFO_0000132,result),(judgment,CCO.ont00001986,decision),
            (decision,RDF.type,BASE.BaseballDecisionICE),(decision,CCO.ont00001808,result),
            (record,RDF.type,BASE.BaseballEventRecord)):
            graph.add(triple)
        for node in (result,judgment,decision):graph.add((record,CCO.ont00001808,node))
        if i:
            act=EX[f'batter{i}'];role=URIRef(str(OTHER)+'/role/batter')
            for triple in ((act,RDF.type,BASE.BatterAct),(act,BFO.BFO_0000132,pa),
                (act,BFO.BFO_0000055,role),(role,RDF.type,BASE.BatterRole),(role,BFO.BFO_0000197,OTHER)):
                graph.add(triple)
        if i==1:
            graph.add((EX.act1,RDF.type,BASE.StealAttemptAct))
        else:
            contact=EX[f'contact{i}']
            for triple in ((contact,RDF.type,BASE.BattedBallPlayProcess),(contact,BFO.BFO_0000132,pa),
                (contact,BFO.BFO_0000117,EX[f'resolution{i}'])):graph.add(triple)
    return data


def evidence(data):
    source=rows(data)
    return source,M.live_result('run-construction-breadth',source,graph_count=1)


class RunConstructionBreadth(unittest.TestCase):
    def test_self_batting_independent_running_and_teammate_count_two_people(self):
        source,result=evidence(supported_fixture())
        run,=result['runs']
        self.assertEqual(run['value'],M.exact(2))
        self.assertEqual(run['contributors'],[str(PLAYER),str(OTHER)])
        self.assertEqual(result['unresolvedRuns'],[])
        player,=summarize(source,evidence=result)['playerResults']
        self.assertEqual(player['metricId'],'run-construction-breadth')
        self.assertEqual(player['value'],M.exact(2))
        self.assertEqual(player['aggregate'],dict(kind='mean',sum=M.exact(2),count=1))

    def test_missing_contribution_or_ambiguous_channel_does_not_shrink_breadth(self):
        for fault in ('missing','conflicting'):
            data=supported_fixture();g=data.graph(G1)
            if fault=='missing':g.remove((EX.contact2,BFO.BFO_0000117,EX.resolution2))
            else:g.add((EX.act2,RDF.type,BASE.StealAttemptAct))
            source,result=evidence(data)
            self.assertEqual(result['runs'],[])
            self.assertEqual(result['unresolvedRuns'][0]['gaps'],['UNSUPPORTED_RUN_CONTRIBUTOR'])
            self.assertFalse(summarize(source,evidence=result)['playerPopulationComplete'])

    def test_error_progress_is_excluded_but_independent_steal_still_counts(self):
        data=supported_fixture();g=data.graph(G1)
        for i in (0,2):
            g.remove((EX[f'result{i}'],RDF.type,BASE.SingleProcess))
            g.add((EX[f'result{i}'],RDF.type,BASE.ErrorProcess))
        _,result=evidence(data);run,=result['runs']
        self.assertEqual(run['value'],M.exact(1))
        self.assertEqual(run['contributors'],[str(PLAYER)])

    def test_fully_evidenced_excluded_contributions_allow_zero_not_unknown(self):
        data=supported_fixture();g=data.graph(G1)
        g.remove((EX.act1,RDF.type,BASE.StealAttemptAct))
        for i in range(3):
            g.remove((EX[f'result{i}'],RDF.type,BASE.SingleProcess));g.add((EX[f'result{i}'],RDF.type,BASE.ErrorProcess))
            c=EX[f'contact{i}']
            g.add((c,RDF.type,BASE.BattedBallPlayProcess));g.add((c,BFO.BFO_0000132,EX[f'pa{i}']))
            g.add((c,BFO.BFO_0000117,EX[f'resolution{i}']))
        source,result=evidence(data)
        self.assertEqual(result['runs'][0]['value'],M.exact(0))
        self.assertEqual(summarize(source,evidence=result)['playerResults'][0]['value'],M.exact(0))


if __name__=='__main__':unittest.main()
