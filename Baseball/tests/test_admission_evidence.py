import importlib.util
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sqlite3
import io
from contextlib import closing,nullcontext
from types import SimpleNamespace
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission_evidence',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)


def current_implementation(family, entry):
    record=E.read(E.COMPATIBILITY_PATH);context=E.sha(ROOT/record['contextPath'])
    for repair in record.values():
        if isinstance(repair,dict) and repair.get('currentContextSha256')==context:
            bridge=repair.get('families',{}).get(family)
            if bridge:return bridge['currentImplementationSha256']
    return entry['currentImplementationSha256']


class AdmissionEvidence(unittest.TestCase):
    def test_eligibility_uses_one_complete_pa_without_certifying_the_full_pa_total(self):
        owner=E.PLAYER_PARTICIPATION;base=owner.B.BASE
        game=base+'data/game/1';player=base+'data/player/1';pa=game+'/plate-appearance/0'
        source=dict(game=game,roster=[dict(player=player,team=base+'data/team/1',side='away',officialPA=2)],
            members=[dict(pa=pa,player=player,atBatIndex=0,resultType=base+'SingleProcess'),
                     dict(pa=game+'/plate-appearance/1',player=player,atBatIndex=1,resultType=base+'DoublePlayProcess')],
            issues=[])
        shapes=owner.Graph().parse(data=owner.shape_text(source),format='turtle')
        eligibility=owner.URIRef('urn:baseballo:validation:player-eligibility:1')
        query=str(shapes.value(shapes.value(eligibility,owner.SH.sparql),owner.SH.select))
        data=owner.Graph().parse(data=owner.B.PREFIXES+f'''
<{pa}> a base:PlateAppearance ; obo:BFO_0000132 <urn:half> .
<urn:half> obo:BFO_0000132 <urn:inning> . <urn:inning> obo:BFO_0000132 <{game}> .
<{pa}/batter-act> a base:BatterAct ; obo:BFO_0000132 <{pa}> ; obo:BFO_0000055 <{player}/role/batter> .
<{player}/role/batter> a base:BatterRole ; obo:BFO_0000197 <{player}> .
<{pa}/result> a base:BaseballInstitutionalProcess,base:SingleProcess ; obo:BFO_0000132 <{pa}> .
<{pa}/judgment/result> a base:BaseballAdjudicationAct ; obo:BFO_0000132 <{pa}/result> ; cco:ont00001986 <{pa}/decision/result> .
<{pa}/decision/result> a base:BaseballDecisionICE ; cco:ont00001808 <{pa}/result> .
<{pa}/event-record/result> a base:BaseballEventRecord ; cco:ont00001808 <{pa}/result>,<{pa}/judgment/result>,<{pa}/decision/result> .
''',format='turtle')
        self.assertEqual(list(data.query(query,initBindings={'this':owner.URIRef(player)})),[])
        report=owner.Graph()
        report.add((owner.URIRef('urn:failure'),owner.SH.sourceShape,
                    owner.URIRef('urn:baseballo:validation:player-participation:1')))
        result=owner.outcome(source,report)
        self.assertEqual(result['eligiblePlayers'],[player])
        self.assertEqual(result['players'][0]['status'],'withheld')
        # Actual multiple batting stints do not supply ordinary B1 credit.
        data.parse(data=owner.B.PREFIXES+f'<urn:other-act> a base:BatterAct ; obo:BFO_0000132 <{pa}> .',format='turtle')
        self.assertEqual(len(list(data.query(query,initBindings={'this':owner.URIRef(player)}))),1)
        report.add((owner.URIRef('urn:eligibility-failure'),owner.SH.sourceShape,eligibility))
        self.assertEqual(owner.outcome(source,report)['eligiblePlayers'],[])

    def test_administrative_pa_expectations_reuse_complete_mapping_selection(self):
        owner=E.PLAYER_PARTICIPATION;base=owner.B.BASE
        actual=dict(atBatIndex=0,player=base+'data/player/1',pa=base+'data/game/1/plate-appearance/0',
                    eventType='single',resultType=base+'SingleProcess')
        advisory=dict(actual,atBatIndex=1,pa=base+'data/game/1/plate-appearance/1',eventType='game_advisory',resultType=None)
        old_issues=[dict(code='UNRESOLVED_COMPLETED_RESULT',atBatIndex=1,eventType='game_advisory'),
                    dict(code='SOURCE_RECONCILIATION',detail=dict(code='INCOMPLETE_SOURCE_PLAY',
                         path='/liveData/plays/allPlays/1/about/isComplete'))]
        other=dict(code='SOURCE_RECONCILIATION',detail=dict(code='INCOMPLETE_SOURCE_PLAY',
                   path='/liveData/plays/allPlays/0/about/isComplete'))
        source=dict(sourceSha256='original',members=[actual,advisory],issues=[*old_issues,other])
        original=copy.deepcopy(source)
        manifest=dict(inputSha256='original',metricMappingMembershipVerified=True,
            sourceCounts=dict(plateAppearances=1,batterActs=1),
            batterParticipationEvidence=[dict(atBatIndex='0',playerId='1',actIri=actual['pa']+'/batter-act')])
        projected=owner.administrative_expectations(source,manifest)
        self.assertEqual(projected['members'],[actual]);self.assertEqual(projected['issues'],[other])
        self.assertEqual(projected['administrativeRecords'],[advisory])
        self.assertEqual(projected['resolvedAdministrativeIssues'],old_issues)
        self.assertEqual(source,original)
        # An advisory carrying real batting, incomplete mapping evidence, or
        # another source's selection cannot erase an unresolved actual turn.
        for changed in [dict(manifest,inputSha256='different'),dict(manifest,metricMappingMembershipVerified=False),
                        dict(manifest,sourceCounts=dict(plateAppearances=2,batterActs=1)),
                        dict(manifest,batterParticipationEvidence=[]),
                        dict(manifest,batterParticipationEvidence=[*manifest['batterParticipationEvidence'],
                             dict(atBatIndex='1',playerId='1',actIri=advisory['pa']+'/batter-act')])]:
            self.assertEqual(owner.administrative_expectations(source,changed),source)
        old=dict(implementationSha256=owner.PREVIOUS_ADMINISTRATIVE_IMPLEMENTATION,
                 players=[dict(status='withheld',issues=old_issues)])
        self.assertIn(old['implementationSha256'],E.prior_versions('players',owner.fingerprint()))
        self.assertTrue(owner.needs_compound_refresh(old))

    def test_player_pa_checks_are_independent_of_run_total_reconciliation(self):
        owner=E.PLAYER_PARTICIPATION
        source=owner.B.census((ROOT/'data/raw/game-566279.json').read_bytes(),'566279')
        original=copy.deepcopy(source)
        issue=dict(code='SOURCE_RECONCILIATION',detail=dict(code='INNING_RUN_TOTAL_MISMATCH',
            reported=None,observedScoringRows=0,path='/liveData/linescore/innings/8/away'))
        source['issues']=[issue];report=owner.Graph()
        result=owner.outcome(source,report)
        self.assertTrue(all(p['status']=='admitted' for p in result['players']))
        self.assertEqual(result['independentSourceIssues'],[issue])
        self.assertEqual(source,{**original,'issues':[issue]})
        # Actual PA count/membership failures and incomplete turns still block.
        player=source['roster'][0]['player']
        report.add((owner.URIRef('urn:result'),owner.SH.sourceShape,owner.URIRef(
            'urn:baseballo:validation:player-participation:'+player.rsplit('/',1)[-1])))
        checked=owner.outcome(source,report)
        self.assertEqual(next(p for p in checked['players'] if p['player']==player)['issues'],
                         [dict(code='PLAYER_GRAPH_CONFORMANCE')])
        source['issues'].append(dict(code='SOURCE_RECONCILIATION',detail=dict(code='INCOMPLETE_SOURCE_PLAY')))
        self.assertTrue(all(p['status']=='withheld' for p in owner.outcome(source,report)['players']))

    def test_run_total_scope_retries_only_affected_player_proofs(self):
        owner=E.PLAYER_PARTICIPATION
        old=dict(implementationSha256=owner.PREVIOUS_RUN_SCOPE_IMPLEMENTATION,rosterComplete=True,
                 players=[dict(status='admitted',issues=[])])
        self.assertIn(old['implementationSha256'],E.prior_versions('players',owner.fingerprint()))
        self.assertFalse(owner.needs_compound_refresh(old))
        old['players'][0].update(status='withheld',issues=[dict(code='PLAYER_GRAPH_CONFORMANCE')])
        self.assertTrue(owner.needs_compound_refresh(old))  # Missing independent eligibility proof.
        old['eligiblePlayers']=[]
        self.assertFalse(owner.needs_compound_refresh(old))
        old['players'][0]['issues'].append(dict(code='SOURCE_RECONCILIATION',detail=dict(code='TEAM_RUN_TOTAL_MISMATCH')))
        self.assertTrue(owner.needs_compound_refresh(old))
        old['implementationSha256']=owner.fingerprint()
        self.assertFalse(owner.needs_compound_refresh(old))

    def test_ambiguous_roster_does_not_starve_independent_families_or_become_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);promotion=dict(gamePk='1',promotionManifestSha256='promotion')
            witness=dict(kind='retained-b1-census',path='retained-source',sha256='source')
            retained=({},witness);original=E.module
            def module(path,name):
                return SimpleNamespace(available_memory=lambda:2*1024**3) if Path(path).name=='process_state.py' else original(path,name)
            with patch.object(E,'module',side_effect=module),patch.object(E,'checked_marker',return_value={}), \
                 patch.object(E,'diagnostic',return_value={'evidenceState':'current'}), \
                 patch.object(E,'load',side_effect=lambda a,s,p,f:dict(status='withheld' if f in {'batting','pitch-count'} else 'admitted')), \
                 patch.object(E.PLAYER_PARTICIPATION,'load',return_value=None), \
                 patch.object(E.PLAYER_PARTICIPATION,'retained_source',return_value=retained), \
                 patch.object(E.PLAYER_PARTICIPATION,'prove',side_effect=ValueError('A complete unambiguous roster is required')) as prove, \
                 patch.object(E.RETAINED_BATTING,'load',return_value={}), \
                 patch.object(E.EXISTING_GRAPH,'load',side_effect=lambda a,s,p,f,adapter:None if f=='pitch-count' else {}), \
                 patch.object(E.RETAINED_CENSUS,'load',return_value=None), \
                 patch.object(E,'retained_raw_witness',return_value=witness), \
                 patch.object(E,'refresh_existing_graph',return_value=[(Path('proof'),'pitch-count','admitted')]) as refresh:
                result=E.refresh_game(state,promotion,None,None)
                self.assertEqual(result['existingGraphOutcomes'],{'pitch-count':'admitted'})
                self.assertEqual(result['refreshed'],['pitch-count'])
                failure=result['familyFailures']['player-participation']
                self.assertEqual(failure['sourceWitness'],witness)
                self.assertNotIn('admitted',failure.values())
                E.atomic(state/'pipeline/control/mlb-game/admission-evidence/1.json',result)
                with patch.object(E.EXISTING_GRAPH,'load',return_value={}):
                    again=E.refresh_game(state,promotion,None,None)
                self.assertEqual(again['status'],'partial')
                self.assertEqual(again['familyFailures'],result['familyFailures'])
                prove.assert_called_once();refresh.assert_called_once()
                witness['sha256']='new-source'
                prove.side_effect=ValueError('Graph receipt changed')
                with self.assertRaisesRegex(ValueError,'Graph receipt changed'):
                    E.refresh_game(state,promotion,None,None)
                self.assertEqual(prove.call_count,2)

    def test_interrupted_refresh_is_preserved_before_regeneration_and_never_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);promotion=dict(gamePk='1',promotionManifestSha256='promotion')
            proof=E.refresh_path(state,promotion,'m3','producer')
            E.atomic(proof,dict(status='admitted',unwrapped=True))
            E.atomic(proof.with_suffix('.receipt.json'),dict(promotionManifestSha256='promotion',
                proofSha256='previous-completed-proof'))
            E.atomic(proof.with_suffix('.source.json'),dict(sourceSha256='original-input'))
            before={p.name:p.read_bytes() for p in proof.parent.iterdir()}
            failure=dict(promotionManifestSha256='promotion',error='Existing graph admission receipt changed')
            self.assertEqual(E.preserve_interrupted_refresh(state,promotion,dict(failure,error='another failure')),[])
            self.assertEqual(E.preserve_interrupted_refresh(state,promotion,dict(failure,promotionManifestSha256='other')),[])
            preserved=E.preserve_interrupted_refresh(state,promotion,failure)
            self.assertEqual(len(preserved),1)
            archive=Path(preserved[0])
            self.assertEqual({p.name:p.read_bytes() for p in archive.iterdir()},before)
            record=E.read(archive.with_suffix('.json'))
            self.assertFalse(record['rdfChanged'])
            self.assertEqual(record['files'],{p.name:E.sha(p) for p in archive.iterdir()})
            self.assertIsNone(E.refreshed(state,promotion,'m3','producer'))
            self.assertEqual(E.preserve_interrupted_refresh(state,promotion,failure),[])
            # A newly validated set is left intact, even if the old terminal
            # failure remains after an interruption in control-file writing.
            E.atomic(proof,dict(status='withheld'))
            E.atomic(proof.with_suffix('.receipt.json'),dict(promotionManifestSha256='promotion',proofSha256=E.sha(proof)))
            self.assertEqual(E.preserve_interrupted_refresh(state,promotion,failure),[])
            self.assertEqual(E.read(proof)['status'],'withheld')

    def test_retained_sample_is_available_without_acquisition_and_exact_input_wins(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);sample=state/'immutable/42.json';E.atomic(sample,dict(gamePk=42))
            other=state/'pipeline/quarantine/mlb-game/42/repair/input.json';E.atomic(other,dict(gamePk=42,newer=True))
            promotion=dict(gamePk='42',rawSha256=E.sha(sample))
            with patch.object(E,'retained_sample_paths',return_value={'42':[sample]}):
                witness=E.retained_raw_witness(state,promotion)
                self.assertEqual(witness['path'],str(sample))
                self.assertEqual(witness['sha256'],promotion['rawSha256'])
                other.unlink()
                self.assertEqual(E.retained_raw_witness(state,promotion),witness)
            self.assertTrue(sample.is_file())

    def test_corrected_batting_census_reaches_player_check_without_admitting_graph_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);promotion=dict(gamePk='566279',promotionManifestSha256='promotion')
            source=E.PLAYER_PARTICIPATION.B.census((ROOT/'data/raw/game-566279.json').read_bytes(),'566279')
            path=E.refresh_path(state,promotion,'batting','repair').with_suffix('.source.json')
            E.atomic(path,source)
            proof=dict(status='withheld',graphConforms=False,implementationSha256='repair',
                sourceCensusSha256=E.sha(path),proofSha256='checked-repair')
            player=source['members'][0]['player']
            individual=dict(players=[dict(player=player,status='withheld',issues=[
                dict(code='OFFENSIVE_REPLACEMENT_WITHIN_TURN',atBatIndex=0)])],
                retainedSourceEvidence=dict(sha256='original'))
            with patch.object(E.RETAINED_BATTING,'load',return_value=proof):
                corrected,witness=E.corrected_player_source(E,state,promotion,individual)
                self.assertEqual(corrected,source)
                self.assertEqual(witness['battingRepairProofSha256'],'checked-repair')
                self.assertEqual(E.PLAYER_PARTICIPATION.shape_text(corrected),
                                 E.PLAYER_PARTICIPATION.shape_text(source))
                # A real graph failure is still evaluated by the same player
                # SHACL report; correction only removes the old source issue.
                report=E.PLAYER_PARTICIPATION.Graph()
                report.add((E.PLAYER_PARTICIPATION.URIRef('urn:result'),
                    E.PLAYER_PARTICIPATION.SH.sourceShape,E.PLAYER_PARTICIPATION.URIRef(
                    'urn:baseballo:validation:player-participation:'+player.rsplit('/',1)[-1])))
                result=E.PLAYER_PARTICIPATION.outcome(corrected,report)
                rejected=next(p for p in result['players'] if p['player']==player)
                self.assertEqual(rejected['issues'],[dict(code='PLAYER_GRAPH_CONFORMANCE')])
                individual['retainedSourceEvidence']=witness
                self.assertIsNone(E.corrected_player_source(E,state,promotion,individual))
                path.write_text('{}',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'census changed'):
                    E.corrected_player_source(E,state,promotion,individual)

    def test_player_correction_needs_an_existing_reconciled_source(self):
        individual=dict(players=[dict(issues=[dict(code='OFFENSIVE_REPLACEMENT_WITHIN_TURN')])])
        with patch.object(E.RETAINED_BATTING,'load',return_value=None) as load:
            self.assertIsNone(E.corrected_player_source(E,'state',{},individual))
            self.assertEqual(load.call_count,1)
            self.assertIsNone(E.corrected_player_source(E,'state',{},dict(players=[])))
            self.assertEqual(load.call_count,1)

    def test_successful_stages_continue_until_remaining_checks_are_finished(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)
            E.atomic(state/'pipeline/evidence/nifi/game-promotion/1/promotion.json',
                     dict(artifactType='baseball-nifi-game-promotion',gamePk='1',promotedAtUtc='2026-09-29'))
            inventory=SimpleNamespace(query_index_contract_admission=lambda:{},
                validated_promotion_record=lambda *args:dict(gamePk='1'))
            def module(path,name):
                return inventory if Path(path).name=='game_promotion_inventory.py' else SimpleNamespace(fingerprint=lambda:'producer')
            stages=[dict(status='partial-refreshed',refreshed=['player-participation']),
                dict(status='refreshed',refreshed=['batting']),
                dict(status='refreshed',refreshed=['runner-resolution','pitch-count']),
                dict(status='refreshed',refreshed=['pa-runner-resolution']),dict(status='current')]
            with patch.object(E,'module',side_effect=module),patch.object(E,'fingerprint',return_value='worker'), \
                 patch.object(E,'dashboard_game_priorities',return_value={}),patch.object(E,'refresh_game',side_effect=stages) as refresh:
                for _ in stages:
                    self.assertEqual(E.tick(state,Path('java'),Path('classpath'))['processedGames'],1)
                self.assertEqual(E.tick(state,Path('java'),Path('classpath'))['processedGames'],0)
                self.assertEqual(refresh.call_count,len(stages))

    def test_retry_allowance_counts_failures_and_restarts_for_new_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'pipeline/evidence/nifi/game-promotion/1/promotion.json'
            E.atomic(marker,dict(artifactType='baseball-nifi-game-promotion',gamePk='1',promotedAtUtc='2026-09-29'))
            inventory=SimpleNamespace(query_index_contract_admission=lambda:{},
                validated_promotion_record=lambda *args:dict(gamePk='1'))
            def module(path,name):
                return inventory if Path(path).name=='game_promotion_inventory.py' else SimpleNamespace(fingerprint=lambda:'producer')
            control=state/'pipeline/control/mlb-game/admission-evidence/1.json'
            with patch.object(E,'module',side_effect=module),patch.object(E,'fingerprint',return_value='worker'), \
                 patch.object(E,'dashboard_game_priorities',return_value={}),patch.object(E,'refresh_game') as refresh:
                refresh.return_value=dict(status='waiting-for-memory',availableMemoryBytes=900*1024**2)
                for _ in range(3):E.tick(state,Path('java'),Path('classpath'))
                refresh.side_effect=ValueError('validation interrupted')
                for count in (1,2):
                    self.assertEqual(E.tick(state,Path('java'),Path('classpath'))['processedGames'],1)
                    self.assertEqual(E.read(control)['failureAttempts'],count)
                    if count==1:
                        refresh.side_effect=None
                        E.tick(state,Path('java'),Path('classpath'))
                        self.assertEqual(E.read(control)['failureAttempts'],1)
                        refresh.side_effect=ValueError('validation interrupted')
                self.assertEqual(E.tick(state,Path('java'),Path('classpath'))['processedGames'],0)
                self.assertEqual(refresh.call_count,6)
                E.atomic(marker,dict(artifactType='baseball-nifi-game-promotion',gamePk='1',promotedAtUtc='2026-09-30'))
                refresh.side_effect=None;refresh.return_value=dict(status='current')
                self.assertEqual(E.tick(state,Path('java'),Path('classpath'))['processedGames'],1)
                result=E.read(control)
                self.assertEqual((result['attempts'],result['failureAttempts']),(1,0))

    def test_retained_raw_refresh_does_not_require_retired_local_rdf_or_another_batting_check(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'pipeline/quarantine/mlb-game/1/run/input.json'
            E.atomic(source,dict(gamePk=1))
            promotion=dict(gamePk='1',rawSha256='older-promotion-source',promotionManifestSha256='promotion')
            original=E.module
            def module(path,name):
                return SimpleNamespace(available_memory=lambda:2*1024**3) if Path(path).name=='process_state.py' else original(path,name)
            with patch.object(E,'module',side_effect=module),patch.object(E,'checked_marker',return_value={}), \
                 patch.object(E,'diagnostic',return_value={'evidenceState':'implementation-stale'}), \
                 patch.object(E,'refreshed',return_value=None),patch.object(E,'load',side_effect=lambda a,s,p,f:
                    {'status':'withheld' if f=='pitch-count' else 'admitted'}), \
                 patch.object(E.PLAYER_PARTICIPATION,'load',return_value={}), \
                 patch.object(E.RETAINED_BATTING,'load',return_value={}), \
                 patch.object(E.EXISTING_GRAPH,'load',return_value=None), \
                 patch.object(E,'retained_manifest',side_effect=AssertionError('Retired export is not required')), \
                 patch.object(E,'refresh_existing_graph',return_value=[(Path('proof'),'pitch-count','admitted')]) as refresh:
                result=E.refresh_game(state,promotion,Path('java'),Path('classpath'))
            self.assertEqual(result['existingGraphOutcomes'],{'pitch-count':'admitted'})
            witness=refresh.call_args.args[2]
            self.assertEqual(witness,dict(kind='retained-source-response',path=str(source),sha256=E.sha(source)))
            self.assertNotEqual(witness['sha256'],promotion['rawSha256'])

    def test_existing_graph_refresh_keeps_withholding_and_commits_only_after_final_promotion_check(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'promotions/one.json'
            E.atomic(marker,dict(promotedAtUtc='2026-09-29T00:00:00Z'))
            promotion=dict(gamePk='1',promotionManifest=str(marker),promotionManifestSha256=E.sha(marker),
                rawSha256='original-source',authoritativeRdfSha256='promoted-rdf',
                authoritativeGraph='https://w3id.org/baseball/graph/game/1',authoritativeTripleCount=2)
            inventory=SimpleNamespace(query_index_contract_admission=lambda:{},
                validated_promotion_record=Mock(return_value=promotion))
            jena=SimpleNamespace(Session=lambda *args:nullcontext(SimpleNamespace(data_count=2)))
            modules={'game_promotion_inventory.py':inventory,'jena_session.py':jena}
            outcomes=[(Path('proof'),'pitch-count','withheld')]
            source=state/'source.json';source.write_bytes(b'original source')
            witness=dict(path=str(source),sha256=E.sha(source))
            with patch.object(E,'module',side_effect=lambda p,n:modules[Path(p).name]), \
                 patch.object(E,'existing_graph_refresh_needed',return_value=True), \
                 patch.object(E.urllib.request,'urlopen',side_effect=lambda *a,**kw:io.BytesIO(b'export')) as request, \
                 patch.object(E.EXISTING_GRAPH,'validate',return_value=outcomes) as validate, \
                 patch.object(E.EXISTING_GRAPH,'commit') as commit:
                result=E.refresh_existing_graph(state,promotion,witness,Path('java'),Path('jar'),
                                                'http://127.0.0.1:3031/baseball-dev/query')
                self.assertEqual(result,outcomes)
                self.assertEqual(commit.call_args.args[-1],outcomes)
                self.assertEqual(inventory.validated_promotion_record.call_count,2)
                self.assertTrue(request.call_args.args[0].data.startswith(b'CONSTRUCT'))
                commit.reset_mock()
                def changed(*args):
                    E.atomic(marker,dict(promotedAtUtc='2026-09-29T01:00:00Z'))
                    return outcomes
                validate.side_effect=changed
                with self.assertRaisesRegex(ValueError,'Promotion changed'):
                    E.refresh_existing_graph(state,promotion,witness,Path('java'),Path('jar'),
                                             'http://127.0.0.1:3031/baseball-dev/query')
                commit.assert_not_called()

    def test_current_admissions_reuse_verified_proofs_without_export_or_jvm(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'promotions/one.json';E.atomic(marker,dict(promotedAtUtc='now'))
            source=state/'source.json';source.write_bytes(b'original')
            promotion=dict(gamePk='1',promotionManifest=str(marker),promotionManifestSha256=E.sha(marker),
                rawSha256='original',authoritativeRdfSha256='rdf',authoritativeGraph='urn:game',authoritativeTripleCount=1)
            inventory=SimpleNamespace(query_index_contract_admission=lambda:{},validated_promotion_record=lambda *args:promotion)
            witness=dict(path=str(source),sha256=E.sha(source))
            with patch.object(E,'module',return_value=inventory),patch.object(E,'load',return_value=dict(status='withheld')), \
                    patch.object(E.EXISTING_GRAPH,'load',return_value=dict(status='withheld')) as load, \
                    patch.object(E.urllib.request,'urlopen',side_effect=AssertionError('no export')):
                self.assertEqual(E.refresh_existing_graph(state,promotion,witness,None,None,'endpoint'),[])
                self.assertEqual(load.call_count,len(E.EXISTING_GRAPH.SHORT))
                source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'response changed'):
                    E.refresh_existing_graph(state,promotion,witness,None,None,'endpoint')

    def test_memory_deferral_yields_but_smaller_checks_and_later_retry_can_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)
            for pk in ('1','2'):
                E.atomic(state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json',
                         dict(artifactType='baseball-nifi-game-promotion',gamePk=pk,promotedAtUtc='2026-09-29'))
            original=E.module
            inventory=SimpleNamespace(query_index_contract_admission=lambda:{},
                validated_promotion_record=lambda state,path,pk,admission:dict(gamePk=pk))
            def module(path,name):
                return inventory if Path(path).name=='game_promotion_inventory.py' else original(path,name)
            refresh=Mock()
            with patch.object(E,'module',side_effect=module),patch.object(E,'dashboard_game_priorities',return_value={}), \
                 patch.object(E,'refresh_game',refresh):
                refresh.return_value=dict(status='waiting-for-memory',availableMemoryBytes=900*1024*1024)
                result=E.tick(state,Path('java'),Path('classpath'))
                self.assertEqual(result['processedGames'],1)
                self.assertEqual(refresh.call_count,1)
                # A 1.2 GiB reserve only blocks the larger operation. Keep the
                # bounded scan so a following smaller validation can proceed.
                refresh.reset_mock();refresh.side_effect=[
                    dict(status='waiting-for-memory',availableMemoryBytes=1200*1024*1024),
                    dict(status='refreshed',refreshed=['player-participation'])]
                result=E.tick(state,Path('java'),Path('classpath'))
                self.assertEqual((result['processedGames'],result['refreshedGames']),(2,1))
                self.assertEqual(refresh.call_args_list[0].args[1]['gamePk'],'1')

    def test_w1_pins_preserve_unrelated_context_definitions_and_exact_prior_versions(self):
        record=E.read(E.COMPATIBILITY_PATH);walk=record['intentionalWalkPrefix']
        before=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            walk['baselineCommit']+':Baseball/'+record['contextPath']])
        compound=record.get('compoundResultRepair')
        after=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            compound['baselineCommit']+':Baseball/'+record['contextPath']]) if compound
            else (ROOT/record['contextPath']).read_bytes())
        self.assertEqual(hashlib.sha256(before).hexdigest(),walk['previousContextSha256'])
        self.assertEqual(hashlib.sha256(after).hexdigest(),walk['currentContextSha256'])
        excluded={'zero_episode_replacement_witness','zero_pitch_walk_terminal','runner_metric_evidence','main'}
        def unchanged(raw):
            tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in excluded]
            return ast.dump(tree)
        self.assertEqual(unchanged(before),unchanged(after))
        groundout=record.get('defensiveGroundoutRepair')
        history=record.get('historySelectionRepair')
        foul=record.get('foulPrefixRepair')
        selection=record.get('foulDefenseSelectionRepair')
        error_prefix=record.get('errorCountPrefixRepair')
        batter_chain=record.get('prePitchBatterChain')
        final_award=record.get('finalAwardSelection')
        runner_review=record.get('runnerReviewCompletion')
        foul_pitcher=record.get('foulPitcherCompletion')
        current=next(v for v in record.values() if isinstance(v,dict)
            and v.get('currentContextSha256')==E.sha(ROOT/record['contextPath']))
        if compound:
            now=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                groundout['baselineCommit']+':Baseball/'+record['contextPath']]) if groundout
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(now).hexdigest(),compound['currentContextSha256'])
            def unaffected(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in {'compound_double_play_parts','main'}]
                return ast.dump(tree)
            self.assertEqual(unaffected(after),unaffected(now))
        if groundout:
            latest=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                history['baselineCommit']+':Baseball/'+record['contextPath']]) if history
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(latest).hexdigest(),groundout['currentContextSha256'])
            def nondefensive(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None)!='defensive_act_context']
                return ast.dump(tree)
            self.assertEqual(nondefensive(now),nondefensive(latest))
        if history:
            updated=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                foul['baselineCommit']+':Baseball/'+record['contextPath']]) if foul
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(updated).hexdigest(),history['currentContextSha256'])
            self.assertEqual(hashlib.sha256(latest).hexdigest(),history['previousContextSha256'])
            changed={'accounted_runner_history_reviews','completed_pickoff_review',
                     'nonmovement_strikeout_records','reconciled_action_pitch_overlap','personal_runner_histories',
                     'unchanged_runner_tag_review','completed_field_review_dispositions','completed_nonterminal_field_review',
                     'completed_independent_review','reconciled_pitch_counter_order','reconciled_pa_boundary_order',
                     'defensive_act_context','runner_state_neutral_event','counted_foul_running_prefix','counted_foul_neutral_event','metric_pitch_context'}
            def nonhistory(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in changed]
                return ast.dump(tree)
            self.assertEqual(nonhistory(latest),nonhistory(updated))
        if foul:
            active=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                selection['baselineCommit']+':Baseball/'+record['contextPath']]) if selection
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(updated).hexdigest(),foul['previousContextSha256'])
            self.assertEqual(hashlib.sha256(active).hexdigest(),foul['currentContextSha256'])
            def nonfoul(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None)!='counted_foul_neutral_event']
                return ast.dump(tree)
            self.assertEqual(nonfoul(updated),nonfoul(active))
            for family,entry in foul['families'].items():
                reuse=E.code_equivalence(family,entry['previousImplementationSha256'],entry['currentImplementationSha256'],
                    _context=foul['currentContextSha256'])
                self.assertEqual(reuse['kind'],'unchanged-admission-census')
                self.assertIsNone(E.code_equivalence(family,'unknown',entry['currentImplementationSha256']))
                self.assertIsNone(E.code_equivalence(family,entry['previousImplementationSha256'],'unknown'))
        if selection:
            candidate=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                error_prefix['baselineCommit']+':Baseball/'+record['contextPath']]) if error_prefix
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(active).hexdigest(),selection['previousContextSha256'])
            self.assertEqual(hashlib.sha256(candidate).hexdigest(),selection['currentContextSha256'])
            changed={'completed_field_review_dispositions','completed_nonterminal_field_review',
                'runner_state_neutral_event','counted_foul_neutral_event','metric_pitch_context','defensive_act_context'}
            def unaffected_selection(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in changed]
                return ast.dump(tree)
            self.assertEqual(unaffected_selection(active),unaffected_selection(candidate))
            for family,entry in selection['families'].items():
                reuse=E.code_equivalence(family,entry['previousImplementationSha256'],entry['currentImplementationSha256'],
                    _context=selection['currentContextSha256'])
                self.assertEqual(reuse['kind'],entry['reuseKind'])
                self.assertIsNone(E.code_equivalence(family,'unknown',entry['currentImplementationSha256']))
                self.assertIsNone(E.code_equivalence(family,entry['previousImplementationSha256'],'unknown'))
        if error_prefix:
            live=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                batter_chain['baselineCommit']+':Baseball/'+record['contextPath']]) if batter_chain
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(candidate).hexdigest(),error_prefix['previousContextSha256'])
            self.assertEqual(hashlib.sha256(live).hexdigest(),error_prefix['currentContextSha256'])
            def outside_error_prefix(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None)!='counted_foul_running_prefix']
                return ast.dump(tree)
            self.assertEqual(outside_error_prefix(candidate),outside_error_prefix(live))
            for family,entry in error_prefix['families'].items():
                reuse=E.code_equivalence(family,entry['previousImplementationSha256'],entry['currentImplementationSha256'],
                    _context=error_prefix['currentContextSha256'])
                self.assertEqual(reuse['kind'],entry['reuseKind'])
                self.assertIsNone(E.code_equivalence(family,'unknown',entry['currentImplementationSha256']))
                self.assertIsNone(E.code_equivalence(family,entry['previousImplementationSha256'],'unknown'))
        if batter_chain:
            updated=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                final_award['baselineCommit']+':Baseball/'+record['contextPath']]) if final_award
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(live).hexdigest(),batter_chain['previousContextSha256'])
            self.assertEqual(hashlib.sha256(updated).hexdigest(),batter_chain['currentContextSha256'])
            def outside_batter_chain(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in
                    {'counted_foul_initial_batter_chain','counted_foul_neutral_event'}]
                return ast.dump(tree)
            self.assertEqual(outside_batter_chain(live),outside_batter_chain(updated))
            for family,entry in batter_chain['families'].items():
                self.assertIsNotNone(E.code_equivalence(family,entry['previousImplementationSha256'],entry['currentImplementationSha256'],
                    _context=batter_chain['currentContextSha256']))
                self.assertIsNone(E.code_equivalence(family,'unknown',entry['currentImplementationSha256']))
        if final_award:
            active=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                runner_review['baselineCommit']+':Baseball/'+record['contextPath']]) if runner_review
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(updated).hexdigest(),final_award['previousContextSha256'])
            self.assertEqual(hashlib.sha256(active).hexdigest(),final_award['currentContextSha256'])
            def outside_final_award(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in
                    {'intentional_walk_award_terminal','runner_metric_evidence'}]
                return ast.dump(tree)
            self.assertEqual(outside_final_award(updated),outside_final_award(active))
        if runner_review:
            current_context=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                foul_pitcher['baselineCommit']+':Baseball/'+record['contextPath']]) if foul_pitcher
                else (ROOT/record['contextPath']).read_bytes())
            self.assertEqual(hashlib.sha256(active).hexdigest(),runner_review['previousContextSha256'])
            self.assertEqual(hashlib.sha256(current_context).hexdigest(),runner_review['currentContextSha256'])
            changed={'completed_nonterminal_field_review','catcher_pickoff_boundary_kind',
                     'accounted_runner_history_reviews','runner_boundary_anchors'}
            def outside_runner_review(raw):
                tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None) not in changed]
                return ast.dump(tree)
            self.assertEqual(outside_runner_review(active),outside_runner_review(current_context))
        for family,entry in walk['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'w1_'+family.replace('-','_'))
            expected=(record['missingCountResultHandling'] if not final_award and family=='pitch-count' and
                'missingCountResultHandling' in record else current['families'][family])
            self.assertEqual(adapter.fingerprint(),expected['currentImplementationSha256'])
            clock=record['priorClockIsolation']['families'].get(family)
            if clock:
                self.assertIsNotNone(E.code_equivalence(family,clock['previousImplementationSha256'],adapter.fingerprint()))
            independent=current['independentProofs'][family]
            self.assertEqual(E.EXISTING_GRAPH.fingerprint(E,adapter),independent['currentImplementationSha256'])
            self.assertEqual(walk['independentProofs'][family]['previousSourceProducerSha256'],entry['previousImplementationSha256'])
        for kind,adapter in [('players',E.PLAYER_PARTICIPATION),('pa',E.PLAYER_PARTICIPATION.PA),('c2pa',E.PA_RESOLUTION)]:
            entry=current['derivedProofs'][kind]
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            self.assertEqual(E.prior_versions(kind,adapter.fingerprint()),entry['previousImplementationSha256s'])
            self.assertEqual(E.prior_versions(kind,'unknown'),[])

    def test_missing_count_result_fix_preserves_every_previously_produced_census(self):
        record=E.read(E.COMPATIBILITY_PATH);repair=record['missingCountResultHandling']
        path=E.HERE/'pitch-count-admission.py'
        context=ROOT/record['contextPath'];successor=record.get('finalAwardSelection')
        after=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            successor['baselineCommit']+':Baseball/sources/mlb-game/pipeline/pitch-count-admission.py'])
            if successor else path.read_bytes())
        prior_context=(subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            successor['baselineCommit']+':Baseball/'+record['contextPath']]) if successor else context.read_bytes())
        before=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            repair['baselineCommit']+':Baseball/sources/mlb-game/pipeline/pitch-count-admission.py'])
        self.assertEqual(before.replace(b"result_type=play['result']['eventType']",
            b"result_type=play.get('result',{}).get('eventType')"),after)
        adapter=E.module(path,'missing_result_equivalence')
        original=Path.read_bytes
        def previous(p):return before if p.resolve()==path.resolve() else prior_context if p.resolve()==context.resolve() else original(p)
        with patch.object(Path,'read_bytes',previous):
            self.assertEqual(adapter.fingerprint(),repair['previousImplementationSha256'])
        def current(p):return after if p.resolve()==path.resolve() else prior_context if p.resolve()==context.resolve() else original(p)
        with patch.object(Path,'read_bytes',current):
            self.assertEqual(adapter.fingerprint(),repair['currentImplementationSha256'])
        self.assertIsNotNone(E.code_equivalence('pitch-count',repair['previousImplementationSha256'],repair['currentImplementationSha256'],_context=repair['contextSha256']))
        self.assertIsNone(E.code_equivalence('pitch-count','unknown',repair['currentImplementationSha256'],_context=repair['contextSha256']))

    def test_expanded_selection_does_not_reuse_an_older_negative_independent_proof(self):
        record=E.read(E.COMPATIBILITY_PATH)['prePitchBatterChain']
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);promotion=dict(gamePk='1',promotionManifestSha256='retained')
            for family in ('runner-resolution','pitch-count','runner-boundary','defensive'):
                adapter=E.module(E.HERE/(family+'-admission.py'),'f5_negative_'+family.replace('-','_'))
                prior=record['independentProofs'][family]['previous'][0]
                self.assertTrue(prior['requiresOriginalAdmission'])
                path=E.refresh_path(state,promotion,E.EXISTING_GRAPH.SHORT[family],prior['previousImplementationSha256'])
                E.atomic(path,dict(status='withheld'))
                E.atomic(path.with_suffix('.receipt.json'),{})
                self.assertIsNone(E.EXISTING_GRAPH.load(E,state,promotion,family,adapter))

    def test_season_priority_repairs_early_missing_qualification_before_recent_checked_games(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);database=state/'serving/dashboard/builds/current.sqlite'
            database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as db, db:
                db.executescript('''CREATE TABLE game_dimension(graph_iri TEXT,game_pk TEXT,game_set TEXT,season INTEGER);
                    CREATE TABLE metric_suite_admission(graph_iri TEXT,proof_json TEXT);
                    CREATE TABLE metric_suite_runner_resolution_admission(graph_iri TEXT,proof_json TEXT);
                    CREATE TABLE dashboard_player_admission(graph_iri TEXT,proof_json TEXT);
                    CREATE TABLE dashboard_player_game(graph_iri TEXT,roster_complete INTEGER);''')
                for pk,season in [('100',2025),('101',2026),('102',2026),('103',2026),('104',2026)]:
                    db.execute('INSERT INTO game_dimension VALUES (?,?,?,?)',('g'+pk,pk,'regular_season',season))
                    db.execute('INSERT INTO metric_suite_admission VALUES (?,?)',('g'+pk,json.dumps(dict(status='withheld'))))
                    if pk!='104':db.execute('INSERT INTO dashboard_player_game VALUES (?,1)',('g'+pk,))
                db.execute('INSERT INTO dashboard_player_admission VALUES (?,?)',('g102',json.dumps(
                    dict(implementationSha256=E.PLAYER_PARTICIPATION.fingerprint()))))
                db.execute('UPDATE metric_suite_admission SET proof_json=? WHERE graph_iri=?',
                    (json.dumps(dict(status='admitted')),'g103'))
            E.atomic(state/'serving/dashboard-current.json',dict(databasePath=str(database)))
            priority=E.dashboard_game_priorities(state)
            self.assertEqual(sorted(priority,key=lambda pk:(priority[pk],pk)),['104','101','102','103'])
            self.assertNotIn('100',priority)
            self.assertEqual(priority['102'],priority['103'])
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('INSERT INTO metric_suite_runner_resolution_admission VALUES (?,?)',
                    ('g103',json.dumps(dict(status='withheld'))))
            priority=E.dashboard_game_priorities(state)
            self.assertEqual(sorted(priority,key=lambda pk:(priority[pk],pk)),['104','101','103','102'])
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('UPDATE dashboard_player_admission SET proof_json=? WHERE graph_iri=?',
                    (json.dumps(dict(implementationSha256=E.PLAYER_PARTICIPATION.fingerprint(),
                        players=[dict(issues=[dict(code='OFFENSIVE_REPLACEMENT_WITHIN_TURN')])])),'g102'))
            self.assertEqual(E.dashboard_game_priorities(state)['102'],1)

    def test_prior_admitted_clock_proofs_have_identical_checks_when_source_issues_are_empty(self):
        record=E.read(E.COMPATIBILITY_PATH)['priorClockIsolation']
        def old(path):
            return subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                record['changeCommit']+'^:Baseball/'+path])
        def tree(text):return ast.dump(ast.parse(text),include_attributes=False)
        source='sources/mlb-game/pipeline/reconcile-metric-source.py'
        before=ast.parse(old(source));after=ast.parse((ROOT/source).read_bytes())
        definitions={n.name:n for n in after.body if isinstance(n,ast.FunctionDef)}
        current=definitions['reconcile']
        # T1 adds an issue partition and diagnostic values, not new issue
        # predicates. Verify those exact edits before comparing the whole AST.
        added={
            'clock_conflicts':"clock_conflicts = [i for i in issues if i['code'] in CLOCK_CONFLICT_CODES]",
            'blocking_issues':"blocking_issues = [i for i in issues if i['code'] not in CLOCK_CONFLICT_CODES]"}
        for name,statement in added.items():
            matches=[n for n in current.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
            self.assertEqual(len(matches),1)
            self.assertEqual(ast.dump(matches[0]),ast.dump(ast.parse(statement).body[0]))
            current.body.remove(matches[0])
        returned=current.body[-1].value
        extra={k.arg:k.value for k in returned.keywords if k.arg in {'blockingIssues','clockConflicts','clockDecision','clockStatus'}}
        expected=ast.parse("dict(blockingIssues=blocking_issues,clockConflicts=clock_conflicts,clockDecision=CLOCK_DECISION,clockStatus='conflicted' if clock_conflicts else 'no-reversed-pairs')").body[0].value
        self.assertEqual({k:ast.dump(v) for k,v in extra.items()},{k.arg:ast.dump(k.value) for k in expected.keywords})
        returned.keywords=[k for k in returned.keywords if k.arg not in extra]
        status=next(k for k in returned.keywords if k.arg=='status')
        self.assertEqual(ast.dump(status.value),ast.dump(ast.parse("'consistent' if not blocking_issues else 'inconsistent'",mode='eval').body))
        status.value=ast.parse("'consistent' if not issues else 'inconsistent'",mode='eval').body
        for node in ast.walk(current):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='issue' and node.args and isinstance(node.args[0],ast.Constant):
                code=node.args[0].value
                if code in {'REVERSED_PLAY_TIMES','REVERSED_EVENT_TIMES'}:
                    variable='about' if code=='REVERSED_PLAY_TIMES' else 'event'
                    self.assertEqual({k.arg:ast.dump(k.value) for k in node.keywords},
                        {key:ast.dump(ast.parse(variable+"['"+key+"']",mode='eval').body) for key in ('startTime','endTime')})
                    node.keywords=[]
        constants={n.targets[0].id:n for n in after.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
        self.assertEqual(ast.literal_eval(constants['CLOCK_CONFLICT_CODES'].value),{'REVERSED_PLAY_TIMES','REVERSED_EVENT_TIMES'})
        self.assertEqual(ast.literal_eval(constants['CLOCK_DECISION'].value),'archive/design-records/mlb-game-clock-conflict-isolation/review.json')
        self.assertEqual(ast.literal_eval(constants['VERSION'].value),2)
        constants['VERSION'].value=ast.Constant(1)
        after.body=[n for n in after.body if n not in (constants['CLOCK_CONFLICT_CODES'],constants['CLOCK_DECISION'])]
        self.assertEqual(ast.dump(before),ast.dump(after))

        class PriorIssueKey(ast.NodeTransformer):
            def visit_Subscript(self,node):
                self.generic_visit(node)
                if isinstance(node.slice,ast.Constant) and node.slice.value=='blockingIssues':node.slice.value='issues'
                return node
        for family,entry in record['families'].items():
            if family in {'pitch-count','runner-boundary'}:
                continue  # Context-dependent positive cases are exercised below.
            own='sources/mlb-game/pipeline/'+family+'-admission.py'
            shape='sources/mlb-game/shacl/'+family+'-admission.ttl'
            support='sources/mlb-game/pipeline/batting-admission.py'
            validator='scripts/pipeline/validate-shacl.py';context='scripts/pipeline/prepare-rml-context.py'
            adapter=E.module(ROOT/own,'prior_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),current_implementation(family,entry))
            historical=subprocess.check_output(['git','-C',str(ROOT.parent),'show',record['changeCommit']+':Baseball/'+own])
            self.assertEqual(tree(old(own)),ast.dump(PriorIssueKey().visit(ast.parse(historical))))
            for unchanged in (shape,validator):self.assertEqual(old(unchanged),(ROOT/unchanged).read_bytes())
            paths=([own,shape,source,validator] if family=='batting' else
                [own,shape,support,source,validator] if family=='scoring-run' else
                [own,shape,context,support,source,validator])
            digest=hashlib.sha256('\n'.join(p+':'+hashlib.sha256(old(p)).hexdigest() for p in paths).encode()).hexdigest()
            self.assertEqual(digest,entry['previousImplementationSha256'])
            if family=='runner-resolution':
                definition=lambda raw:next(n for n in ast.parse(raw).body if getattr(n,'name',None)=='nonmovement_strikeout_records')
                self.assertEqual(ast.dump(definition(old(context))),ast.dump(definition(subprocess.check_output(['git','-C',str(ROOT.parent),'show',record['changeCommit']+':Baseball/'+context]))))

    def test_prior_clock_reuse_requires_positive_hash_bound_source_census(self):
        record=E.read(E.COMPATIBILITY_PATH)
        entries=[(family,entry,kind) for section,kind in
            [('priorClockIsolation','prior-stricter-clock-check'),
             ('priorPinchHitterIsolation','prior-stricter-pinch-hitter-check')]
            for family,entry in record[section]['families'].items()]
        for family,entry,kind in entries:
            with self.subTest(family=family),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run'/f'{family}.json'
                proof=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,gamePk='1',
                    graph='graph',sourceSha256='source',authoritativeRdfSha256='rdf',
                    implementationSha256=entry['previousImplementationSha256'],status='admitted',
                    sourceReconciled=True,graphConforms=True,issues=[])
                for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                    E.atomic(path.with_suffix(suffix),dict(gamePk='1',sourceSha256='source',status='reconciled',issues=[]))
                    proof[key]=E.sha(path.with_suffix(suffix))
                marker=state/'promotion.json';field=E.FIELDS[family]
                def publish(value):
                    E.atomic(path,value);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                    return dict(gamePk='1',rawSha256='source',authoritativeGraph='graph',authoritativeRdfSha256='rdf',
                        promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
                promotion=publish(proof)
                result=E.compatible_proof(state,promotion,family,entry['currentImplementationSha256'])
                self.assertEqual({key:result[key] for key in proof},proof)
                self.assertEqual(result['implementationReuse']['kind'],kind)
                self.assertIsNone(E.compatible_proof(state,promotion,family,'unknown-next-version'))
                self.assertIsNone(E.compatible_proof(state,{**promotion,'rawSha256':'different'},family,entry['currentImplementationSha256']))
                self.assertIsNone(E.compatible_proof(state,publish({**proof,'status':'withheld'}),family,entry['currentImplementationSha256']))
                E.atomic(path.with_suffix('.source.json'),dict(gamePk='1',sourceSha256='source',status='withheld',issues=[dict(code='REVERSED_PLAY_TIMES')]))
                inconsistent={**proof,'sourceCensusSha256':E.sha(path.with_suffix('.source.json'))}
                with self.assertRaisesRegex(ValueError,'reconciled source census'):
                    E.compatible_proof(state,publish(inconsistent),family,entry['currentImplementationSha256'])

    def test_prior_positive_count_and_boundary_checks_preserve_census_and_shapes(self):
        record=E.read(E.COMPATIBILITY_PATH)
        raw=(ROOT/'data/raw/game-566279.json').read_bytes()
        for section,families in [('priorClockIsolation',('pitch-count','runner-boundary')),
                                 ('priorPinchHitterIsolation',('runner-boundary',))]:
            change=record[section]
            for family in families:
                with self.subTest(section=section,family=family),tempfile.TemporaryDirectory() as temp:
                    own='sources/mlb-game/pipeline/'+family+'-admission.py'
                    shape='sources/mlb-game/shacl/'+family+'-admission.ttl'
                    context='scripts/pipeline/prepare-rml-context.py'
                    support='sources/mlb-game/pipeline/batting-admission.py'
                    source='sources/mlb-game/pipeline/reconcile-metric-source.py'
                    validator='scripts/pipeline/validate-shacl.py'
                    paths=([own,shape,context,support,source,validator] if family=='runner-boundary' else
                           [own,shape,support,source,context,validator])
                    prior_root=Path(temp)/'Baseball'
                    for relative in paths:
                        contents=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                            change['changeCommit']+'^:Baseball/'+relative])
                        target=prior_root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_bytes(contents)
                    before=E.module(prior_root/own,'old_positive_'+family.replace('-','_'))
                    after=E.module(ROOT/own,'current_positive_'+family.replace('-','_'))
                    entry=change['families'][family]
                    self.assertEqual(before.fingerprint(),entry['previousImplementationSha256'])
                    self.assertEqual(after.fingerprint(),current_implementation(family,entry))
                    for unchanged in (shape,validator):
                        self.assertEqual((prior_root/unchanged).read_bytes(),(ROOT/unchanged).read_bytes())
                    previous=before.census(raw,'566279');current=after.census(raw,'566279')
                    self.assertEqual(previous['issues'],[])
                    self.assertEqual(current,previous)
                    self.assertEqual(after.shape_text(current),before.shape_text(previous))
                    # The newly handled initial PH case could not supply a
                    # previous positive check. Existing complete substitutions
                    # keep their exact participants, even across both edits.
                    doc=json.loads((ROOT/'data/raw/samples/2026-07-18/824169.json').read_bytes())
                    play=doc['liveData']['plays']['allPlays'][31]
                    self.assertEqual(before.CONTEXT.batter_participation_context(play,'824169',source_consistent=True),
                                     after.CONTEXT.batter_participation_context(play,'824169',source_consistent=True))
                    play['playEvents']=play['playEvents'][3:]
                    for index,event in enumerate(play['playEvents']):event['index']=index
                    play['playEvents'][0].pop('replacedPlayer')
                    play['playEvents'][0]['count'].update(balls=0,strikes=0)
                    with self.assertRaises((KeyError,ValueError)):
                        before.CONTEXT.batter_participation_context(play,'824169',source_consistent=True)
                    self.assertEqual(len(after.CONTEXT.batter_participation_context(play,'824169',source_consistent=True)['participations']),1)

    def test_exact_q5_edit_does_not_change_reused_proof_dependencies(self):
        record=E.read(E.COMPATIBILITY_PATH)
        path=ROOT/record['contextPath']
        old=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            record['changeCommit']+'^:Baseball/'+record['contextPath']])
        current=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            '400f1ef2fb62:Baseball/'+record['contextPath']])
        self.assertEqual(hashlib.sha256(old).hexdigest(),record['previousContextSha256'])
        self.assertEqual(hashlib.sha256(current).hexdigest(),record['currentContextSha256'])
        before,after=ast.parse(old),ast.parse(current)
        changed=record['changedDefinition']
        # The whole module, including imports and constants, must be identical
        # apart from this one definition. Never infer compatibility by labels.
        def without_changed(tree):
            clone=copy.deepcopy(tree)
            clone.body=[n for n in clone.body if getattr(n,'name',None)!=changed]
            return ast.dump(clone,include_attributes=False)
        self.assertEqual(without_changed(before),without_changed(after))
        definitions={n.name:n for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old_definitions={n.name:n for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertNotEqual(ast.dump(old_definitions[changed]),ast.dump(definitions[changed]))
        for family,entry in record['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'equivalence_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),current_implementation(family,entry))
            baseline=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
                record['intentionalWalkPrefix']['baselineCommit']+':Baseball/sources/mlb-game/pipeline/'+family+'-admission.py'])
            context_attributes={n.attr for n in ast.walk(ast.parse(baseline))
                if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='CONTEXT'}
            self.assertEqual(context_attributes,set(entry['contextDefinitions']))
            visited=set();pending=list(context_attributes & definitions.keys())
            while pending:
                name=pending.pop()
                if name in visited:continue
                visited.add(name)
                nodes=list(ast.walk(definitions[name]))
                self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                    and n.func.id in {'eval','exec','getattr','globals','locals','__import__','module'} for n in nodes))
                pending.extend({n.id for n in nodes if isinstance(n,ast.Name)} & definitions.keys()-visited)
            self.assertNotIn(changed,visited,family)
            common=[E.HERE/'batting-admission.py',E.HERE/'reconcile-metric-source.py',ROOT/'scripts/pipeline/validate-shacl.py']
            paths=([Path(adapter.__file__),adapter.SHAPE,path,*common] if family=='runner-resolution' else
                [Path(adapter.__file__),adapter.SHAPE,*common[:2],path,common[2]])
            prior=hashlib.sha256('\n'.join(p.relative_to(ROOT).as_posix()+':'+
                (record['previousContextSha256'] if p==path else hashlib.sha256(baseline).hexdigest()
                 if p==Path(adapter.__file__) else hashlib.sha256(subprocess.check_output(
                     ['git','-C',str(ROOT.parent),'show',record['changeCommit']+'^:Baseball/'+p.relative_to(ROOT).as_posix()])).hexdigest()) for p in paths).encode()).hexdigest()
            self.assertEqual(prior,entry['previousImplementationSha256'])
        self.assertNotIn('runner-boundary',record['families'])

    def test_q7_changes_only_history_selection_and_preserves_unrelated_proof_dependencies(self):
        record=E.read(E.COMPATIBILITY_PATH)
        bridge=record['zeroEpisodeIsolation']
        path=ROOT/record['contextPath']
        prior=subprocess.check_output(['git','-C',str(ROOT.parent),'show','400f1ef2fb62:Baseball/'+record['contextPath']])
        current=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            record['intentionalWalkPrefix']['baselineCommit']+':Baseball/'+record['contextPath']])
        self.assertEqual(hashlib.sha256(prior).hexdigest(),bridge['previousContextSha256'])
        self.assertEqual(hashlib.sha256(current).hexdigest(),bridge['currentContextSha256'])
        before,after=ast.parse(prior),ast.parse(current)
        old=next(n for n in before.body if getattr(n,'name',None)=='personal_runner_histories')
        changed=next(n for n in after.body if getattr(n,'name',None)=='personal_runner_histories')
        call=ast.dump(ast.parse('isolate_zero_episode_histories(result)').body[0])
        self.assertEqual(sum(ast.dump(n)==call for n in changed.body),1)
        changed.body=[n for n in changed.body if ast.dump(n)!=call]
        changed.body[0]=copy.deepcopy(old.body[0])  # docstring, not executable behavior
        after.body=[n for n in after.body if getattr(n,'name',None)!='isolate_zero_episode_histories']
        self.assertEqual(ast.dump(before),ast.dump(after))
        for family,entry in bridge['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'q7_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),current_implementation(family,entry))
            reuse=E.code_equivalence(family,entry['previousImplementationSha256'],entry['currentImplementationSha256'],
                _context=bridge['currentContextSha256'])
            self.assertEqual(reuse['kind'],'prior-stricter-history-selection' if family=='runner-boundary' else 'unchanged-proof-dependencies')
            self.assertIsNotNone(E.code_equivalence(family,entry['previousImplementationSha256'],adapter.fingerprint()))
            if family in record['families']:
                old_entry=record['families'][family]
                self.assertIsNotNone(E.code_equivalence(family,old_entry['previousImplementationSha256'],adapter.fingerprint()))

    def test_equivalent_code_reuses_exact_proof_without_changing_its_outcome_or_fingerprint(self):
        record=E.read(E.COMPATIBILITY_PATH)
        # Exercise this historical equivalence at its exact context revision.
        # New selections must not make historical negative proofs current.
        original_sha=E.sha
        context=patch.object(E,'sha',side_effect=lambda p:record['currentContextSha256']
            if Path(p)==ROOT/record['contextPath'] else original_sha(p))
        context.start();self.addCleanup(context.stop)
        for family,status in [('runner-resolution','admitted'),('pitch-count','withheld'),('defensive','withheld')]:
            with self.subTest(family=family),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run'/f'{family}.json'
                entry=record['families'][family]
                proof=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,
                    status=status,gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',graph='graph',
                    implementationSha256=entry['previousImplementationSha256'],sourceReconciled=True,graphConforms=True,
                    issues=[] if status=='admitted' else [dict(code='ORIGINAL_WITHHELD_REASON')])
                for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                    E.atomic(path.with_suffix(suffix),dict(retained=key));proof[key]=E.sha(path.with_suffix(suffix))
                E.atomic(path,proof);original=path.read_bytes()
                marker=state/'promotion.json';field=E.FIELDS[family]
                E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                    promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
                adapter=SimpleNamespace(fingerprint=lambda:entry['currentImplementationSha256'],
                    promoted_admission=lambda *args:{'status':'withheld'})
                result=E.load(adapter,state,promotion,family)
                self.assertEqual({key:result[key] for key in proof},proof)
                self.assertEqual(path.read_bytes(),original)
                self.assertEqual(result['implementationReuse']['currentImplementationSha256'],adapter.fingerprint())
                self.assertEqual(E.diagnostic(state,promotion,family,adapter.fingerprint())['evidenceState'],'implementation-compatible')
                self.assertIsNone(E.compatible_proof(state,{**promotion,'rawSha256':'different'},family,adapter.fingerprint()))
                self.assertIsNone(E.compatible_proof(state,promotion,family,'unrecognized-next-version'))
                if family=='defensive':
                    invalid={**proof,'status':'admitted','populationComplete':False}
                    E.atomic(path,invalid);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                    invalid_promotion={**promotion,'promotionManifestSha256':E.sha(marker)}
                    with self.assertRaisesRegex(ValueError,'conformance evidence'):
                        E.load(adapter,state,invalid_promotion,family)
                    E.atomic(path,proof);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                path.with_suffix('.report.ttl').write_text('changed report')
                with self.assertRaisesRegex(ValueError,'artifact changed'):E.load(adapter,state,promotion,family)

    def test_independent_retained_resolution_census_keeps_its_source_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run/runner-resolution.json'
            source=dict(gamePk='1',game='https://baseballontology.org/data/game/1',
                sourceSha256='witness-input',status='reconciled',issues=[])
            proof=dict(artifactType='baseballo-runner-resolution-admission',contractVersion=1,
                gamePk='1',graph='graph',authoritativeRdfSha256='rdf',sourceSha256='witness-input',
                status='admitted',sourceReconciled=True,graphConforms=True,implementationSha256='previous')
            for suffix,key,data in (('.source.json','sourceCensusSha256',source),
                    ('.shapes.ttl','shapeSha256',{}),('.report.ttl','reportSha256',{})):
                E.atomic(path.with_suffix(suffix),data);proof[key]=E.sha(path.with_suffix(suffix))
            E.atomic(path,proof);marker=state/'promotion.json'
            E.atomic(marker,dict(runnerResolutionAdmission=str(path),runnerResolutionAdmissionSha256=E.sha(path)))
            promotion=dict(gamePk='1',authoritativeGraph='graph',authoritativeRdfSha256='rdf',
                rawSha256='ingestion-input',promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
            reuse=dict(kind='prior-stricter-history-selection')
            with patch.object(E,'code_equivalence',return_value=reuse):
                result=E.compatible_proof(state,promotion,'runner-resolution','current')
                self.assertEqual(result['sourceSha256'],'witness-input')
                self.assertEqual(result['implementationSha256'],'previous')
                self.assertEqual(result['implementationReuse']['promotionSourceSha256'],'ingestion-input')
                self.assertEqual(E.diagnostic(state,promotion,'runner-resolution','current')['evidenceState'],
                    'implementation-compatible')
                self.assertIsNone(E.compatible_proof(state,dict(promotion,authoritativeRdfSha256='changed'),
                    'runner-resolution','current'))
                for changes in (dict(status='withheld'),dict(sourceSha256='unbound-source')):
                    E.atomic(path,dict(proof,**changes))
                    E.atomic(marker,dict(runnerResolutionAdmission=str(path),runnerResolutionAdmissionSha256=E.sha(path)))
                    altered=dict(promotion,promotionManifestSha256=E.sha(marker))
                    self.assertIsNone(E.compatible_proof(state,altered,'runner-resolution','current'))
            with patch.object(E,'code_equivalence',return_value=None):
                self.assertIsNone(E.compatible_proof(state,altered,'runner-resolution','unknown'))

    def test_stale_previously_withheld_is_preserved_and_never_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run/defensive.json'
            proof=dict(status='withheld',gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',
                implementationSha256='old',issues=[dict(code='INCOMPLETE_DEFENSIVE_POPULATION')])
            E.atomic(path,proof)
            marker=state/'promotion.json';E.atomic(marker,dict(defensiveAdmission=str(path),defensiveAdmissionSha256=E.sha(path)))
            promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
            result=E.diagnostic(state,promotion,'defensive','current')
            self.assertEqual((result['evidenceState'],result['previousStatus']),('implementation-stale','withheld'))
            self.assertEqual(result['previousIssues'],proof['issues'])
            adapter=SimpleNamespace(fingerprint=lambda:'current',promoted_admission=lambda *args:{'status':'withheld'})
            self.assertEqual(E.load(adapter,state,promotion,'defensive'),{'status':'withheld'})
            # A separately produced current proof still must match the exact graph,
            # source, implementation, promotion and retained artifacts.
            target=E.refresh_path(state,promotion,'defensive','current')
            E.atomic(target,{**proof,'artifactType':'baseballo-defensive-admission','contractVersion':1,
                'graph':'graph','implementationSha256':'current'})
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            self.assertEqual(E.load(adapter,state,promotion,'defensive')['issues'],proof['issues'])
            changed=E.read(target);changed['sourceSha256']='another-input';E.atomic(target,changed)
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            with self.assertRaisesRegex(ValueError,'different inputs'):E.load(adapter,state,promotion,'defensive')


if __name__=='__main__':unittest.main()
