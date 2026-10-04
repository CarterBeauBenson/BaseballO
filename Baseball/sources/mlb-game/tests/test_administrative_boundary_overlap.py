"""Accepted overlapping placement/replacement bounds keep independent identities."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import types
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
ACTIVE=ROOT/'scripts/pipeline/prepare-rml-context.py'
SOURCE=Path(os.environ['LOCALAPPDATA'])/'BaseballO/state/pipeline/quarantine/mlb-game/823350/5f2f763039f7424a94e82f5233c35304/input.json'
RAW=SOURCE.read_bytes()
assert hashlib.sha256(RAW).hexdigest()=='bd78a921eec99ef87419554f182b88313882714f9d20d77d89295a52987d27c9'
DOC=json.loads(RAW)
old=subprocess.check_output(['git','-C',str(ROOT.parent),'show','6ad0e20:Baseball/scripts/pipeline/prepare-rml-context.py'])
def context(code,name):
    m=types.ModuleType(name);m.__file__=str(ACTIVE);exec(compile(code,str(ACTIVE),'exec'),m.__dict__);return m
OLD=context(old,'overlap_before');NEW=context(ACTIVE.read_bytes(),'overlap_active')
spec=importlib.util.spec_from_file_location('overlap_proofs',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)

def target(result):return next(h for h in result['halves'] if h['inning']==10 and h['half']=='top')

class AdministrativeBoundaryOverlap(unittest.TestCase):
    def test_named_replacement_recovers_five_histories_without_changing_existing_facts(self):
        before=OLD.personal_runner_histories(RAW);after=NEW.personal_runner_histories(RAW,previous=before)
        self.assertEqual(target(before)['status'],'withheld')
        self.assertEqual(target(after),dict(inning=10,half='top',status='reconciled',issues=[],personalHistories=5))
        prior={h['lifetimeKey']:h for h in before['histories']};current={h['lifetimeKey']:h for h in after['histories']}
        self.assertTrue(prior.keys()<=current.keys())
        self.assertTrue(all(current[k]==v for k,v in prior.items()))
        placed=next(h for h in after['histories'] if h['entryAnchor']=='placement/10/top/571448')
        replacement=next(h for h in after['histories'] if h['entryAnchor']=='replacement/10/top/571448/682988')
        self.assertEqual(placed['terminationAnchor'],replacement['entryAnchor'])
        self.assertEqual(placed['episodes'],[])
        self.assertEqual(placed['terminal'],'replaced')
        self.assertTrue(replacement['episodes'])
        self.assertEqual(SOURCE.read_bytes(),RAW)
        self.assertTrue(any(i['code']=='C3_ADMINISTRATIVE_BASE_BOUNDARY' for i in after['boundaryIssues']))
        self.assertEqual({(h['inning'],h['half']) for h in after['withheldHistories']},{(8,'bottom'),(12,'bottom')})

    def test_clock_overlap_cannot_replace_missing_transition_evidence(self):
        for fault in ('base','outgoing','count','out','review','own-clock','before-placement','movement'):
            doc=copy.deepcopy(DOC);pa=next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==85)
            event=pa['playEvents'][2]
            if fault=='base':event['base']=1
            elif fault=='outgoing':event['replacedPlayer']['id']=999999999
            elif fault=='count':event['count']['balls']=1
            elif fault=='out':event['details']['isOut']=True
            elif fault=='review':event['details']['hasReview']=True
            elif fault=='own-clock':event['endTime']='2026-07-29T01:53:43.900Z'
            elif fault=='before-placement':event['startTime']='2026-07-29T01:53:00.000Z'
            else:
                for r in pa['runners']:
                    if r['details']['runner']['id']==682988:r['movement']['start']='1B'
            result=NEW.personal_runner_histories(json.dumps(doc).encode())
            self.assertFalse(result.get('reconciledAdministrativeOverlaps'),fault)
            self.assertFalse(any(h['entryAnchor']=='replacement/10/top/571448/682988' for h in result['histories']),fault)

    def test_inherited_negative_proof_does_not_close_new_selection(self):
        record=E.read(E.COMPATIBILITY_PATH)
        adapter=E.module(E.HERE/'runner-boundary-admission.py','overlap_inherited_boundary')
        prior=record['foulPitcherCompletion']['independentProofs']['runner-boundary']['previous'][0]
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);promotion=dict(gamePk='1',promotionManifestSha256='promotion')
            path=E.refresh_path(state,promotion,'b2',prior['previousImplementationSha256'])
            E.atomic(path.with_suffix('.receipt.json'),{})
            E.atomic(path,dict(status='withheld'))
            self.assertIsNone(E.EXISTING_GRAPH.load(E,state,promotion,'runner-boundary',adapter))
            self.assertEqual(E.read(path),dict(status='withheld'))
            E.atomic(path,dict(status='admitted'))
            with self.assertRaisesRegex(ValueError,'receipt changed'):
                E.EXISTING_GRAPH.load(E,state,promotion,'runner-boundary',adapter)

    def test_only_history_selection_changed_and_proof_reuse_preserves_producers(self):
        def outside(raw):
            tree=ast.parse(raw);tree.body=[n for n in tree.body if getattr(n,'name',None)!='personal_runner_histories'];return ast.dump(tree)
        self.assertEqual(outside(old),outside(ACTIVE.read_bytes()))
        bridge=E.read(E.COMPATIBILITY_PATH)['administrativeBoundaryOverlap']
        self.assertEqual(bridge['currentContextSha256'],E.sha(ACTIVE))
        for family,item in bridge['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'overlap_test_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),item['currentImplementationSha256'])
            reuse=E.code_equivalence(family,item['previousImplementationSha256'],adapter.fingerprint())
            self.assertEqual(reuse['kind'],item['reuseKind'])
            self.assertEqual(reuse['previousImplementationSha256'],item['previousImplementationSha256'])
            self.assertIsNone(E.code_equivalence(family,'unknown',adapter.fingerprint()))
            entry=bridge['independentProofs'][family]
            self.assertEqual(entry['currentImplementationSha256'],E.EXISTING_GRAPH.fingerprint(E,adapter))
            if family in ('runner-boundary','runner-resolution','pitch-count'):
                self.assertTrue(entry['requiresOriginalAdmission'])
                self.assertTrue(all(i['requiresOriginalAdmission'] for i in entry['previous']))
        for kind,adapter in [('players',E.PLAYER_PARTICIPATION),('pa',E.PLAYER_PARTICIPATION.PA),('c2pa',E.PA_RESOLUTION)]:
            self.assertEqual(E.prior_versions(kind,adapter.fingerprint()),bridge['derivedProofs'][kind]['previousImplementationSha256s'])

if __name__=='__main__':unittest.main()
