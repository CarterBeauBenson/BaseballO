"""The repair runs five unchanged maps for exactly the failed foul pitches."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
from rdflib import Graph, RDF, URIRef

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('foul_addition',ROOT/'sources/mlb-game/pipeline/targeted-foul-addition.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools


class FoulAddition(unittest.TestCase):
    def test_new_selection_after_retirement_uses_its_own_input_and_preserves_old_receipts(self):
        import io
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);case=dict(gamePk='1',selected=[dict(atBatIndex='2',playId='new-bunt')])
            source=state/'pipeline/quarantine/mlb-game/1/targeted-foul/input.json'
            old=dict(kind='targeted-reacquisition',gamePk='1',path=str(source),sha256='old-source')
            manifest=source.with_name('acquisition.json');F.W.atomic(manifest,old)
            marker=state/'pipeline/evidence/nifi/game-promotion/1/old.json';F.W.atomic(marker,dict(gamePk='1'))
            receipt=source.with_name('retirement.json')
            F.W.atomic(receipt,dict(sourceSha256='old-source',promotionEvidence=str(marker),
                promotionManifestSha256=F.W.sha(marker),admissionOutcomes={},rawRetiredAfterPromotion=True))
            before=(manifest.read_bytes(),receipt.read_bytes())
            with patch.object(F.urllib.request,'urlopen',return_value=io.BytesIO(b'{"gamePk":1}')) as fetch:
                witness=F.acquire(state,case)
                self.assertEqual(F.acquire(state,case),witness)
                fetch.assert_called_once()
            self.assertEqual(Path(witness['path']).parent.name,'targeted-foul-'+F.case_sha(case)[:16])
            self.assertEqual((manifest.read_bytes(),receipt.read_bytes()),before)
            self.assertFalse(source.exists())
            self.assertIsNone(F.retirement_receipt(state,'1',witness))
            Path(witness['path']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'input changed'):F.acquire(state,case)
            F.W.atomic(receipt,dict(sourceSha256='wrong-source'))
            with self.assertRaisesRegex(ValueError,'receipt does not bind'):F.acquire(state,case)

    def test_completed_scope_survives_worker_changes_but_partial_scope_retries(self):
        case=dict(gamePk='1',selected=[dict(playId='foul')])
        old=dict(caseSha256=F.case_sha(case),implementationSha256='old',status='complete',attempts=1)
        self.assertTrue(F.finished_attempt(old,case,'new'))
        self.assertFalse(F.finished_attempt(dict(old,status='partial'),case,'new'))
        self.assertFalse(F.finished_attempt(old,dict(case,selected=[dict(playId='new-foul')]),'new'))

    def test_existing_second_foul_case_includes_reported_first_bunt_dependency_only_in_its_pa(self):
        import copy
        first,second,unrelated='first-bunt','second-foul','other-pa-bunt'
        def event(pid,call,strikes):
            return dict(kind='pitch',playId=pid,call=call,strike=True,strikesAfter=strikes)
        source=dict(status='reconciled',gamePk='823631',game='https://w3id.org/baseball/game/823631',
            plateAppearances=[dict(pa='https://w3id.org/baseball/game/823631/pa/79',
                events=[event(first,'L',1),event(second,'F',2)]),
                dict(pa='https://w3id.org/baseball/game/823631/pa/80',events=[event(unrelated,'L',1)])])
        document=dict(gameData=dict(venue=dict(id=1)),_baseballO=dict(metricMappingEvidence=dict(withheldFouls=[])),
            liveData=dict(plays=dict(allPlays=[dict(atBatIndex=int(pa['pa'].rsplit('/',1)[1]),
                playEvents=[dict(playId=e['playId'],_baseballO=dict(isSecondCountedFoul=e['call']=='F',
                    isCountedFoulBunt=e['call']=='L')) for e in pa['events']]) for pa in source['plateAppearances']])))
        def context(args,**kwargs):F.W.atomic(Path(args[-1]),document)
        raw=b'{"gamePk":823631}'
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);census=path/'source.json';F.W.atomic(census,source)
            report=path/'report.ttl'
            report.write_text('@prefix sh: <http://www.w3.org/ns/shacl#> .\n'+''.join(
                f'[] sh:sourceConstraintComponent sh:ClassConstraintComponent ; sh:focusNode <{source["game"]}/process/strike/{pid}> .\n'
                for pid in (first,second,unrelated)))
            case=dict(gamePk='823631',selected=[dict(atBatIndex='79',playId=second)],
                sourceCensus=str(census),sourceCensusSha256=F.W.sha(census),report=str(report),reportSha256=F.W.sha(report))
            with patch.object(F.C,'census',return_value=source),patch.object(F.subprocess,'run',side_effect=context):
                selected=F.select(raw,'823631',case)
            self.assertEqual([e['playId'] for e in selected['events']],[first,second])
            self.assertEqual(selected['source']['plateAppearances'],source['plateAppearances'][:1])
            changed=copy.deepcopy(source);changed['plateAppearances'][0]['events'][0]['strikesAfter']=2
            with patch.object(F.C,'census',return_value=changed):
                with self.assertRaisesRegex(ValueError,'outcome changed'):F.select(raw,'823631',case)
            report.write_text('changed evidence')
            with patch.object(F.C,'census',return_value=source):
                with self.assertRaisesRegex(ValueError,'report changed'):F.select(raw,'823631',case)

    def test_one_unsupported_pa_does_not_block_a_supported_pa_or_retire_its_input(self):
        raw=(ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        source=F.C.census(raw,'824087')
        selected=[]
        for pa in source['plateAppearances']:
            for event in pa['events']:
                if event.get('call')=='F' and event.get('strike') and event.get('strikesAfter')==2:
                    selected.append(dict(atBatIndex=pa['pa'].rsplit('/',1)[1],playId=event['playId']))
                    break
            if len(selected)==2:break
        bad=selected[1];good=selected[0]
        document=dict(gameData=dict(venue=dict(id=1)),_baseballO=dict(metricMappingEvidence=dict(
            withheldFouls=[dict(bad,reason='SUBSTITUTION_IN_PREFIX')])),liveData=dict(plays=dict(allPlays=[
                dict(atBatIndex=int(row['atBatIndex']),playEvents=[dict(playId=row['playId'],
                    _baseballO=dict(isSecondCountedFoul=row==good))]) for row in selected])))
        def context(args,**kwargs):F.W.atomic(Path(args[-1]),document)
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);census=state/'source.json';F.W.atomic(census,source)
            case=dict(gamePk='824087',selected=selected,sourceCensus=str(census),sourceCensusSha256=F.W.sha(census))
            with patch.object(F.subprocess,'run',side_effect=context):
                delta=F.select(raw,'824087',case)
            self.assertEqual([e['playId'] for e in delta['events']],[good['playId']])
            self.assertEqual([p['pa'].rsplit('/',1)[1] for p in delta['source']['plateAppearances']],[good['atBatIndex']])
            self.assertEqual(delta['unresolvedFouls'],[dict(bad,reason='SUBSTITUTION_IN_PREFIX')])
            witness=dict(kind='targeted-reacquisition',path=str(state/'input.json'))
            def add(*args,repair):
                repair['select'](raw,'824087');return dict(status='complete',addedTriples=14)
            with patch.object(F,'select',return_value=delta),patch.object(F,'acquire',return_value=witness), \
                    patch.object(F.W,'add_game',side_effect=add),patch.object(F,'finish',return_value={}) as finish:
                result=F.tick(state,case,None,None,None)
                self.assertEqual(result['status'],'partial')
                self.assertFalse(finish.call_args.kwargs['retire'])
                F.tick(state,case,None,None,None)
                finish.assert_called_once()

    def test_real_mapping_is_limited_to_recorded_missing_foul(self):
        raw=(ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        source=F.C.census(raw,'824087');pa=next(p for p in source['plateAppearances'] if p['pa'].endswith('/37'))
        event=next(e for e in pa['events'] if e.get('call')=='F' and e['strike'] and e['strikesAfter']==2)
        pid=event['playId'];strike=source['game']+'/process/strike/'+pid
        report=Graph().parse(data=f'''@prefix sh: <http://www.w3.org/ns/shacl#> .
            [] sh:sourceConstraintComponent sh:ClassConstraintComponent ; sh:focusNode <{strike}> .''',format='turtle')
        cases=F.recorded_fouls(source,report)
        self.assertEqual(cases,[dict(atBatIndex='37',playId=pid)])
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary);census=path/'source.json';F.W.atomic(census,source)
            case=dict(gamePk='824087',selected=cases,sourceCensus=str(census),sourceCensusSha256=F.W.sha(census))
            selected=F.select(raw,'824087',case)
            self.assertEqual([e['playId'] for e in selected['events']],[pid])
            context=path/'game-context.json';mapping=path/'addition.ttl'
            F.execution_inputs(raw,'824087',selected,context,mapping)
            maps=Graph().parse(mapping)
            self.assertEqual({str(m).rsplit('#',1)[1] for m in maps.subjects(RDF.type,
                URIRef('http://www.w3.org/ns/r2rml#TriplesMap'))},set(F.MAPS))
            java,mapper=installed_tools();output=path/'delta.ttl'
            run=subprocess.run([str(java),'-Xmx256m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=path,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
            graph=Graph().parse(output)
            self.assertEqual(len(graph),14)
            self.assertTrue(all(str(s).endswith('/'+pid) for s in graph.subjects()))
            self.assertIn((URIRef(strike),RDF.type,URIRef('https://baseballontology.org/StrikeProcess')),graph)
            changed=json.loads(raw);changed['liveData']['plays']['allPlays'][37]['playEvents'][3]['startTime']='2026-07-20T00:00:00Z'
            with self.assertRaisesRegex(ValueError,'source is unresolved|outcome changed'):
                F.select(json.dumps(changed).encode(),'824087',case)

    def test_other_pitch_clock_revision_preserves_promoted_census(self):
        raw=(ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        source=F.C.census(raw,'824087')
        pa=next(p for p in source['plateAppearances'] if p['pa'].endswith('/37'))
        foul=next(e for e in pa['events'] if e.get('call')=='F' and e['strike'] and e['strikesAfter']==2)
        other=next(e for e in pa['events'] if e['playId']!=foul['playId'])
        # The retained promoted census can have an earlier end for another
        # pitch; source selection adds only the unchanged, identified foul.
        from datetime import datetime,timedelta
        other['end']=(datetime.fromisoformat(other['end'].replace('Z','+00:00'))-timedelta(milliseconds=1)).isoformat().replace('+00:00','Z')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source.json';F.W.atomic(path,source)
            case=dict(gamePk='824087',sourceCensus=str(path),sourceCensusSha256=F.W.sha(path),
                selected=[dict(atBatIndex='37',playId=foul['playId'])])
            selected=F.select(raw,'824087',case)
            self.assertEqual(selected['source']['plateAppearances'],[pa])
            self.assertEqual([e['playId'] for e in selected['events']],[foul['playId']])

    def test_fixed_failure_precedes_bounded_rescan_after_version_change(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game/foul-addition'
            for pk in ('822678','823172'):
                F.W.atomic(state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json',
                           dict(promotedAtUtc='2026-10-03T00:00:00Z'))
            case=dict(gamePk='823172',selected=[dict(atBatIndex='20',playId='recorded-foul')])
            F.W.atomic(control/'823172.json',dict(status='failed',attempts=2,case=case,
                caseSha256=F.case_sha(case),implementationSha256='previous-selector'))
            self.assertEqual(F.next_case(state,limit=1),case)

    def test_exhausted_first_game_does_not_hide_later_recorded_repairs(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game/foul-addition'
            version=F.fingerprint()
            for pk in ('822678','999999'):
                F.W.atomic(state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json',
                           dict(promotedAtUtc='2026-10-01T00:00:00Z'))
            F.W.atomic(control/'822678.json',dict(status='failed',attempts=2,implementationSha256=version))
            marker=state/'pipeline/evidence/nifi/game-promotion/999999/promotion.json'
            case=dict(gamePk='999999',selected=[dict(atBatIndex='1',playId='recorded-foul')])
            F.W.atomic(control/'inventory.json',dict(games={'999999':dict(
                identity=[F.W.sha(marker),version],status='selected',case=case)}))
            self.assertEqual(F.next_case(state),case)

    def test_new_scope_can_follow_success_and_unchanged_failures_stop_at_two(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);case=dict(gamePk='1',selected=[dict(playId='later-foul')])
            control=state/'pipeline/control/mlb-game/foul-addition/1.json'
            F.W.atomic(control,dict(status='complete',implementationSha256=F.fingerprint(),
                caseSha256=F.case_sha(dict(gamePk='1',selected=[]))))
            with patch.object(F,'acquire',side_effect=ValueError('bounded-source-failure')) as acquire:
                self.assertEqual(F.tick(state,case,None,None,None)['attempts'],1)
                self.assertEqual(F.tick(state,case,None,None,None)['attempts'],2)
                self.assertEqual(F.tick(state,case,None,None,None)['attempts'],2)
                self.assertEqual(acquire.call_count,2)
            for pk in ('1','2'):
                F.W.atomic(state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json',dict(promotedAtUtc='now'))
            marker=lambda pk:state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json'
            later=dict(gamePk='2',selected=[dict(playId='independent-foul')])
            F.W.atomic(control.parent/'inventory.json',dict(games={pk:dict(
                identity=[F.W.sha(marker(pk)),F.fingerprint()],status='selected',case=value)
                for pk,value in [('1',case),('2',later)]}))
            self.assertEqual(F.next_case(state),later)

    def test_promoted_case_resumes_finalization_when_missing_foul_report_is_gone(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);case=dict(gamePk='1',selected=[dict(playId='foul')])
            control=state/'pipeline/control/mlb-game/foul-addition/1.json'
            F.W.atomic(state/'pipeline/evidence/nifi/game-promotion/1/promoted.json',dict(promotedAtUtc='now'))
            witness=dict(path='retired-owned-input',sha256='source',kind='targeted-reacquisition')
            F.W.atomic(control,dict(status='failed',case=case,caseSha256=F.case_sha(case),attempts=1,
                implementationSha256=F.fingerprint(),additionComplete=True,additionStatus='complete',sourceWitness=witness))
            self.assertEqual(F.next_case(state),case)
            with patch.object(F,'acquire') as acquire,patch.object(F.W,'add_game') as add, \
                    patch.object(F,'finish',return_value={'pitch-count':'admitted'}) as finish:
                result=F.tick(state,case,None,None,None)
                acquire.assert_not_called();add.assert_not_called();finish.assert_called_once()
                self.assertEqual(result['status'],'complete')
                self.assertIsNone(F.next_case(state))

    def test_retirement_can_finish_after_interruption_after_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'pipeline/quarantine/mlb-game/1/targeted-foul/input.json'
            F.W.atomic(source,dict(gamePk=1))
            witness=dict(path=str(source),sha256=F.W.sha(source),kind='targeted-reacquisition')
            marker=state/'pipeline/evidence/nifi/game-promotion/1/promoted.json'
            F.W.atomic(marker,dict(gamePk='1',promotedAtUtc='now'))
            refresh=Mock(return_value=[('1','pitch-count','admitted')])
            original=F.W.atomic
            def interrupt(path,value):
                if path.name=='retirement.json' and value.get('rawRetiredAfterPromotion'):raise RuntimeError('interrupted')
                original(path,value)
            with patch.object(F.W,'module',return_value=SimpleNamespace(refresh_existing_graph=refresh)), \
                    patch.object(F.W.I,'validated_promotion_record',return_value={}), \
                    patch.object(F.W.I,'query_index_contract_admission',return_value={}):
                with patch.object(F.W,'atomic',side_effect=interrupt):
                    with self.assertRaisesRegex(RuntimeError,'interrupted'):F.finish(state,'1',witness,None,None)
                self.assertFalse(source.exists())
                self.assertEqual(F.finish(state,'1',witness,None,None),{'pitch-count':'admitted'})
                refresh.assert_called_once()
                self.assertTrue(F.W.read(source.with_name('retirement.json'))['rawRetiredAfterPromotion'])
                bad=dict(witness,sha256='unrelated')
                with self.assertRaisesRegex(ValueError,'receipt does not bind'):F.finish(state,'1',bad,None,None)


if __name__=='__main__':unittest.main()
