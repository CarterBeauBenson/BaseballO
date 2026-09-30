"""Retired input/export files do not prevent checking retained source facts."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rdflib import RDF,URIRef
from test_batting_admission import B,BASE,fixture

E=B.module(B.HERE/'admission-evidence.py','retained_census_test_evidence')
C=E.RETAINED_CENSUS


class RetainedCensusAdmissions(unittest.TestCase):
    def test_default_windows_root_keeps_all_sidecars_within_path_limit(self):
        state=Path('C:/Users/carte/AppData/Local/BaseballO/state')
        promotion=dict(gamePk='823332',promotionManifestSha256='a'*64)
        with patch.object(C,'fingerprint',return_value='b'*64):
            path=C.path_for(E,state,promotion,'runner-resolution',B)
            for suffix in ('.source.json','.receipt.json','.shapes.ttl','.report.ttl'):
                self.assertLess(len(str(path.with_suffix(suffix))),260)
            changed=C.path_for(E,state,dict(promotion,promotionManifestSha256='c'*64),'runner-resolution',B)
            self.assertNotEqual(path,changed)

    def test_existing_source_and_current_shacl_preserve_missing_facts_and_source_failures(self):
        for mode in ('valid','missing-fact','source-unresolved'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                state=Path(directory);source,graph=fixture()
                source.update(gamePk='1',sourceSha256='original-source',sourceRevision='original',status='reconciled',issues=[],implementationSha256=B.fingerprint())
                if mode=='missing-fact':graph.remove((URIRef(source['members'][0]['pa']+'/result'),RDF.type,BASE.WalkProcess))
                if mode=='source-unresolved':source.update(status='withheld',issues=[dict(code='UNRESOLVED_COMPLETED_RESULT')])
                census=state/'pipeline/evidence/mlb-game/1/original/batting.source.json';E.atomic(census,source)
                original=census.read_bytes();rdf=state/'live-export.ttl';graph.serialize(destination=rdf,format='turtle')
                marker=state/'promotion.json'
                promotion=dict(gamePk='1',authoritativeGraph='https://w3id.org/baseball/graph/game/1',rawSha256='original-source',
                    authoritativeRdfSha256='promoted-rdf-hash',promotionManifest=str(marker))
                proof=dict(gamePk='1',graph=promotion['authoritativeGraph'],sourceSha256='original-source',
                    authoritativeRdfSha256='promoted-rdf-hash',implementationSha256=B.fingerprint(),sourceCensusSha256=E.sha(census))
                previous=census.with_name('batting.json');E.atomic(previous,proof)
                E.atomic(marker,dict(battingAdmission=str(previous),battingAdmissionSha256=E.sha(previous)))
                promotion['promotionManifestSha256']=E.sha(marker)
                witness=C.source(E,state,promotion,'batting',B)
                self.assertEqual(witness['censusProducerSha256'],B.fingerprint())
                with patch.object(E,'module',return_value=B):
                    results=C.validate(E,state,promotion,{'batting':witness},rdf,None,None,None)
                    self.assertIsNone(C.load(E,state,promotion,'batting',B))
                    E.EXISTING_GRAPH.commit(E,promotion,results)
                    checked=C.load(E,state,promotion,'batting',B)
                self.assertEqual(checked['status'],'admitted' if mode=='valid' else 'withheld')
                self.assertEqual(census.read_bytes(),original)
                self.assertEqual(checked['authoritativeRdfSha256'],'promoted-rdf-hash')
                self.assertEqual(checked['sourceSha256'],'original-source')
                if mode=='source-unresolved':self.assertEqual(checked['issues'],source['issues'])
                census.write_text('{}')
                with self.assertRaisesRegex(ValueError,'census changed'):C.load(E,state,promotion,'batting',B)


if __name__=='__main__':unittest.main()
