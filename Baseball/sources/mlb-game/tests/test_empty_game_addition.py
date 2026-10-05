"""EG1 scope and BK1 joins without network or graph mutation."""
import copy
from contextlib import closing
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sqlite3
import unittest
from unittest.mock import patch
from rdflib import Graph, RDF, Namespace, URIRef
from pyshacl import validate

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('eg1_test',ROOT/'sources/mlb-game/pipeline/targeted-empty-game-addition.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)


class EmptyGameAddition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'data/raw/game-566279.json').read_bytes()
        cls.document=json.loads(cls.raw)
        cls.play=next(p for p in cls.document['liveData']['plays']['allPlays'] if p['atBatIndex']==12)

    def test_balk_requires_exact_action_runner_join_and_awarded_distance(self):
        row,=E.BK.C.balk_runner_evidence(self.play,'12')
        self.assertEqual((row['runnerId'],row['runnerIndex']),('488671','0'))
        self.assertEqual(row['actionId'],'a05f90a9-c21a-4e07-a4e0-7660dd0beb46')
        mutations=[lambda p:p['runners'][0]['details'].update(playIndex=99),
            lambda p:p['runners'][0]['movement'].update(end='3B'),
            lambda p:p['runners'][0]['details'].update(eventType='wild_pitch'),
            lambda p:p['playEvents'][5].update(actionPlayId=None),
            lambda p:p['playEvents'][5]['details'].update(eventType='forced_balk'),
            lambda p:p['runners'].append(copy.deepcopy(p['runners'][0]))]
        for mutate in mutations:
            play=copy.deepcopy(self.play);mutate(play)
            self.assertEqual(E.BK.C.balk_runner_evidence(play,'12'),[])

    def test_whole_game_pa_admission_needs_no_redundant_individual_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);database=state/'published.sqlite';player='urn:player'
            with closing(sqlite3.connect(database)) as db,db:
                db.executescript('CREATE TABLE dashboard_player_admission(graph_iri,proof_json);'
                    'CREATE TABLE dashboard_player_game(graph_iri,player,plate_appearances);'
                    'CREATE TABLE dashboard_player_metric(graph_iri,player,metric_id,complete);')
                db.execute('INSERT INTO dashboard_player_game VALUES (?,?,?)',('urn:graph',player,4))
                db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?)',('urn:graph',player,'empty-game-rate',0))
            E.W.atomic(state/'serving/dashboard-current.json',dict(buildId='20261006T000000Z-fixture',databasePath=str(database)))
            case=dict(graph='urn:graph',excludedPlayerGames=[dict(player=player)])
            self.assertEqual(E.outstanding(state,case),[player])
            with closing(sqlite3.connect(database)) as db,db:db.execute('UPDATE dashboard_player_game SET plate_appearances=NULL')
            self.assertIsNone(E.outstanding(state,case))

    def test_shared_balk_identity_keeps_both_runners_and_final_batting_result(self):
        play=copy.deepcopy(self.play)
        extra=copy.deepcopy(play['runners'][0]);extra['details']['runner']['id']=123456
        extra['movement'].update(start='3B',end='score');extra['details']['isScoringEvent']=True
        play['runners'].append(extra)
        rows=E.BK.C.balk_runner_evidence(play,'12')
        self.assertEqual(len(rows),2);self.assertEqual(len({r['actionId'] for r in rows}),1)
        self.assertEqual(play['result'],self.play['result'])
        Graph().parse(data=E.BK.shapes('566279',rows),format='turtle')

    def test_scoring_balk_uses_existing_run_process_and_rejects_wrong_result_type(self):
        row=dict(atBatIndex='37',runnerIndex='0',runnerId='702332',resolutionKind='score',actionId='fixture-balk')
        game='https://baseballontology.org/data/game/822846'
        iri=lambda suffix:URIRef(game+suffix)
        b=Namespace('https://baseballontology.org/');o=Namespace('http://purl.obolibrary.org/obo/')
        c=Namespace('https://www.commoncoreontologies.org/')
        record,act,resolution,pa,process,judgment,decision=map(iri,('/runner-record/37/0',
            '/runner-act/movement/37/0','/runner-resolution/score/37/0','/plate-appearance/37',
            '/process/balk/fixture-balk','/judgment/balk/fixture-balk','/decision/balk/fixture-balk'))
        rule=b['data/rule/balk'];data=Graph()
        triples=[(record,RDF.type,b.BaseballEventRecord),
            *[(record,c.ont00001808,node) for node in (act,resolution,process,judgment,decision)],
            (act,RDF.type,b.BaserunningAct),(act,o.BFO_0000132,pa),(act,o.BFO_0000057,b['data/player/702332']),
            (resolution,RDF.type,b.RunProcess),(resolution,o.BFO_0000062,act),(resolution,o.BFO_0000132,pa),
            (process,RDF.type,b.BalkProcess),(process,o.BFO_0000132,pa),(process,o.BFO_0000117,judgment),
            (process,c.ont00001920,rule),(rule,RDF.type,b.BalkRule),
            (judgment,RDF.type,b.UmpireJudgmentAct),(judgment,o.BFO_0000132,process),
            (judgment,c.ont00001921,rule),(judgment,c.ont00001986,decision),
            (decision,RDF.type,b.BaseballDecisionICE),(decision,c.ont00001808,process)]
        for triple in triples:data.add(triple)
        shapes=Graph().parse(data=E.BK.shapes('822846',[row]),format='turtle')
        self.assertTrue(validate(data,shacl_graph=shapes)[0])
        data.remove((resolution,RDF.type,b.RunProcess));data.add((resolution,RDF.type,b.SafeProcess))
        self.assertFalse(validate(data,shacl_graph=shapes)[0])

    def test_selected_census_addition_preserves_old_source_and_does_not_expand_scope(self):
        raw=self.raw;game='https://baseballontology.org/data/game/566279'
        full=E.R.H.census(raw,'566279');old=copy.deepcopy(full)
        selected_histories=full['history']['histories'][:2]
        selected_keys={h['lifetimeKey'] for h in selected_histories}
        old['history']['histories']=full['history']['histories'][2:3]
        old_keys={h['lifetimeKey'] for h in old['history']['histories']}
        old['history']['episodeMembership']=[r for r in old['history']['episodeMembership'] if r['lifetimeKey'] in old_keys]
        old['history']['placementAdjudications']=[];old['populationComplete']=False
        selected=dict(sourceWitness=dict(path='retained-input.json',sha256=hashlib.sha256(raw).hexdigest()),
            history=dict(histories=selected_histories,
                episodeMembership=[r for r in full['history']['episodeMembership'] if r['lifetimeKey'] in selected_keys],
                placementAdjudications=[]))
        updated,shape,provenance=E.project_census('runnerHistoryAdmission',old,selected)
        self.assertEqual({h['lifetimeKey'] for h in updated['history']['histories']},old_keys|selected_keys)
        self.assertEqual(len(old['history']['histories']),1);self.assertFalse(updated['populationComplete'])
        self.assertEqual(updated['sourceSha256'],old['sourceSha256'])
        self.assertEqual(provenance['addedHistoryKeys'],sorted(selected_keys))
        Graph().parse(data=shape,format='turtle')
        old_contact=dict(gamePk='566279',sourceSha256='original',plays=[
            dict(atBatIndex='12',playId='contact',status='withheld',links=[],memberships=[])])
        link=dict(atBatIndex='12',runnerIndex='0',resolutionKind='advance',playId='contact')
        selected.update(plateAppearances=['12'],contactCensus=dict(plays=[dict(old_contact['plays'][0],
            status='admitted',links=[link])]))
        updated,shape,provenance=E.project_census('contactContinuationAdmission',old_contact,selected)
        self.assertEqual(updated['plays'][0]['links'],[link]);self.assertEqual(updated['sourceSha256'],'original')
        Graph().parse(data=shape,format='turtle')
        selected['contactCensus']['plays'][0]['links']=[]
        with self.assertRaisesRegex(ValueError,'remove an existing source obligation'):
            E.project_census('contactContinuationAdmission',updated,selected)

    def test_balk_context_preserves_existing_censuses_and_proof_identities(self):
        prior=subprocess.check_output(['git','show','8f1835b:Baseball/scripts/pipeline/prepare-rml-context.py'])
        current=E.BK.CONTEXT_PATH.read_bytes();before=ast.parse(prior);after=ast.parse(current)
        after.body=[n for n in after.body if getattr(n,'name',None)!='balk_runner_evidence']
        main=next(n for n in after.body if getattr(n,'name',None)=='main')
        removed=0
        for node in ast.walk(main):
            if not isinstance(node,ast.Dict):continue
            keep=[(k,v) for k,v in zip(node.keys,node.values) if not (isinstance(k,ast.Constant) and k.value=='balkAdvances')]
            removed+=len(node.keys)-len(keep)
            node.keys=[k for k,v in keep];node.values=[v for k,v in keep]
        self.assertEqual(removed,1);self.assertEqual(ast.dump(before),ast.dump(after))
        bridge=E.E.read(E.E.COMPATIBILITY_PATH)['balkRunnerAttribution']
        self.assertEqual(hashlib.sha256(prior).hexdigest(),bridge['previousContextSha256'])
        self.assertEqual(hashlib.sha256(current).hexdigest(),bridge['currentContextSha256'])
        for family,entry in bridge['families'].items():
            adapter=E.E.module(E.HERE/(family+'-admission.py'),'bk1_check_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            self.assertEqual(E.E.code_equivalence(family,entry['previousImplementationSha256'],adapter.fingerprint())['kind'],
                'unchanged-proof-dependencies')
            self.assertIsNone(E.E.code_equivalence(family,'unknown',adapter.fingerprint()))

    def test_scoped_existing_maps_preserve_history_dependencies_and_source_bytes(self):
        player='https://baseballontology.org/data/player/'+str(self.play['matchup']['batter']['id'])
        case=dict(gamePk='566279',excludedPlayerGames=[dict(player=player)])
        with patch.object(E,'approved_case',return_value=case):selected=E.select(self.raw,'566279',[player])
        self.assertIn('12',selected['plateAppearances']);self.assertTrue(selected['balks'])
        history=selected['history'];keys={(r['atBatIndex'],r['runnerIndex']) for r in selected['episodes']}
        self.assertTrue({(r['atBatIndex'],r['runnerIndex']) for r in history['episodeMembership']}<=keys)
        for play in selected['context']['liveData']['plays']['allPlays']:
            for row in play['runners']:
                self.assertIn((str(row['_baseballO']['atBatIndex']),str(row['_baseballO']['runnerIndex'])),keys)
        Graph().parse(data=E.shapes('566279',selected),format='turtle')
        with tempfile.TemporaryDirectory() as directory:
            context=Path(directory)/'game-context.json';mapping=Path(directory)/'addition.ttl'
            E.execution_inputs(self.raw,'566279',selected,context,mapping)
            self.assertEqual((Path(directory)/'game.json').read_bytes(),self.raw)
            graph=Graph().parse(mapping);rr=Namespace('http://www.w3.org/ns/r2rml#')
            self.assertEqual({str(s).rsplit('#',1)[-1] for s in graph.subjects(RDF.type,rr.TriplesMap)},set(E.MAPS))
            self.assertNotIn('{$.',mapping.read_text())
        self.assertEqual(self.raw,(ROOT/'data/raw/game-566279.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'outside the approved'):E.approved_case('566279')


if __name__=='__main__':unittest.main()
