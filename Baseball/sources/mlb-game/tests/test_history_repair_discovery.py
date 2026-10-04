"""Bounded queue discovery reuses H3 and cannot silently replace a game."""
import copy
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_history_addition_recovery import H

D=H.DISCOVERY


class HistoryRepairDiscovery(unittest.TestCase):
    def test_named_legacy_gap_queues_only_existing_graph_evidence_without_inventing_census(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);_,_,manifest,promotion,witness=self.setup_case(state)
            H.atomic(manifest,{})
            marker=state/'pipeline/evidence/nifi/game-promotion/824087/marker.json'
            value=H.read(marker);value['rmlManifestSha256']=H.sha(manifest);H.atomic(marker,value)
            promotion['promotionManifestSha256']=H.sha(marker)
            contract=H.read(H.SELECTION);contract['legacyEvidenceGames']=['824087']
            api=SimpleNamespace(**vars(H));api.SELECTION=state/'selection.json';H.atomic(api.SELECTION,contract)
            with patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H.I,'validated_promotion_record',return_value=promotion), \
                    patch.object(D,'source',return_value=witness), \
                    patch.object(H.H.CONTEXT,'personal_runner_histories') as history, \
                    patch.object(H,'select_history') as select:
                self.assertEqual(D.discover(api,state,set()),'824087')
                case=D.cases(api,state)[0]
                self.assertTrue(case['legacyHistoryEvidence'])
                self.assertEqual(case['selectedHistoryKeys'],[])
                self.assertEqual(case['inputSha256'],promotion['rawSha256'])
                self.assertTrue(H.read(Path(case['repairRequest']))['legacyHistoryEvidence'])
                self.assertEqual(H.read(manifest),{})
                history.assert_not_called();select.assert_not_called()
                contract['legacyEvidenceGames']=[]
                record=D.inspect_record(api,state,marker,contract,{})
                self.assertEqual(record['status'],'retained-history-census-unavailable')

    def test_legacy_evidence_without_retained_source_never_acquires_api_input(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);request=state/'request.json'
            promotion=dict(gamePk='822864',promotionManifestSha256='promotion')
            H.atomic(request,dict(gamePk='822864',promotionManifestSha256='promotion',legacyHistoryEvidence=True))
            api=SimpleNamespace(**vars(H));api.module=lambda *a:SimpleNamespace(retained_raw_witness=lambda *a:None)
            with patch.object(D.urllib.request,'urlopen') as acquire:
                with self.assertRaisesRegex(FileNotFoundError,'no retained source witness'):
                    D.source(api,state,promotion,request)
                acquire.assert_not_called()

    def setUp(self):
        self.boundary_loader=D.boundary_admission
        version=D.fingerprint(SimpleNamespace(**vars(H)))
        fingerprint=patch.object(D,'fingerprint',return_value=version)
        fingerprint.start();self.addCleanup(fingerprint.stop)
        self.admission=patch.object(D,'boundary_admission',return_value=None)
        self.admission.start();self.addCleanup(self.admission.stop)

    def test_boundary_shortcut_requires_owning_admission_and_preserves_provenance(self):
        api=SimpleNamespace(**vars(H));marker=Path('promotions/42/marker.json')
        proof=dict(status='withheld',proofSha256='proof',implementationSha256='original')
        evidence=SimpleNamespace(module=lambda *a:None,load=lambda *a:proof)
        api.module=lambda *a:evidence
        with patch.object(H.I,'validated_promotion_record',return_value={}), \
                patch.object(H.I,'query_index_contract_admission',return_value={}):
            self.assertIsNone(self.boundary_loader(api,Path('state'),marker))
            proof.update(status='admitted',implementationReuse={'kind':'prior-stricter-history-selection'})
            admitted=self.boundary_loader(api,Path('state'),marker)
            self.assertEqual(admitted,{k:v for k,v in proof.items() if k!='status'})

    def test_complete_history_does_not_reacquire_for_unresolved_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);_,_,_,promotion,witness=self.setup_case(state)
            marker=state/'pipeline/evidence/nifi/game-promotion/824087/marker.json'
            admission=state/'runner-history-admission.json'
            promotion.update(authoritativeGraph='https://w3id.org/baseball/graph/game/824087',
                authoritativeRdfSha256='promoted-rdf')
            proof=dict(artifactType='baseballo-runner-history-admission',contractVersion=1,
                gamePk=promotion['gamePk'],graph=promotion['authoritativeGraph'],
                authoritativeRdfSha256=promotion['authoritativeRdfSha256'],
                sourceSha256=witness['sha256'],implementationSha256='retained-original-producer',
                status='admitted',sourceReconciled=True,graphConforms=True,populationComplete=True)
            for suffix,key in (('.source.json','sourceCensusSha256'),
                    ('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                artifact=admission.with_suffix(suffix);artifact.write_text('retained evidence')
                proof[key]=H.sha(artifact)
            H.atomic(admission,proof)
            value=dict(H.read(marker),rawSha256=witness['sha256'],runnerHistoryAdmission=str(admission),
                runnerHistoryAdmissionSha256=H.sha(admission))
            H.atomic(marker,value)
            prior_bytes=admission.read_bytes();api=SimpleNamespace(**vars(H))
            with patch.object(H.I,'validated_promotion_record',return_value=promotion), \
                    patch.object(D,'boundary_admission') as boundary,patch.object(D,'source') as source:
                record=D.inspect_record(api,state,marker,H.read(H.SELECTION),{})
                self.assertEqual(record['reason'],'existing-complete-history')
                self.assertEqual(record['retainedHistoryAdmission']['implementationSha256'],
                    'retained-original-producer')
                self.assertNotIn('boundaryAdmission',record)
                previous=dict(status='selected',case={'gamePk':'824087','repairRequestSha256':'original'})
                resumed=D.inspect_record(api,state,marker,H.read(H.SELECTION),previous)
                self.assertEqual(resumed['status'],'selected');self.assertEqual(resumed['case'],previous['case'])
                source.assert_not_called();boundary.assert_not_called()
                self.assertEqual(admission.read_bytes(),prior_bytes)
                for change,message in (({'authoritativeRdfSha256':'other'},'another graph'),
                        ({'sourceSha256':'unbound'},'unbound source'),
                        ({'reportSha256':'changed'},'artifact changed')):
                    with self.subTest(change=change):
                        H.atomic(admission,{**proof,**change});value['runnerHistoryAdmissionSha256']=H.sha(admission)
                        with self.assertRaisesRegex(ValueError,message):
                            D.retained_history_admission(api,state,marker,value)
                H.atomic(admission,proof)
                with self.assertRaisesRegex(ValueError,'admission changed'):
                    D.retained_history_admission(api,state,marker,value)
                for change in ({'status':'withheld'},{'populationComplete':False},
                        {'graphConforms':False},{'sourceReconciled':False}):
                    with self.subTest(change=change):
                        H.atomic(admission,{**proof,**change});value['runnerHistoryAdmissionSha256']=H.sha(admission)
                        self.assertIsNone(D.retained_history_admission(api,state,marker,value))

    def test_admitted_boundaries_skip_source_and_missing_legacy_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);_,_,manifest,_,_=self.setup_case(state)
            marker=state/'pipeline/evidence/nifi/game-promotion/824087/marker.json'
            proof=dict(proofSha256='retained-proof',implementationSha256='original-producer')
            manifest.unlink()
            with patch.object(D,'boundary_admission',return_value=proof),patch.object(D,'source') as source:
                record=D.inspect_record(SimpleNamespace(**vars(H)),state,marker,H.read(H.SELECTION),{})
            self.assertEqual(record['status'],'not-applicable')
            self.assertEqual(record['boundaryAdmission'],proof)
            self.assertEqual(record['reason'],'existing-boundary-admission')
            source.assert_not_called()
            self.assertFalse(D.inventory_path(state).parent.joinpath('824087').exists())
            previous=dict(status='selected',case={'gamePk':'824087','repairRequestSha256':'original'})
            with patch.object(D,'boundary_admission',return_value=proof):
                resumed=D.inspect_record(SimpleNamespace(**vars(H)),state,marker,H.read(H.SELECTION),previous)
            self.assertEqual(resumed['status'],'selected')
            self.assertEqual(resumed['case'],previous['case'])

    def test_metadata_inspection_advances_without_source_work_and_prioritizes_unseen(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);_,_,manifest,promotion,_=self.setup_case(state)
            first=state/'pipeline/evidence/nifi/game-promotion/824087/marker.json'
            second=first.parent.parent/'824088/marker.json'
            H.atomic(second,dict(H.read(first),gamePk='824088'))
            H.atomic(D.inventory_path(state),dict(games={'824087':dict(status='selected',identity=['old','worker'])}))
            api=SimpleNamespace(**vars(H))
            with patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(D,'source') as source,patch.object(H,'select_history') as select:
                # The fingerprint follows the real selector; source preparation
                # is the separate operation that must not run during inspection.
                with patch.object(D,'fingerprint',return_value='inspection'):
                    result=D.inspect_promotions(api,state,set(),limit=1)
                self.assertEqual(result['inspectedGames'],1)
                rows=D.inventory(api,state)['games']
                self.assertEqual(rows['824087']['identity'],['old','worker'])
                self.assertEqual(rows['824088']['status'],'awaiting-source')
                self.assertTrue(Path(rows['824088']['repairRequest']).is_file())
                source.assert_not_called();select.assert_not_called()

    def test_worker_and_diagnostic_changes_do_not_reacquire_completed_request(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);_,_,manifest,promotion,witness=self.setup_case(state)
            api=SimpleNamespace(**vars(H));before=D.fingerprint(api)
            api.fingerprint=lambda:'different-execution-worker'
            with patch.object(D,'conflict_details',side_effect=AssertionError('not selection')):
                self.assertEqual(D.fingerprint(api),before)
            with patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H.I,'validated_promotion_record',return_value=promotion), \
                    patch.object(D,'source',return_value=witness) as source:
                D.discover(api,state,set());case=D.cases(api,state)[0]
                Path(witness['path']).unlink()  # Successful source retirement.
                inventory=D.inventory(api,state)
                inventory['games']['824087']['identity'][1]='previous-inspection'
                H.atomic(D.inventory_path(state),inventory)
                self.assertIsNone(D.discover(api,state,set()))
                self.assertEqual(D.cases(api,state)[0],case)
                source.assert_called_once()

    def test_new_selector_has_its_own_request_and_reuses_original_acquisition(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);raw,removed,manifest,promotion,_=self.setup_case(state)
            api=SimpleNamespace(**vars(H));pk=promotion['gamePk'];digest=promotion['promotionManifestSha256']
            original=H.read(manifest)['runnerHistoryReconciliation']
            request=dict(gamePk=pk,promotionManifestSha256=digest,rmlManifestSha256=H.sha(manifest),
                contextBuilderSha256='previous-approved-selector',scopeDecision=D.SCOPE,
                historyFailures=[dict(inning=r['inning'],half=r['half'],issues=r['issues'])
                    for r in original['withheldHistories']],boundaryIssues=original.get('boundaryIssues',[]))
            legacy=D.inventory_path(state).parent/pk/(digest+'.json');H.atomic(legacy,request)
            source=state/'pipeline/quarantine/mlb-game'/pk/('targeted-history-'+digest[:16])/'input.json'
            source.parent.mkdir(parents=True);source.write_bytes(raw)
            witness=dict(gamePk=pk,path=str(source),sha256=H.sha(source),kind='retained-response-copy',
                acquisitionRequest=str(legacy),acquisitionRequestSha256=H.sha(legacy))
            receipt=source.with_name('acquisition.json');H.atomic(receipt,witness)
            H.atomic(D.inventory_path(state),dict(games={pk:dict(status='failed',identity=[digest,'old-worker'],
                error='Recorded history repair request changed')}))
            prior_request=legacy.read_bytes();prior_receipt=receipt.read_bytes()
            with patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H.I,'validated_promotion_record',return_value=promotion), \
                    patch.object(D.urllib.request,'urlopen') as fetch:
                self.assertEqual(D.discover(api,state,set()),pk)
                case=D.cases(api,state)[0];current=Path(case['repairRequest'])
                self.assertNotEqual(current,legacy)
                self.assertEqual(H.read(current)['contextBuilderSha256'],H.read(H.SELECTION)['contextBuilderSha256'])
                self.assertEqual(case['sourceWitness'],witness)
                self.assertEqual(H.acquire_selection_source(state,case),witness)
                self.assertEqual(case['selectedHistoryKeys'],[removed['lifetimeKey']])
                self.assertEqual(legacy.read_bytes(),prior_request)
                self.assertEqual(receipt.read_bytes(),prior_receipt)
                self.assertEqual(source.read_bytes(),raw)
                fetch.assert_not_called()
                changed=H.read(current);changed['boundaryIssues']=[dict(code='different-scope')]
                H.atomic(current,changed)
                with self.assertRaisesRegex(ValueError,'different repair scope'):
                    D.source(api,state,promotion,current)
                # A modified original request cannot be used as acquisition evidence.
                H.atomic(legacy,dict(request,scopeDecision='changed'))
                with self.assertRaisesRegex(ValueError,'acquisition receipt'):
                    D.source(api,state,promotion,current)

    def test_one_named_request_precedes_acquisition_and_receipt_recovers_without_refetch(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);api=SimpleNamespace(**vars(H))
            promotion=dict(gamePk='42',promotionManifestSha256='a'*64)
            request=D.inventory_path(state).parent/'42/request.json'
            H.atomic(request,promotion)
            calls=[]
            def fetch(req,**kwargs):
                self.assertEqual(H.read(request)['gamePk'],'42')
                calls.append(req.full_url)
                return io.BytesIO(b'{"gamePk":42}')
            original=api.atomic
            def interrupted(path,value):
                if path.name=='acquisition.json':raise RuntimeError('receipt interrupted')
                original(path,value)
            api.module=lambda *a:SimpleNamespace(retained_raw_witness=lambda *a:None)
            with patch.object(D.urllib.request,'urlopen',side_effect=fetch):
                api.atomic=interrupted
                with self.assertRaisesRegex(RuntimeError,'receipt interrupted'):D.source(api,state,promotion,request)
                api.atomic=original
                witness=D.source(api,state,promotion,request)
                self.assertEqual(D.source(api,state,promotion,request),witness)
            self.assertEqual(calls,['https://statsapi.mlb.com/api/v1.1/game/42/feed/live'])
            self.assertEqual(witness['kind'],'targeted-reacquisition')
            self.assertEqual(witness['acquisitionRequestSha256'],H.sha(request))

    def setup_case(self,state):
        raw=(H.ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        current=H.H.CONTEXT.personal_runner_histories(raw)
        old=copy.deepcopy(current);removed=old['histories'].pop()
        old['episodeMembership']=[e for e in old['episodeMembership'] if e['lifetimeKey']!=removed['lifetimeKey']]
        old['withheldHistories']=[dict(inning=int(removed['inning']),half=removed['half'],issues=[dict(code='UNRESOLVED_REVIEW_EFFECT')])]
        source=state/'pipeline/quarantine/mlb-game/824087/targeted-history-fixture/input.json'
        source.parent.mkdir(parents=True);source.write_bytes(raw)
        manifest=state/'manifest.json';H.atomic(manifest,dict(runnerHistoryReconciliation=old))
        marker=state/'pipeline/evidence/nifi/game-promotion/824087/marker.json'
        H.atomic(marker,dict(gamePk='824087',promotedAtUtc='now',rmlManifest=str(manifest),rmlManifestSha256=H.sha(manifest)))
        promotion=dict(gamePk='824087',promotionManifestSha256=H.sha(marker),rawSha256=current['inputSha256'])
        witness=dict(gamePk='824087',kind='retained-response-copy',path=str(source),sha256=H.sha(source))
        return raw,removed,manifest,promotion,witness

    def test_discovery_records_exact_missing_selection_and_preserves_prior_histories(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);raw,removed,manifest,promotion,witness=self.setup_case(state)
            api=SimpleNamespace(**vars(H))
            with patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H.I,'validated_promotion_record',return_value=promotion), \
                    patch.object(D,'source',return_value=witness) as source:
                self.assertEqual(D.discover(api,state,set()),'824087')
                case=D.cases(api,state)[0]
                self.assertTrue(Path(case['repairRequest']).is_file())
                self.assertEqual(case['selectedHistoryKeys'],[removed['lifetimeKey']])
                history,delta=H.select_history(H.read(manifest),case,raw)
                self.assertEqual(delta['histories'],[removed])
                self.assertEqual(len(history['histories']),len(H.read(manifest)['runnerHistoryReconciliation']['histories'])+1)
                self.assertEqual(H.acquire_selection_source(state,case),witness)
                self.assertIsNone(D.discover(api,state,set()))
                source.assert_called_once()
                Path(witness['path']).write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError,'recorded scope'):H.acquire_selection_source(state,case)

    def test_identity_conflict_gets_one_distinct_recovery_attempt_then_stays_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);raw,removed,manifest,promotion,witness=self.setup_case(state)
            broken=H.read(manifest);broken['runnerHistoryReconciliation']['histories'][0]['terminationAnchor']='conflict'
            H.atomic(manifest,broken)
            marker=state/'pipeline/evidence/nifi/game-promotion/824087/marker.json'
            record=H.read(marker);record['rmlManifestSha256']=H.sha(manifest);H.atomic(marker,record)
            promotion['promotionManifestSha256']=H.sha(marker)
            api=SimpleNamespace(**vars(H))
            with patch.object(H.I,'retained_artifact',return_value=manifest), \
                    patch.object(H.I,'validated_promotion_record',return_value=promotion), \
                    patch.object(D,'source',return_value=witness) as source:
                self.assertIsNone(D.discover(api,state,set()))
                self.assertEqual(D.cases(api,state),[])
                failure=D.inventory(api,state)['games']['824087']
                self.assertEqual(failure['status'],'failed')
                self.assertIn('identity no longer aligns',failure['error'])
                self.assertEqual(failure['sourceWitness'],witness)
                self.assertEqual(failure['diagnostics']['changedHistories'][0]['previous']['terminationAnchor'],'conflict')
                self.assertNotEqual(failure['diagnostics']['changedHistories'][0]['current']['terminationAnchor'],'conflict')
                self.assertTrue(Path(failure['repairRequest']).is_file())
                self.assertIsNone(D.discover(api,state,set()))
                recovery=D.inventory(api,state)['games']['824087']
                self.assertEqual(recovery['sourceRecovery']['conflictedWitness'],witness)
                self.assertNotEqual(recovery['repairRequest'],failure['repairRequest'])
                self.assertEqual(H.read(Path(recovery['repairRequest']))['recoverRetainedSourceSha256'],witness['sha256'])
                self.assertIsNone(D.discover(api,state,set()))
                self.assertEqual(source.call_count,2)
            self.assertEqual(Path(witness['path']).read_bytes(),raw)

    def test_recovery_fetch_preserves_conflicted_source_and_recovers_its_own_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);api=SimpleNamespace(**vars(H))
            promotion=dict(gamePk='42',promotionManifestSha256='a'*64)
            request=D.inventory_path(state).parent/'42/recovery.json'
            H.atomic(request,dict(promotion,recoverRetainedSourceSha256='b'*64))
            old=state/'pipeline/quarantine/mlb-game/42'/('targeted-history-'+'a'*16)/'input.json'
            old.parent.mkdir(parents=True);old.write_bytes(b'conflicted original bytes')
            api.module=lambda *a:SimpleNamespace(retained_raw_witness=lambda *a:self.fail('must not recopy the conflict'))
            with patch.object(D.urllib.request,'urlopen',return_value=io.BytesIO(b'{"gamePk":42}')) as fetch:
                witness=D.source(api,state,promotion,request)
                self.assertEqual(D.source(api,state,promotion,request),witness)
                fetch.assert_called_once()
            self.assertEqual(witness['kind'],'targeted-reacquisition')
            self.assertNotEqual(Path(witness['path']),old)
            self.assertEqual(old.read_bytes(),b'conflicted original bytes')

    def test_conflict_evidence_reports_the_actual_base_disagreement_without_repairing_it(self):
        raw=H.json.dumps(dict(liveData=dict(plays=dict(allPlays=[dict(atBatIndex=53,
            result=dict(description='Runner to second'),matchup=dict(postOnSecond=dict(id=1)),
            runners=[dict(movement=dict(end='1B'))])])))).encode()
        old=dict(inputSha256='original',histories=[dict(lifetimeKey='prior',runnerId='1')])
        current=dict(inputSha256='different',histories=[],withheldHistories=[dict(inning=6,half='bottom',
            issues=[dict(code='POST_BASE_RECONCILIATION_FAILED',atBatIndex=53),
                    dict(code='UNSUPPORTED_HALF_TERMINATION',atBatIndex=None)])])
        details=D.conflict_details(SimpleNamespace(**vars(H)),raw,old,current)
        self.assertEqual(details['priorInputSha256'],'original')
        self.assertEqual(details['currentInputSha256'],'different')
        self.assertIsNone(details['changedHistories'][0]['current'])
        play=details['sourcePlays'][0]
        self.assertEqual(play['runners'][0]['movement']['end'],'1B')
        self.assertEqual(play['postBases']['postOnSecond']['id'],1)
        self.assertEqual(current['histories'],[])


if __name__=='__main__':unittest.main()
