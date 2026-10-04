"""Repair scope, dependency slicing and crash-safe input retirement."""
import importlib.util
import tempfile
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from rdflib import Graph,RDF,URIRef
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('history_repair',ROOT/'sources/mlb-game/pipeline/targeted-history-addition.py')
H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)

class HistoryAdditionRecovery(unittest.TestCase):
    def test_unrelated_existing_source_rejection_stays_withheld_without_blocking_history(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);prior=state/'prior.json';evidence=state/'repair';evidence.mkdir()
            old=dict(status='withheld',sourceReconciled=False,graphConforms=False,
                authoritativeRdfSha256='base',sourceSha256='source',
                issues=[dict(code='UNRESOLVED_RUNNER_BOUNDARY',atBatIndex='4',runnerIndex=0)])
            H.atomic(prior,old)
            marker=dict(gamePk='1',rawSha256='source',runnerResolutionAdmission=str(prior),
                runnerResolutionAdmissionSha256=H.sha(prior))
            history_proof=dict(status='withheld',sourceReconciled=True,graphConforms=True,sourceSha256='source')
            current=dict(old);selected=[dict(episodes=[dict(atBatIndex='12',runnerIndex=0)])]
            def prove(value):
                def run(**kwargs):H.atomic(kwargs['output'],value);return dict(value)
                return run
            session=SimpleNamespace(validate_with_jena=lambda **kwargs:(True,Graph(),None))
            from contextlib import nullcontext
            with patch.object(H.J,'Session',return_value=nullcontext(session)), \
                    patch.object(H.H,'prove',side_effect=prove(history_proof)), \
                    patch.object(H,'module',return_value=SimpleNamespace(prove=prove(current))):
                fields=H.revalidate(marker,dict(outputSha256='base'),{},state/'graph.ttl',
                    evidence,None,None,source_raw=b'source',selected_histories=selected)
                saved=H.read(Path(fields['runnerResolutionAdmission']))
                self.assertEqual(saved['status'],'withheld')
                self.assertFalse(saved['sourceReconciled']);self.assertFalse(saved['graphConforms'])
                self.assertEqual(saved['issues'],old['issues'])
                self.assertEqual(saved['partialRepairIsolation']['originalProofSha256'],H.sha(prior))
                self.assertEqual(saved['partialRepairIsolation']['selectedPlateAppearances'],['12'])
                for faults in ([dict(code='UNRESOLVED_RUNNER_BOUNDARY',atBatIndex='12',runnerIndex=0)],
                               [dict(code='SOURCE_RECONCILIATION')],
                               [dict(code='NEW_SOURCE_ISSUE',atBatIndex='4')]):
                    current['issues']=faults
                    with self.assertRaisesRegex(ValueError,'runnerResolutionAdmission'):
                        H.revalidate(marker,dict(outputSha256='base'),{},state/'graph.ttl',
                            evidence,None,None,source_raw=b'source',selected_histories=selected)
                current.update(old,sourceReconciled=True)
                with self.assertRaisesRegex(ValueError,'runnerResolutionAdmission'):
                    H.revalidate(marker,dict(outputSha256='base'),{},state/'graph.ttl',
                        evidence,None,None,source_raw=b'source',selected_histories=selected)

    def test_new_request_with_same_history_keys_requires_its_own_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);case=dict(gamePk='1',selectionRepair='H3',discovered=True,selectedHistoryKeys=[],
                repairRequest='request.json',repairRequestSha256='new-request',sourceSha256='source')
            control=state/'pipeline/control/mlb-game/history-addition/1.json'
            H.atomic(control,dict(status='evidence-refreshed',selectedHistoryKeys=[],implementationSha256='worker',
                repairRequestSha256='old-request',sourceSha256='source',attempts=2))
            with patch.object(H,'cases',return_value=[case]),patch.object(H,'fingerprint',return_value='worker'), \
                    patch.object(H.DISCOVERY,'discover',return_value=None), \
                    patch.object(H,'add_game',return_value=dict(status='evidence-refreshed',selectedHistoryKeys=[])) as add:
                self.assertEqual(H.next_case(state),'1')
                result=H.tick(state,'1',None,None,None)
                self.assertEqual(result['attempts'],1);self.assertEqual(result['repairRequestSha256'],'new-request')
                self.assertIsNone(H.next_case(state));H.tick(state,'1',None,None,None);add.assert_called_once()
                case['sourceSha256']='different-source'
                self.assertEqual(H.next_case(state),'1')

    def test_memory_deferrals_do_not_exhaust_retries_or_starve_other_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);cases=[dict(gamePk='1'),dict(gamePk='2')]
            def execute(state,pk,*args):
                return dict(status='waiting-for-memory' if pk=='1' else 'complete')
            with patch.object(H,'cases',return_value=cases),patch.object(H,'fingerprint',return_value='worker'), \
                    patch.object(H.DISCOVERY,'discover',return_value=None),patch.object(H,'add_game',side_effect=execute) as add:
                summary=H.drain(state,None,None,None)
                self.assertEqual(summary['outcomes'],{'complete':1,'waiting-for-memory':1})
                self.assertEqual(H.read(state/'pipeline/control/mlb-game/history-addition/1.json')['attempts'],0)
                self.assertEqual(add.call_count,2)
                H.drain(state,None,None,None)
                self.assertEqual(add.call_count,3)

    def test_python_drain_lock_excludes_the_existing_powershell_game_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/work/mlb-game-locks/1.lock'
            script=state/'lock.ps1'
            script.write_text('''param($Helper,$State)
$ErrorActionPreference='Stop'
. $Helper
try {$handle=Enter-MlbGameLock -StateRoot $State -GamePk '1' -TimeoutSeconds 1}
catch {if ($_.Exception.Message -like 'Timed out waiting*') {exit 0}; throw}
$handle.Dispose();throw 'Game lock overlapped the Python writer'
''',encoding='utf-8')
            with H.LOCK.exclusive(path):
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(script),str(H.HERE/'game-lock.ps1'),str(state)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_heavy_history_execution_keeps_full_memory_reserve(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'pipeline/evidence/nifi/game-promotion/1/prior.json'
            H.atomic(marker,dict(promotedAtUtc='now'))
            with patch.object(H,'cases',return_value=[dict(gamePk='1')]), \
                    patch.object(H.TX,'HttpGraphStore'),patch.object(H.TX,'recover'), \
                    patch.object(H.I,'validated_promotion_record',return_value={}), \
                    patch.object(H.I,'query_index_contract_admission',return_value={}), \
                    patch.object(H.MEMORY,'available_memory',return_value=512*1024**2), \
                    patch.object(H,'command') as command:
                result=H.add_game(state,'1',None,None,None)
                self.assertEqual(result['status'],'waiting-for-memory');command.assert_not_called()

    def test_legacy_evidence_refresh_keeps_withheld_result_and_never_maps_or_promotes(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'pipeline/evidence/nifi/game-promotion/1/prior.json'
            manifest=state/'mapping.json';H.atomic(manifest,{})
            H.atomic(marker,dict(gamePk='1',promotedAtUtc='now',rmlManifest=str(manifest),rmlManifestSha256=H.sha(manifest)))
            source=state/'input.json';source.write_bytes(b'original bytes')
            case=dict(gamePk='1',discovered=True,selectionRepair='H3',selectedHistoryKeys=[],legacyHistoryEvidence=True)
            witness=dict(path=str(source),sha256=H.sha(source))
            proof=dict(status='withheld',issues=[dict(code='SOURCE_GRAPH_CONFORMANCE')],proofSha256='proof')
            admission=SimpleNamespace(existing_graph_refresh_needed=lambda *a:True,
                refresh_existing_graph=lambda *a:[],module=lambda *a:None,load=lambda *a:proof)
            with patch.object(H,'cases',return_value=[case]),patch.object(H,'module',return_value=admission), \
                    patch.object(H.TX,'HttpGraphStore'),patch.object(H.TX,'recover'), \
                    patch.object(H.I,'validated_promotion_record',return_value={}), \
                    patch.object(H.I,'query_index_contract_admission',return_value={}), \
                    patch.object(H.I,'retain_game_artifacts'),patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H.MEMORY,'available_memory',return_value=2*1024**3), \
                    patch.object(H,'acquire_selection_source',return_value=witness), \
                    patch.object(H,'command') as mapping,patch.object(H.TX,'prepare') as promotion, \
                    patch.object(H.EVENT,'emit'):
                result=H.add_game(state,'1',None,None,None)
            self.assertEqual(result['historyEvidence'],proof)
            self.assertEqual(result['status'],'evidence-refreshed');self.assertFalse(result['rdfChanged'])
            self.assertEqual(source.read_bytes(),b'original bytes');self.assertEqual(H.read(manifest),{})
            mapping.assert_not_called();promotion.assert_not_called()

    def test_named_selection_survives_a_later_manifest_without_expanding_its_scope(self):
        raw=b'current response';digest=H.hashlib.sha256(raw).hexdigest()
        rows=[dict(lifetimeKey=key,inning=1,half='top') for key in ('selected','unrelated')]
        history=dict(inputSha256=digest,sourceConsistency='consistent',histories=rows,
            episodeMembership=[],placementAdjudications=[])
        case=dict(gamePk='1',selectionRepair='H3',inputSha256='original-response',sourceSha256=digest,
            selectedHistoryKeys=['selected'],halves=[dict(inning=1,half='top')])
        with patch.object(H.H.CONTEXT,'personal_runner_histories',return_value=history):
            _,delta=H.select_history(dict(runnerHistoryReconciliation=history),case,raw)
            self.assertEqual([r['lifetimeKey'] for r in delta['histories']],['selected'])
            with self.assertRaisesRegex(ValueError,'inventoried histories'):
                H.select_history(dict(runnerHistoryReconciliation=history),dict(case,selectedHistoryKeys=['missing']),raw)
            with self.assertRaisesRegex(ValueError,'half-inning scope'):
                H.select_history(dict(runnerHistoryReconciliation=history),dict(case,halves=[dict(inning=2,half='top')]),raw)
            with self.assertRaisesRegex(ValueError,'another or inconsistent input'):
                H.select_history(dict(runnerHistoryReconciliation=dict(history,inputSha256='unrelated')),case,raw)

    def test_completion_receipt_does_not_skip_promotion_validation_or_retire_input(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'pipeline/evidence/nifi/game-promotion/1/prior.json'
            H.atomic(marker,dict(promotedAtUtc='2026-10-01',targetedAddition=dict(decision=H.DECISION)))
            with patch.object(H,'cases',return_value=[dict(gamePk='1')]), \
                    patch.object(H.TX,'HttpGraphStore'),patch.object(H.TX,'recover'), \
                    patch.object(H.I,'validated_promotion_record',side_effect=ValueError('invalid promotion')), \
                    patch.object(H.I,'query_index_contract_admission',return_value={}), \
                    patch.object(H,'finish_selection') as finish:
                with self.assertRaisesRegex(ValueError,'invalid promotion'):
                    H.add_game(state,'1',None,None,None)
                finish.assert_not_called()

    def test_existing_named_history_is_an_idempotent_completion_but_empty_rml_is_not(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'pipeline/evidence/nifi/game-promotion/1/prior.json'
            manifest=state/'mapping.json';H.atomic(manifest,dict(mappingBaseIri='urn:mapping',outputPath=str(state/'retired.ttl'),outputSha256='old'))
            H.atomic(marker,dict(gamePk='1',promotedAtUtc='2026-10-01',authoritativeGraph='urn:game',
                authoritativeTripleCount=1,rmlManifest=str(manifest),rmlManifestSha256=H.sha(manifest),
                targetedAddition=dict(decision='another-additive-repair')))
            case=dict(gamePk='1',selectedHistoryKeys=['selected'],promotionManifestSha256='older')
            history=dict(histories=[dict(lifetimeKey='selected')],placementAdjudications=[])
            base=Graph().parse(data='<urn:one> <urn:p> <urn:o> .',format='turtle');outputs=[Graph(),base]
            def render(args,*unused):outputs[0].serialize(destination=args[args.index('-o')+1],format='turtle')
            with patch.object(H,'cases',return_value=[case]),patch.object(H.TX,'HttpGraphStore') as store, \
                    patch.object(H.TX,'recover'),patch.object(H.I,'validated_promotion_record',return_value={}), \
                    patch.object(H.I,'query_index_contract_admission',return_value={}), \
                    patch.object(H.I,'retain_game_artifacts'),patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H,'select_history',return_value=(history,history)),patch.object(H,'subset_mapping'), \
                    patch.object(H,'command',side_effect=render),patch.object(H.V,'verify'), \
                    patch.object(H.TX,'prepare') as prepare,patch.object(H.EVENT,'emit') as emit, \
                    patch.object(H.MEMORY,'available_memory',return_value=2*1024**3):
                store.return_value.get.return_value=base.serialize(format='nt',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'produced no triples'):
                    H.add_game(state,'1',None,None,None)
                emit.assert_not_called()
                outputs.pop(0)
                result=H.add_game(state,'1',None,None,None)
                self.assertEqual(result['status'],'already-present')
                self.assertFalse(result['rdfChanged']);self.assertEqual(result['addedTriples'],0)
                self.assertEqual(result['selectedHistoryKeys'],['selected'])
                self.assertIn(result['status'],H.SUCCESS);prepare.assert_not_called();emit.assert_called_once()

    def test_old_game_completion_does_not_skip_a_different_history_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);case=dict(gamePk='1',selectionRepair='H3',selectedHistoryKeys=['new-history'])
            control=state/'pipeline/control/mlb-game/history-addition/1.json'
            H.atomic(control,dict(status='complete',selectedHistoryKeys=['old-history']))
            with patch.object(H,'cases',return_value=[case]),patch.object(H,'fingerprint',return_value='current'), \
                    patch.object(H,'add_game',return_value=dict(status='complete',selectedHistoryKeys=['new-history'])) as add:
                self.assertEqual(H.next_case(state),'1')
                self.assertEqual(H.tick(state,'1',None,None,None)['status'],'complete')
                add.assert_called_once()
                self.assertIsNone(H.next_case(state))
                H.tick(state,'1',None,None,None);add.assert_called_once()

    def test_only_existing_placement_and_game_end_dependencies_are_sliced(self):
        delta=dict(histories=[dict(gameEndInstantIri='urn:end')],placementAdjudications=[{}])
        names=H.history_maps(delta)
        with tempfile.TemporaryDirectory() as temp:
            mapping=Path(temp)/'delta.ttl';H.subset_mapping('1',mapping,names)
            graph=Graph().parse(mapping)
            self.assertEqual({str(s).rsplit('#',1)[1] for s in graph.subjects(RDF.type,
                URIRef('http://www.w3.org/ns/r2rml#TriplesMap'))},set(names))
        self.assertEqual(len(names),11)
        self.assertEqual(H.history_maps(dict(histories=[{}],placementAdjudications=[])),H.MAPS)

    def test_different_source_requires_explicit_original_binding(self):
        proof=dict(sourceSha256='new',sourceRevalidation=dict(
            decision='archive/design-records/metric-source-c1-operation-2026-09-14/review.json',
            mode='current-history-source-census',promotionSourceSha256='old',sourceSha256='new',originalProofSha256='prior'))
        H.retain_source_binding(proof,dict(rawSha256='old'),'runnerHistoryAdmission')
        self.assertEqual(proof['sourceSha256'],'new')
        with self.assertRaisesRegex(ValueError,'unbound source'):
            H.retain_source_binding(proof,dict(rawSha256='unrelated'),'runnerHistoryAdmission')

    def test_retirement_recovers_after_delete_without_readding_or_rechecking_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'pipeline/quarantine/mlb-game/1/targeted-h2/input.json'
            H.atomic(source,dict(gamePk=1));witness=dict(path=str(source),sha256=H.sha(source))
            marker=state/'promotion.json'
            H.atomic(marker,dict(pipelineRunId='run',targetedAddition=dict(sourceWitness=witness)))
            case=dict(gamePk='1',selectionRepair='H3')
            refresh=SimpleNamespace(refresh_existing_graph=lambda *a:None)
            original_atomic=H.atomic
            def interrupt_after_delete(path,value):
                if path.name=='cleanup.json' and value.get('rawRetiredAfterPromotion'):raise RuntimeError('interrupted after delete')
                original_atomic(path,value)
            with patch.object(H,'module',return_value=refresh) as module, \
                    patch.object(H.I,'validated_promotion_record',return_value={}), \
                    patch.object(H.I,'query_index_contract_admission',return_value={}), \
                    patch.object(H.EVENT,'emit') as emit:
                with patch.object(H,'atomic',side_effect=interrupt_after_delete):
                    with self.assertRaisesRegex(RuntimeError,'interrupted after delete'):
                        H.finish_selection(state,case,marker,None,None)
                self.assertFalse(source.exists());emit.assert_not_called()
                H.finish_selection(state,case,marker,None,None)
                self.assertEqual(module.call_count,1);emit.assert_called_once()
                receipt=H.read(state/'pipeline/evidence/mlb-game/1/run/cleanup.json')
                self.assertTrue(receipt['rawRetiredAfterPromotion'])

    def test_retirement_never_deletes_a_checked_in_witness(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'immutable.json';source.write_bytes(b'{}')
            marker=state/'promotion.json';H.atomic(marker,dict(targetedAddition=dict(
                sourceWitness=dict(path=str(source),sha256=H.sha(source)))))
            with self.assertRaisesRegex(ValueError,'escapes its owned input'):
                H.finish_selection(state,dict(gamePk='1'),marker,None,None)
            self.assertTrue(source.is_file())

if __name__=='__main__':unittest.main()
