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

    def test_identity_conflict_is_retained_and_not_reacquired_each_tick(self):
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
                self.assertIsNone(D.discover(api,state,set()))
                source.assert_called_once()
            self.assertEqual(Path(witness['path']).read_bytes(),raw)


if __name__=='__main__':unittest.main()
