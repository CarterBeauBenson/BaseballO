"""Count admission remains bound to one promoted source/RDF revision."""
import json
from pathlib import Path
import tempfile
import unittest

from test_pitch_count_admission import A


class CountProvenance(unittest.TestCase):
    def fixture(self,root):
        output=root/'pipeline/evidence/mlb-game/101/run/count.json';output.parent.mkdir(parents=True)
        proof=dict(artifactType='baseballo-pitch-count-admission',contractVersion=1,gamePk='101',
            graph='https://w3id.org/baseball/graph/game/101',sourceSha256='a'*64,authoritativeRdfSha256='b'*64,
            implementationSha256=A.fingerprint(),status='admitted',sourceReconciled=True,graphConforms=True)
        for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
            path=output.with_suffix(suffix);path.write_text('retained '+suffix)
            proof[key]=A.B.sha(path.read_bytes())
        output.write_text(json.dumps(proof))
        marker=root/'promotion.json'
        marker.write_text(json.dumps(dict(pitchCountAdmission=str(output),pitchCountAdmissionSha256=A.B.sha(output.read_bytes()))))
        return output,dict(promotionManifest=str(marker),promotionManifestSha256=A.B.sha(marker.read_bytes()),
            gamePk='101',rawSha256='a'*64,authoritativeRdfSha256='b'*64,authoritativeGraph=proof['graph'])

    def test_complete_retained_proof_and_changed_source_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,promotion=self.fixture(root)
            self.assertEqual(A.promoted_admission(root,promotion)['status'],'admitted')
            promotion['rawSha256']='c'*64
            self.assertEqual(A.promoted_admission(root,promotion)['status'],'withheld')

    def test_changed_artifact_and_promotion_marker_fail(self):
        for target in ('report','marker','proof'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path,promotion=self.fixture(root)
                modified=path.with_suffix('.report.ttl') if target=='report' else Path(promotion['promotionManifest']) if target=='marker' else path
                modified.write_text('changed')
                with self.assertRaises(ValueError):A.promoted_admission(root,promotion)


if __name__=='__main__':unittest.main()
