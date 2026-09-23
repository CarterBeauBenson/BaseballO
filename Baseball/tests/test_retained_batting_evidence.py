import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('retained_batting_test',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)
R=E.RETAINED_BATTING


class RetainedBattingEvidence(unittest.TestCase):
    def fixture(self,state):
        source=R.B.census((ROOT/'data/raw/game-566279.json').read_bytes(),'566279')
        self.assertEqual(source['issues'],[])
        original=copy.deepcopy(source)
        source.update(status='withheld',issues=[dict(code='OFFENSIVE_REPLACEMENT_WITHIN_TURN',atBatIndex=0,eventIndex=1)])
        path=state/'pipeline/evidence/mlb-game/566279/original/batting-admission.json'
        E.atomic(path.with_suffix('.source.json'),source)
        proof=dict(artifactType='baseballo-batting-admission',contractVersion=1,status='withheld',
            gamePk='566279',sourceSha256=source['sourceSha256'],authoritativeRdfSha256='rdf',graph='graph',
            sourceReconciled=False,graphConforms=False,implementationSha256=R.B.fingerprint(),
            issues=source['issues'],sourceCensusSha256=E.sha(path.with_suffix('.source.json')))
        E.atomic(path,proof)
        manifest=dict(inputSha256=source['sourceSha256'],outputSha256='rdf',metricMappingMembershipVerified=True,
            contextBuilderSha256=E.read(E.COMPATIBILITY_PATH)['previousContextSha256'],
            batterParticipationEvidence=[dict(atBatIndex=str(p['atBatIndex']),playerId=p['player'].rsplit('/',1)[-1],
                actIri=p['pa']+'/batter-act',pitchIds=[]) for p in source['members']])
        manifest_path=state/'rml.json';E.atomic(manifest_path,manifest)
        marker=state/'promotion.json'
        E.atomic(marker,dict(battingAdmission=str(path),battingAdmissionSha256=E.sha(path),
            rmlManifest=str(manifest_path),rmlManifestSha256=E.sha(manifest_path)))
        promotion=dict(gamePk='566279',rawSha256=source['sourceSha256'],authoritativeRdfSha256='rdf',
            authoritativeGraph='graph',promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
        return promotion,original,path,manifest_path

    def update_manifest(self,promotion,path,change):
        manifest=E.read(path);change(manifest);E.atomic(path,manifest)
        marker_path=Path(promotion['promotionManifest']);marker=E.read(marker_path)
        marker['rmlManifestSha256']=E.sha(path);E.atomic(marker_path,marker)
        promotion['promotionManifestSha256']=E.sha(marker_path)

    def test_exact_retained_single_batter_evidence_keeps_existing_shapes_and_original_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);promotion,original,path,manifest=self.fixture(state)
            retained=path.read_bytes(),path.with_suffix('.source.json').read_bytes()
            source=R.source_census(E,state,promotion)
            self.assertEqual(source['issues'],[])
            self.assertEqual(R.B.shape_text(source),R.B.shape_text(original))
            self.assertEqual(source['roster'],original['roster'])
            self.assertEqual(source['members'],original['members'])
            self.assertEqual(retained,(path.read_bytes(),path.with_suffix('.source.json').read_bytes()))
            self.assertNotEqual(source['implementationSha256'],R.B.fingerprint())

    def test_multiple_batters_missing_members_unknown_context_and_identity_mismatch_stay_withheld(self):
        for fault in ('multiple','missing','duplicate','player','act','context','source','serialization'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);promotion,original,path,manifest=self.fixture(state)
                def change(value):
                    rows=value['batterParticipationEvidence']
                    if fault=='multiple':rows.append({**rows[0],'playerId':'999','actIri':rows[0]['actIri']+'/999'})
                    elif fault=='missing':rows.pop()
                    elif fault=='duplicate':rows[-1]=dict(rows[0])
                    elif fault=='player':rows[0]['playerId']='999'
                    elif fault=='act':rows[0]['actIri']+='/unexpected'
                    elif fault=='context':value['contextBuilderSha256']='unknown'
                    elif fault=='source':value['inputSha256']='another-source'
                    else:value['metricMappingMembershipVerified']=False
                self.update_manifest(promotion,manifest,change)
                self.assertIsNone(R.source_census(E,state,promotion))

    def test_unrelated_source_errors_and_changed_retained_artifacts_never_receive_new_admission(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);promotion,original,path,manifest=self.fixture(state)
            census_path=path.with_suffix('.source.json');census=E.read(census_path)
            census['issues'].append(dict(code='PLAYER_PA_MISMATCH'));E.atomic(census_path,census)
            with self.assertRaisesRegex(ValueError,'census changed'):R.source_census(E,state,promotion)
            proof=E.read(path);proof.update(issues=census['issues'],sourceCensusSha256=E.sha(census_path));E.atomic(path,proof)
            marker_path=Path(promotion['promotionManifest']);marker=E.read(marker_path)
            marker['battingAdmissionSha256']=E.sha(path);E.atomic(marker_path,marker)
            promotion['promotionManifestSha256']=E.sha(marker_path)
            self.assertIsNone(R.source_census(E,state,promotion))


if __name__=='__main__':unittest.main()
