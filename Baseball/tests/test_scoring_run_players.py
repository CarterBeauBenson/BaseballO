"""Counted-run admission and complete player means, through RDF/query/SQL."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, URIRef

from test_run_construction_serving import run_fixture, EX, WHOLE
from test_metric_suite_serving import M, G1, G2, bindings, database
from runner_pattern_fixture import BASE, BFO, CCO

spec = importlib.util.spec_from_file_location('scoring_admission',
    M.ROOT/'sources/mlb-game/pipeline/scoring-run-admission.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
PLAYER = URIRef('https://baseballontology.org/data/player/1')
TEAM = URIRef('https://baseballontology.org/data/team/1')
SCOPE = dict(startDate='2026-08-01', endDate='2026-08-01', gameSet='regular_season')
PROOF = dict(status='admitted', sourceReconciled=True, graphConforms=True)


def fixture():
    data = run_fixture()
    g = data.graph(G1)
    for s, p, o in list(g):
        if s == EX.runner or o == EX.runner:
            g.remove((s,p,o)); g.add((PLAYER if s==EX.runner else s,p,PLAYER if o==EX.runner else o))
    role = URIRef(str(PLAYER)+'/team/1/role/player')
    for triple in ((EX.game,BFO.BFO_0000055,role), (role,RDF.type,BASE.PlayerRole),
                   (role,BFO.BFO_0000197,PLAYER), (role,CCO.ont00001992,TEAM),
                   (EX.teamRole,RDF.type,BASE.HomeTeamRole), (EX.teamRole,BFO.BFO_0000197,TEAM),
                   (EX.teamRole,BFO.BFO_0000054,EX.game)):
        g.add(triple)
    source = dict(game=str(EX.game), roster=[dict(player=str(PLAYER),team=str(TEAM),side='home')],
                  runs=[dict(run=str(EX.resolution2),act=str(EX.act2),player=str(PLAYER))])
    return data, source


def rows(data):
    return M.normalize_bindings(bindings(data,[G1]),[G1])


def summarize(source, **changes):
    args = dict(graphs=[G1], admissions={G1:PROOF}, date_scope=SCOPE,
                schedule={'complete':True}, evidence=M.run_construction_evidence(source))
    args.update(changes)
    return M.scoring_run_players(source, **args)


class RunAdmission(unittest.TestCase):
    def check(self, source, graph):
        return validate(graph, shacl_graph=A.shape_text(source), shacl_graph_format='turtle',
                        inference='none', advanced=True)[0]

    def test_exact_run_roster_and_scorer_census(self):
        data, source = fixture(); g = data.graph(G1)
        self.assertTrue(self.check(source,g))
        g.add((EX.act2,CCO.ont00001833,EX.wrongRunner))
        self.assertFalse(self.check(source,g))

    def test_missing_extra_run_and_missing_roster_are_rejected(self):
        for fault in ('missing','extra','roster'):
            data,source = fixture();g=data.graph(G1)
            if fault=='missing':g.remove((EX.resolution2,RDF.type,BASE.RunProcess))
            elif fault=='extra':
                g.add((EX.extraRun,RDF.type,BASE.RunProcess));g.add((EX.extraRun,BFO.BFO_0000132,EX.pa2))
            else:g.remove((EX.game,BFO.BFO_0000055,None))
            self.assertFalse(self.check(source,g),fault)

    def test_zero_runs_needs_positive_complete_census(self):
        data,source=fixture();g=data.graph(G1)
        source['runs']=[];g.remove((EX.resolution2,RDF.type,BASE.RunProcess))
        self.assertTrue(self.check(source,g))
        g.add((EX.extraRun,RDF.type,BASE.RunProcess));g.add((EX.extraRun,BFO.BFO_0000132,EX.pa2))
        self.assertFalse(self.check(source,g))

    def test_real_walkoff_source_census_and_conflicting_final_total(self):
        raw=(M.ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        source=A.census(raw,'824087')
        self.assertEqual(source['status'],'reconciled')
        doc=json.loads(raw)
        self.assertEqual(len(source['runs']),sum(doc['liveData']['linescore']['teams'][s]['runs'] for s in ('away','home')))
        doc['liveData']['linescore']['teams']['home']['runs']+=1
        self.assertEqual(A.census(json.dumps(doc).encode(),'824087')['status'],'withheld')


class ScoringPlayers(unittest.TestCase):
    def test_first_live_player_mean_without_batting_requirement(self):
        data,_=fixture(); result=summarize(rows(data))
        self.assertTrue(result['playerPopulationComplete'])
        player,=result['playerResults']
        self.assertEqual(player['aggregate'],dict(kind='mean',sum=M.exact(3),count=1))
        self.assertEqual(player['value'],M.exact(3))
        self.assertNotIn('plateAppearances',player)

    def test_missing_source_proof_schedule_or_history_never_admits_subset(self):
        data,_=fixture();source=rows(data)
        for change in (dict(admissions={}),dict(schedule={'complete':False})):
            self.assertFalse(summarize(source,**change)['playerPopulationComplete'])
        data.graph(G1).remove((WHOLE,RDF.type,BFO.BFO_0000015))
        result=summarize(rows(data))
        self.assertFalse(result['playerPopulationComplete'])
        self.assertIn('COMPLETE_SCORING_HISTORIES',result['playerSummaryGaps'])

    def test_non_scoring_games_remain_in_team_exposure(self):
        data,_=fixture();source=rows(data)
        roster=next(r for r in source if r['kind']=='player_team_game')
        source.append(dict(roster,graph=G2,game='https://baseballontology.org/data/game/102'))
        result=summarize(source,graphs=[G1,G2],admissions={G1:PROOF,G2:PROOF})
        self.assertEqual(result['playerResults'][0]['teamGames'],2)
        self.assertEqual(result['playerResults'][0]['aggregate']['count'],1)

    def test_query_and_sql_proof_admission_are_separate_from_source_numbers(self):
        data,_=fixture();source=bindings(data,[G1])
        with database() as connection:
            M.materialize_game(connection,G1,source,scoring_run_admission=PROOF)
            payload=M._json(dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)]))
            connection.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',
                               ('2026-08-01',payload,M._hash(payload)))
            result=M.query_sql(connection,{'metricId':'run-construction-depth'},SCOPE)['metric']
            self.assertTrue(result['playerPopulationComplete'])
            self.assertEqual(result['playerResults'][0]['value'],M.exact(3))
            dashboard=M.query_sql(connection,{'view':'dashboard'},SCOPE)
            self.assertEqual(next(m for m in dashboard['metrics'] if m['metricId']=='run-construction-depth'),result)
            connection.execute("UPDATE metric_suite_run_admission SET proof_sha256='broken'")
            with self.assertRaisesRegex(M.EvidenceError,'run admission checksum'):
                M.query_sql(connection,{'metricId':'run-construction-depth'},SCOPE)


if __name__=='__main__':unittest.main()
