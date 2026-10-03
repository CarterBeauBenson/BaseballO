"""W1 retains base provenance and applies unchanged constraints to its delta."""
import tempfile
import unittest
from unittest.mock import patch, Mock
import hashlib
import copy
import json
import io
from pathlib import Path
from rdflib import Graph,Namespace,RDF,URIRef
from rdflib.compare import isomorphic
from pyshacl import validate
from test_award_origin_final_decision import ROOT

import importlib.util
spec=importlib.util.spec_from_file_location('w1_worker',ROOT/'sources/mlb-game/pipeline/targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


class AwardRetryIdentity(unittest.TestCase):
    def test_named_recovery_preserves_new_bytes_and_resumes_cleanup_without_mapping_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);request=state/'recovery.json';raw=b'{"gamePk":42,"revision":"new"}'
            W.atomic(request,dict(scopeDecision='archive/design-records/metric-repair-scope-2026-09-30/answers.md',
                cases=[dict(gamePk='42',retiredSourceSha256='retired',retiringPromotionRunId='prior')]))
            W.atomic(state/'pipeline/evidence/mlb-game/42/prior/cleanup.json',
                dict(rawRetiredAfterPromotion=True,sourceWitness=dict(sha256='retired')))
            control=state/'pipeline/control/mlb-game/award-addition/42.json';W.atomic(control,dict(status='failed'))
            with patch.object(W,'RECOVERY',request),patch.object(W,'fingerprint',return_value='worker'), \
                    patch.object(W.urllib.request,'urlopen',return_value=io.BytesIO(raw)) as fetch:
                witness=W.recovery_witness(state)
                self.assertEqual(Path(witness['path']).read_bytes(),raw)
                self.assertEqual(witness['retiredSourceSha256'],'retired')
                self.assertEqual(W.recovery_witness(state),witness)
                self.assertEqual(fetch.call_count,1)
                def promoted(*args):
                    marker=state/'pipeline/evidence/nifi/game-promotion/42/repaired.json'
                    W.atomic(marker,dict(gamePk='42',targetedAddition=dict(sourceWitness=witness)))
                    return dict(status='complete',promotionEvidence=str(marker))
                with patch.object(W,'add_game',side_effect=promoted) as add:
                    with patch.object(W,'retire_recovery_input',side_effect=OSError('cleanup interrupted')):
                        result=W.tick(state,'42',witness,None,None,None)
                    self.assertTrue(result['additionComplete']);self.assertEqual(result['status'],'failed')
                    self.assertIsNone(W.recovery_witness(state))
                    self.assertEqual(add.call_count,1)
                self.assertEqual(W.read(control)['status'],'complete')
                self.assertFalse(Path(witness['path']).exists())
                receipt=Path(witness['path']).with_name('retirement.json');completed=receipt.read_bytes()
                self.assertTrue(W.read(receipt)['rawRetiredAfterPromotion'])
                self.assertIsNone(W.recovery_witness(state))
                self.assertEqual(receipt.read_bytes(),completed)
                self.assertEqual(fetch.call_count,1)

    def test_success_and_retry_limits_belong_to_exact_source_and_implementation(self):
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);witness=dict(path=str(state/'input.json'),sha256='first')
            with patch.object(W,'fingerprint',return_value='one') as version, \
                    patch.object(W,'add_game',return_value=dict(status='complete')) as add:
                W.tick(state,'42',witness,None,None,None)
                W.tick(state,'42',witness,None,None,None)
                self.assertEqual(add.call_count,1)
                other=dict(witness,sha256='second')
                self.assertEqual(W.tick(state,'42',other,None,None,None)['attempts'],1)
                version.return_value='two'
                self.assertEqual(W.tick(state,'42',other,None,None,None)['attempts'],1)
                self.assertEqual(add.call_count,3)
                add.side_effect=ValueError('recorded failure')
                failed=dict(witness,sha256='third')
                for count in (1,2):
                    self.assertEqual(W.tick(state,'42',failed,None,None,None)['attempts'],count)
                W.tick(state,'42',failed,None,None,None)
                self.assertEqual(add.call_count,5)
                result=W.tick(state,'42',dict(witness,sha256='fourth'),None,None,None)
                self.assertEqual(result['attempts'],1)
                self.assertEqual(result['sourceWitness']['sha256'],'fourth')

    def test_retired_input_does_not_hide_a_new_witness_after_an_older_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);control=state/'pipeline/control/mlb-game/award-addition'
            W.atomic(control/'822864.json',dict(status='complete'))
            W.atomic(control/'42.json',dict(status='complete',implementationSha256='one',sourceSha256='older'))
            retired=state/'retired/input.json';current=state/'current/input.json'
            W.atomic(current,dict(gamePk=42,liveData=dict(plays=dict(allPlays=[
                dict(result=dict(eventType='intent_walk'),playEvents=[{}]*5)]))))
            (state/'pipeline/evidence/nifi/game-promotion/42').mkdir(parents=True)
            with patch.object(W,'fingerprint',return_value='one'),patch.object(Path,'glob',return_value=iter([retired,current])), \
                    patch.object(Path,'rglob',return_value=iter([])),patch.object(W,'select',return_value=[dict(atBatIndex='1')]):
                witness=W.next_witness(state)
            self.assertEqual(witness['path'],str(current))
            self.assertEqual(witness['sha256'],W.sha(current))


class TargetedAwardAddition(unittest.TestCase):
    def test_dependency_selection_excludes_other_runners_and_requires_exact_resolution(self):
        from test_zero_pitch_walk_prefix import fixture,CONTEXT
        play,document=fixture();pa=str(play['atBatIndex'])
        awards=CONTEXT.runner_metric_evidence(play,pa,'2026',document=document)['awardAdvances']
        unrelated=copy.deepcopy(play['runners'][0]);unrelated['details']['runner']['id']=909090
        play['runners'].append(unrelated)
        before=copy.deepcopy(play)
        selected=W.selected_dependencies(play,pa,awards)
        expected=CONTEXT.runner_episode_evidence(play,pa)
        for key in selected:
            self.assertEqual(selected[key],[r for r in expected[key] if r['runnerIndex']=='0'])
            self.assertEqual(len(selected[key]),1)
        self.assertEqual(play,before)
        mismatched=copy.deepcopy(awards);mismatched[0]['resolutionKind']='out'
        with self.assertRaisesRegex(ValueError,'do not match'):
            W.selected_dependencies(play,pa,mismatched)

    def test_execution_slices_only_approved_maps_and_selected_dependency_rows(self):
        from test_zero_pitch_walk_prefix import fixture,CONTEXT
        play,document=fixture();pa=str(play['atBatIndex'])
        awards=CONTEXT.runner_metric_evidence(play,pa,'2026',document=document)['awardAdvances']
        selected=[dict(awardAdvances=awards,**W.selected_dependencies(play,pa,awards))]
        raw=json.dumps(dict(gamePk=823585,gameData=dict(venue=dict(id=5325)))).encode()
        with tempfile.TemporaryDirectory() as temp:
            context=Path(temp)/'game-context.json';mapping=Path(temp)/'award.rml.ttl'
            W.execution_inputs(raw,'823585',selected,context,mapping)
            self.assertEqual(W.read(context)['liveData']['plays']['allPlays'],
                             [{CONTEXT.CONTEXT_KEY:selected[0]}])
            graph=Graph().parse(mapping);rr=Namespace('http://www.w3.org/ns/r2rml#')
            self.assertEqual({str(s).rsplit('#',1)[-1] for s in graph.subjects(RDF.type,rr.TriplesMap)},
                             set(W.MAPS+W.DEPENDENCY_MAPS))
            text=mapping.read_text(encoding='utf-8')
            self.assertNotIn('{$.gamePk}',text)
            self.assertNotIn('{$.gameData.venue.id}',text)
            self.assertIn('/venue/5325/artifact/base/{baseCode}',text)

    def test_pending_staging_does_not_become_the_base_mapping_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            prior=Path(temp)/'staging.json';W.atomic(prior,dict(inputSha256='failed-new-source',outputSha256='failed-rdf'))
            marker=dict(gamePk='1',rmlManifestSha256='missing-original-hash')
            promotion=dict(rmlManifestAdmissionMode='pending-staging-over-current-promotion',
                authoritativeGraph='urn:original-graph',rawSha256='original-source',authoritativeRdfSha256='original-rdf',
                promotionManifest='original-promotion.json',promotionManifestSha256='original-marker')
            result=W.base_manifest(marker,promotion,prior)
            self.assertEqual(result['inputSha256'],'original-source')
            self.assertEqual(result['outputSha256'],'original-rdf')
            self.assertNotIn('outputPath',result)
            self.assertEqual(result['baseMappingManifestAvailability'],'unavailable-prior-staging-reuse')
            promotion['rmlManifestAdmissionMode']='exact-promoted-manifest'
            with self.assertRaisesRegex(ValueError,'manifest changed'):W.base_manifest(marker,promotion,prior)

    def test_scoping_keeps_award_constraints_and_rejects_missing_dependencies(self):
        base=Namespace('https://baseballontology.org/');cco=Namespace('https://www.commoncoreontologies.org/')
        sh=Namespace('http://www.w3.org/ns/shacl#');data=Graph();award=URIRef('urn:award');unrelated=URIRef('urn:unrelated')
        data.add((award,RDF.type,base.WalkProcess));data.add((award,cco.ont00001803,URIRef('urn:act')))
        data.add((unrelated,RDF.type,base.WalkProcess))
        scoped=W.authoritative_scope(data,{award});original=Graph().parse(W.HERE.parent/'shacl/authoritative.ttl')
        targets={sh.targetClass,sh.targetNode,sh.targetObjectsOf,sh.targetSubjectsOf}
        before=Graph();after=Graph()
        for triple in original:
            if triple[1] not in targets:before.add(triple)
        for triple in scoped:
            if triple[1] not in targets:after.add(triple)
        self.assertTrue(isomorphic(before,after))
        self.assertEqual(set(scoped.objects(None,sh.targetNode)),{award})
        ok,report,_=validate(data,shacl_graph=scoped,advanced=True)
        self.assertFalse(ok)
        self.assertIn(URIRef('https://w3id.org/baseball/shacl/AwardCausedAdvanceShape'),set(report.objects(None,sh.sourceShape)))

    def test_prior_selection_receipt_does_not_bypass_current_promotion_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'input.json';source.write_bytes(b'{}')
            witness=dict(path=str(source),sha256=W.sha(source))
            selected=[dict(atBatIndex='7',awardAdvances=[dict(runnerIndex='0')])]
            decisions=dict(decision=W.DECISION)
            repair=dict(decisions=decisions,select=lambda raw,pk:selected)
            marker=state/'pipeline/evidence/nifi/game-promotion/1/prior.json'
            value=dict(promotedAtUtc='2026-10-01T00:00:00Z',targetedAddition=decisions)
            W.atomic(marker,value)
            with patch.object(W.TX,'HttpGraphStore'),patch.object(W.TX,'recover'), \
                    patch.object(W.EVENT,'emit') as emit, \
                    patch.object(W.I,'validated_promotion_record',side_effect=RuntimeError('continue-current-selection')) as validate:
                with self.assertRaisesRegex(RuntimeError,'continue-current-selection'):
                    W.add_game(state,'1',witness,None,None,None,repair=repair)
                emit.assert_not_called();validate.assert_called_once()
                digest=hashlib.sha256(json.dumps(selected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                value['targetedAddition']=dict(decisions,selectionSha256=digest);W.atomic(marker,value)
                with self.assertRaisesRegex(RuntimeError,'continue-current-selection'):
                    W.add_game(state,'1',witness,None,None,None,repair=repair)
                emit.assert_not_called()
                selected[0]['awardAdvances'].append(dict(runnerIndex='1'))
                with self.assertRaisesRegex(RuntimeError,'continue-current-selection'):
                    W.add_game(state,'1',witness,None,None,None,repair=repair)


class AdditionOutputCompletion(unittest.TestCase):
    def test_empty_output_is_failure_and_same_selection_still_checks_current_triples(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'input.json';source.write_bytes(b'{}')
            witness=dict(path=str(source),sha256=W.sha(source))
            selected=[dict(atBatIndex='7')];decisions=dict(decision=W.DECISION)
            digest=hashlib.sha256(json.dumps(selected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            marker=state/'pipeline/evidence/nifi/game-promotion/1/prior.json'
            value=dict(gamePk='1',promotedAtUtc='2026-10-01T00:00:00Z',authoritativeGraph='urn:game',
                authoritativeTripleCount=1,rmlManifest=str(state/'prior.json'),rmlManifestSha256='prior',
                targetedAddition=dict(decisions,selectionSha256=digest,sourceWitness=witness))
            W.atomic(marker,value)
            base=Graph().parse(data='<urn:one> <urn:p> <urn:o> .',format='turtle')
            outputs=[Graph(),base,base+Graph().parse(data='<urn:two> <urn:p> <urn:o> .',format='turtle')]
            check=Mock(side_effect=RuntimeError('missing-triple-reaches-selected-shacl'))
            repair=dict(decisions=decisions,select=lambda raw,pk:selected,
                execution_inputs=Mock(),revalidate=check)
            def render(args,*unused):outputs[0].serialize(destination=args[args.index('-o')+1],format='turtle')
            with patch.object(W.TX,'HttpGraphStore') as store,patch.object(W.TX,'recover'), \
                    patch.object(W.EVENT,'emit') as emit,patch.object(W.I,'retain_game_artifacts'), \
                    patch.object(W.I,'validated_promotion_record',return_value={}), \
                    patch.object(W.I,'retained_artifact',return_value=state/'prior.json'), \
                    patch.object(W,'base_manifest',return_value=dict(mappingBaseIri='urn:mapping',outputSha256='base')), \
                    patch.object(W.A,'command',side_effect=render),patch.object(W.TX,'prepare') as prepare:
                store.return_value.get.return_value=base.serialize(format='nt',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'produced no triples'):
                    W.add_game(state,'1',witness,None,None,None,repair=repair)
                emit.assert_not_called();check.assert_not_called()
                outputs.pop(0)
                result=W.add_game(state,'1',witness,None,None,None,repair=repair)
                self.assertEqual(result['status'],'already-complete')
                self.assertEqual(result['promotionEvidence'],str(marker));emit.assert_called_once()
                # Same facts in a newer response do not inherit the old receipt's source.
                source.write_bytes(b'{"revision":2}');new_witness=dict(witness,sha256=W.sha(source))
                result=W.add_game(state,'1',new_witness,None,None,None,repair=repair)
                self.assertEqual(result['status'],'already-present')
                self.assertNotIn('sourceWitness',result)
                outputs.pop(0)
                with self.assertRaisesRegex(RuntimeError,'missing-triple-reaches-selected-shacl'):
                    W.add_game(state,'1',new_witness,None,None,None,repair=repair)
                check.assert_called_once();prepare.assert_not_called()


if __name__=='__main__':unittest.main()
