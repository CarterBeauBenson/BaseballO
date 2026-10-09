"""D2/W5 active selectors, scoped retry and the actual RML overlay."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from rdflib import Graph, RDF, URIRef
from pyshacl import validate
from test_empty_game_addition import E, ROOT

NEW=E.C
PACKAGE=ROOT/'archive/design-records/mlb-game-walk-after-reconciled-review'
EVIDENCE=json.loads((PACKAGE/'evidence.json').read_text())
DOCUMENT=json.loads((Path(__file__).parent/'fixtures/reconciled-walk-reviews.json').read_text())
D2_REVIEW=E.W.module(ROOT/'archive/design-records/mlb-game-defensive-indifference-running/check.py','accepted_d2_tests')
D2_REVIEW.select=NEW.defensive_indifference_evidence


def play(index):
    return copy.deepcopy(next(p for p in DOCUMENT['liveData']['plays']['allPlays'] if p['atBatIndex']==index))


def awards(module,pa):
    return module.runner_metric_evidence(pa,str(pa['atBatIndex']),'2026',document=DOCUMENT)['awardAdvances']


class DefensiveIndifferenceSelection(D2_REVIEW.DefensiveIndifference):
    pass


class TargetedCompletion(unittest.TestCase):
    def test_d2_resolution_expectation_and_retained_projection_agree(self):
        case=json.loads((ROOT/'archive/design-records/mlb-game-defensive-indifference-running/evidence.json').read_text())['witnesses'][0]
        game=case['gamePk'];doc=dict(gamePk=int(game),liveData=dict(plays=dict(allPlays=[case['play']])))
        raw=json.dumps(doc).encode();owner=E.R.P.R
        with patch.object(owner.B.SOURCE,'reconcile',return_value=dict(blockingIssues=[],sourceRevision='fixture')):
            census=owner.census(raw,game)
        target=next(r for r in census['resolutions'] if r['act'].endswith('/73/0'))
        self.assertTrue(target['stealAttempt'])
        old=copy.deepcopy(census)
        for row in old['resolutions']:row['stealAttempt']=False
        selected=dict(independent=case['expected'],sourceWitness=dict(sha256=hashlib.sha256(raw).hexdigest()))
        updated,shape,provenance=E.project_census('runnerResolutionAdmission',old,selected)
        self.assertEqual(updated,census)
        self.assertFalse(any(r['stealAttempt'] for r in old['resolutions']))
        self.assertEqual(provenance['updatedActTypes'],[target['act']])
        self.assertIsNone(E.project_census('runnerResolutionAdmission',updated,selected))
        self.assertNotIn('FILTER NOT EXISTS { <'+target['act']+'> a base:StealAttemptAct }',shape)

    def test_history_dependency_pa_keeps_all_required_d2_types_only(self):
        # The selected player's history reaches PA 68, where another runner
        # has a D2 act. Full PA conformance needs its type, not a new history.
        key=E.C.CONTEXT_KEY;game='823412';player='https://baseballontology.org/data/player/800325'
        def source_play(pa,batter,indices,d2):
            return dict(atBatIndex=pa,matchup=dict(batter=dict(id=batter)),
                runners=[{key:dict(runnerIndex=i)} for i in indices],
                **{key:dict(batterParticipations=[],defensiveIndifferenceActs=d2)})
        independent=dict(atBatIndex='68',runnerIndex='0',runnerId='592885')
        unrelated=dict(atBatIndex='70',runnerIndex='0',runnerId='592885')
        document=dict(gamePk=int(game),liveData=dict(plays=dict(allPlays=[
            source_play(69,800325,['0'],[]),source_play(68,111111,['0','1'],[independent]),
            source_play(70,111111,['0'],[unrelated])])),**{key:dict(compoundDoublePlayParts=[])})
        episodes=[dict(atBatIndex='69',runnerIndex='0'),dict(atBatIndex='68',runnerIndex='1')]
        selection=dict(episodes=episodes,context={key:{},'liveData':dict(plays=dict(allPlays=[
            {key:dict(runnerEpisodes=[episode])} for episode in episodes]))})
        census=dict(game='https://baseballontology.org/data/game/'+game,sourceSha256='fixture',resolutions=[])
        with patch.object(E,'approved_case',return_value=dict(excludedPlayerGames=[dict(player=player)])), \
                patch.object(E,'prepare',return_value=document), \
                patch.object(E.R.P.R,'census',return_value=census), \
                patch.object(E.R.P,'shape_text',return_value=('',[dict(plateAppearance=census['game']+'/plate-appearance/69',status='pending')])), \
                patch.object(E.R,'select_case',return_value=selection), \
                patch.object(E.CONTACT,'census',return_value={}):
            result=E.select(b'fixture',game,[player])
        self.assertEqual(result['independent'],[independent])
        self.assertEqual(result['episodes'],episodes)
        dependency=next(p for p in result['context']['liveData']['plays']['allPlays']
            if p[key]['runnerEpisodes'][0]['atBatIndex']=='68')
        self.assertEqual([r[key]['runnerIndex'] for r in dependency['runners']],['1'])
        self.assertEqual(dependency[key]['defensiveIndifferenceActs'],[independent])

    def test_only_approved_selectors_change_and_unaffected_proofs_remain_usable(self):
        bridge=E.E.read(E.E.COMPATIBILITY_PATH)['reviewedWalkIndependentRunning']
        before=subprocess.check_output(['git','show',bridge['baselineCommit']+':Baseball/scripts/pipeline/prepare-rml-context.py'])
        self.assertEqual(hashlib.sha256(before).hexdigest(),bridge['previousContextSha256'])
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);candidate=work/'Baseball/scripts/pipeline/prepare-rml-context.py'
            candidate.parent.mkdir(parents=True);candidate.write_bytes(before)
            subprocess.run(['git','-c','core.autocrlf=false','-C',str(work),'apply',str(PACKAGE/'selection.patch')],check=True)
            expected=ast.parse(candidate.read_bytes())
        actual=ast.parse(E.BK.CONTEXT_PATH.read_bytes())
        actual.body=[n for n in actual.body if getattr(n,'name',None)!='defensive_indifference_evidence']
        main=next(n for n in actual.body if getattr(n,'name',None)=='main')
        for node in ast.walk(main):
            if not isinstance(node,ast.Dict):continue
            pairs=[(k,v) for k,v in zip(node.keys,node.values) if not (isinstance(k,ast.Constant) and k.value=='defensiveIndifferenceActs')]
            node.keys=[k for k,v in pairs];node.values=[v for k,v in pairs]
        self.assertEqual(ast.dump(expected),ast.dump(actual))
        self.assertEqual(E.W.sha(E.BK.CONTEXT_PATH),bridge['currentContextSha256'])
        for family,entry in bridge['families'].items():
            adapter=E.E.module(E.HERE/(family+'-admission.py'),'d2_w5_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            self.assertEqual(E.E.code_equivalence(family,entry['previousImplementationSha256'],adapter.fingerprint())['kind'],entry['reuseKind'])
            self.assertIsNone(E.E.code_equivalence(family,'unknown',adapter.fingerprint()))
            self.assertEqual(E.E.EXISTING_GRAPH.fingerprint(E.E,adapter),bridge['independentProofs'][family]['currentImplementationSha256'])
        for kind,module in (('players',E.E.PLAYER_PARTICIPATION),('pa',E.E.PLAYER_PARTICIPATION.PA),
                            ('c2pa',E.E.PA_RESOLUTION),('retained-batting',E.E.RETAINED_BATTING)):
            producer=(module.PREVIOUS_LOOKUP_IMPLEMENTATION if kind=='c2pa' else module.fingerprint())
            self.assertEqual(producer,bridge['derivedProofs'][kind]['currentImplementationSha256'])
            self.assertTrue(E.E.prior_versions(kind,producer))

    def test_d2_reopens_retired_selection_only_for_current_excluded_players(self):
        case=json.loads((ROOT/'archive/design-records/mlb-game-defensive-indifference-running/evidence.json').read_text())['witnesses'][0]
        play=case['play'];batter='https://baseballontology.org/data/player/'+str(play['matchup']['batter']['id'])
        runner='https://baseballontology.org/data/player/'+case['expected'][0]['runnerId']
        inventory=dict(gamePk=case['gamePk'],excludedPlayerGames=[dict(player=batter),dict(player=runner)])
        previous=dict(status='complete',selected=dict(context=dict(liveData=dict(plays=dict(allPlays=[play])))))
        with tempfile.TemporaryDirectory() as directory:
            for players,expected in (([batter],True),([runner],True),([],False),(['player/999999'],False)):
                with patch.object(E,'outstanding',return_value=players):
                    self.assertEqual(E.selection_repair_retry(Path(directory),inventory,previous),expected)
            with patch.object(E,'outstanding',return_value=[batter]):
                self.assertFalse(E.selection_repair_retry(Path(directory),inventory,dict(previous,
                    independentRunningDecision=E.INDEPENDENT_DECISION,reviewedWalkDecision=E.REVIEW_WALK_DECISION)))

    def test_w5_retries_reconciled_awards_without_reopening_ordinary_walks(self):
        document=copy.deepcopy(DOCUMENT);batter='https://baseballontology.org/data/player/'+str(play(11)['matchup']['batter']['id'])
        case=dict(gamePk=str(document['gamePk']),excludedPlayerGames=[dict(player=batter)])
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);source=state/'input.json';E.W.atomic(source,document)
            previous=dict(status='already-present',sourceWitness=dict(path=str(source),sha256=E.W.sha(source)))
            with patch.object(E,'outstanding',return_value=[batter]),patch.object(E.C,'personal_runner_histories',return_value={}):
                self.assertTrue(E.selection_repair_retry(state,case,previous))
                self.assertFalse(E.selection_repair_retry(state,case,dict(previous,
                    independentRunningDecision=E.INDEPENDENT_DECISION,reviewedWalkDecision=E.REVIEW_WALK_DECISION)))
                with patch.object(E.C,'accounted_runner_count_reviews',return_value=dict(issues=[],events={} )):
                    self.assertFalse(E.selection_repair_retry(state,case,previous))
            source.write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'retained source changed'):
                E.selection_repair_retry(state,case,previous)

    def test_retired_execution_context_is_only_a_hash_checked_retry_diagnostic(self):
        document=copy.deepcopy(DOCUMENT);batter='https://baseballontology.org/data/player/'+str(play(11)['matchup']['batter']['id'])
        case=dict(gamePk='822714',excludedPlayerGames=[dict(player=batter)])
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);folder=state/'pipeline/evidence/mlb-game/822714/old-addition'
            context=folder/'game-context.json';E.W.atomic(context,document)
            previous=dict(status='complete',deltaPath=str(folder/'addition.ttl'),executionContextSha256=E.W.sha(context))
            with patch.object(E,'outstanding',return_value=[batter]):
                self.assertTrue(E.selection_repair_retry(state,case,previous))
                context.write_text('{}',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'retained context changed'):
                    E.selection_repair_retry(state,case,previous)

    def test_d2_mapper_emits_only_existing_act_type_and_shacl_requires_it(self):
        sys.path.insert(0,str(ROOT/'tests'))
        from test_rmlmapper_iterator_compatibility import installed_tools
        cases=json.loads((ROOT/'archive/design-records/mlb-game-defensive-indifference-running/evidence.json').read_text())['witnesses']
        rows=[dict(r,atBatIndex=str(n)) for n,c in enumerate(cases) for r in E.C.defensive_indifference_evidence(c['play'])]
        game='900000001';doc=dict(gamePk=int(game),liveData=dict(plays=dict(allPlays=[{E.C.CONTEXT_KEY:dict(defensiveIndifferenceActs=rows)}])))
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);E.W.atomic(work/'game-context.json',doc);E.W.atomic(work/'game.json',doc)
            mapping=work/'addition.rml.ttl';E.W.A.subset_mapping(game,mapping,E.D2.MAPS)
            java,mapper=installed_tools();output=work/'result.ttl'
            result=subprocess.run([str(java),'-Xmx256m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=work,capture_output=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace')[-2000:])
            graph=Graph().parse(output);expected={(URIRef('https://baseballontology.org/data/game/'+game+
                '/runner-act/movement/'+r['atBatIndex']+'/'+r['runnerIndex']),RDF.type,
                URIRef('https://baseballontology.org/StealAttemptAct')) for r in rows}
            self.assertEqual(set(graph),expected)
            shape=Graph().parse(data=E.D2.shapes(game,rows),format='turtle')
            self.assertTrue(validate(graph,shacl_graph=shape)[0])
            graph.remove(next(iter(expected)));self.assertFalse(validate(graph,shacl_graph=shape)[0])


class WalkReviewSelection(unittest.TestCase):
    def test_two_existing_reviews_keep_only_the_later_batter_award(self):
        for row in EVIDENCE['cases']:
            pa=play(row['atBatIndex'])
            self.assertFalse(NEW.accounted_runner_history_reviews(pa)['issues'])
            selected=awards(NEW,pa)
            self.assertEqual(len(selected),1)
            self.assertEqual(selected[0]['runnerIndex'],str(row['runnerIndex']))
            self.assertEqual(selected[0]['atBatIndex'],str(row['atBatIndex']))
            self.assertEqual(selected[0]['ruleCode'],'5.05(b)(1)')

    def test_unfinished_or_unknown_reviews_still_withhold(self):
        for index,event in ((11,6),(66,5)):
            for fault in ('unfinished','unknown'):
                pa=play(index);review=pa['playEvents'][event]['reviewDetails']
                review['inProgress']=True if fault=='unfinished' else False
                if fault=='unknown':review['reviewType']='unknown'
                self.assertEqual(awards(NEW,pa),[],(index,fault))

    def test_mismatched_review_counters_still_withhold(self):
        for index,event in ((11,6),(66,5)):
            pa=play(index);pa['playEvents'][event]['count']['outs']+=1
            self.assertEqual(awards(NEW,pa),[],index)

    def test_final_count_destination_and_identity_remain_required(self):
        for fault in ('count','destination','post-occupant','event-join'):
            pa=play(66)
            if fault=='count':pa['playEvents'][-1]['count']['balls']=3
            elif fault=='destination':pa['runners'][0]['movement']['end']='2B'
            elif fault=='post-occupant':pa['matchup']['postOnFirst']['id']=99999999
            else:pa['runners'][0]['details']['playIndex']=0
            self.assertEqual(awards(NEW,pa),[],fault)

    def test_preceding_reviewed_steal_is_not_a_forced_award(self):
        pa=play(11);selected=awards(NEW,pa)
        self.assertEqual({r['runnerIndex'] for r in selected},{'1'})
        self.assertEqual(pa['runners'][0]['details']['eventType'],'stolen_base_2b')
