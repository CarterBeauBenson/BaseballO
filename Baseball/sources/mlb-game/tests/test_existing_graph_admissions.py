"""A later retained witness can verify existing facts, never replace them."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rdflib import RDF,URIRef
from test_batting_admission import B,BASE,fixture

E=B.module(B.HERE/'admission-evidence.py','existing_graph_test_evidence')
X=E.EXISTING_GRAPH


class ExistingGraphAdmissions(unittest.TestCase):
    def test_unchanged_shacl_distinguishes_matching_and_missing_graph_facts(self):
        for missing in (False,True):
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as temporary:
                state=Path(temporary);source,graph=fixture();raw=b'{"separate":"retained response"}'
                source.update(gamePk='1',sourceSha256=B.sha(raw),sourceRevision='later',status='reconciled',
                    issues=[],implementationSha256=B.fingerprint())
                if missing:graph.remove((URIRef(source['members'][0]['pa']+'/result'),RDF.type,BASE.WalkProcess))
                rdf=state/'existing.ttl';graph.serialize(destination=rdf,format='turtle');before=rdf.read_bytes()
                response=state/'input.json';response.write_bytes(raw)
                marker=state/'promotion.json';E.atomic(marker,dict(gamePk='1'));original=marker.read_bytes()
                promotion=dict(gamePk='1',authoritativeGraph='https://w3id.org/baseball/graph/game/1',
                    rawSha256='original-response',authoritativeRdfSha256='original-graph-bytes',
                    promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
                witness=dict(kind='retained-source-response',path=str(response),sha256=B.sha(raw))
                with patch.object(X,'SHORT',{'batting':'b1'}),patch.object(E,'module',return_value=B), \
                     patch.object(E,'load',return_value=dict(status='withheld')), \
                     patch.object(B,'census',return_value=copy.deepcopy(source)):
                    results=X.validate(E,state,promotion,witness,rdf,None,None,None)
                    self.assertIsNone(X.load(E,state,promotion,'batting',B))
                    X.commit(E,promotion,results)
                    proof=X.load(E,state,promotion,'batting',B)
                self.assertEqual(proof['status'],'withheld' if missing else 'admitted')
                self.assertEqual(proof['sourceSha256'],B.sha(raw))
                self.assertEqual(proof['promotionSourceSha256'],'original-response')
                self.assertEqual(proof['authoritativeRdfSha256'],'original-graph-bytes')
                self.assertEqual(proof['validationExportSha256'],B.sha(before))
                self.assertEqual(rdf.read_bytes(),before)
                self.assertEqual(marker.read_bytes(),original)
                with self.assertRaisesRegex(ValueError,'another input'):
                    X.load(E,state,dict(promotion,rawSha256='different-original'),'batting',B)


if __name__=='__main__':unittest.main()
