"""W1 retains base provenance and applies unchanged constraints to its delta."""
import tempfile
import unittest
from unittest.mock import patch
import hashlib
import copy
import json
from pathlib import Path
from rdflib import Graph,Namespace,RDF,URIRef
from rdflib.compare import isomorphic
from pyshacl import validate
from test_award_origin_final_decision import ROOT

import importlib.util
spec=importlib.util.spec_from_file_location('w1_worker',ROOT/'sources/mlb-game/pipeline/targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


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

    def test_prior_decision_completion_requires_the_same_selected_facts(self):
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
                self.assertEqual(W.add_game(state,'1',witness,None,None,None,repair=repair)['status'],'already-complete')
                emit.assert_called_once()
                selected[0]['awardAdvances'].append(dict(runnerIndex='1'))
                with self.assertRaisesRegex(RuntimeError,'continue-current-selection'):
                    W.add_game(state,'1',witness,None,None,None,repair=repair)


if __name__=='__main__':unittest.main()
