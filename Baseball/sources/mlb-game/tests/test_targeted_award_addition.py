"""W1 retains base provenance and applies unchanged constraints to its delta."""
import tempfile
import unittest
from pathlib import Path
from rdflib import Graph,Namespace,RDF,URIRef
from rdflib.compare import isomorphic
from pyshacl import validate
from test_award_origin_final_decision import ROOT

import importlib.util
spec=importlib.util.spec_from_file_location('w1_worker',ROOT/'sources/mlb-game/pipeline/targeted-award-addition.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


class TargetedAwardAddition(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
