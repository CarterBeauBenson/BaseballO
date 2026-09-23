import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission_evidence',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)


class AdmissionEvidence(unittest.TestCase):
    def test_stale_previously_withheld_is_preserved_and_never_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run/defensive.json'
            proof=dict(status='withheld',gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',
                implementationSha256='old',issues=[dict(code='INCOMPLETE_DEFENSIVE_POPULATION')])
            E.atomic(path,proof)
            marker=state/'promotion.json';E.atomic(marker,dict(defensiveAdmission=str(path),defensiveAdmissionSha256=E.sha(path)))
            promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
            result=E.diagnostic(state,promotion,'defensive','current')
            self.assertEqual((result['evidenceState'],result['previousStatus']),('implementation-stale','withheld'))
            self.assertEqual(result['previousIssues'],proof['issues'])
            adapter=SimpleNamespace(fingerprint=lambda:'current',promoted_admission=lambda *args:{'status':'withheld'})
            self.assertEqual(E.load(adapter,state,promotion,'defensive'),{'status':'withheld'})
            # A separately produced current proof still must match the exact graph,
            # source, implementation, promotion and retained artifacts.
            target=E.refresh_path(state,promotion,'defensive','current')
            E.atomic(target,{**proof,'artifactType':'baseballo-defensive-admission','contractVersion':1,
                'graph':'graph','implementationSha256':'current'})
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            self.assertEqual(E.load(adapter,state,promotion,'defensive')['issues'],proof['issues'])
            changed=E.read(target);changed['sourceSha256']='another-input';E.atomic(target,changed)
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            with self.assertRaisesRegex(ValueError,'different inputs'):E.load(adapter,state,promotion,'defensive')


if __name__=='__main__':unittest.main()
