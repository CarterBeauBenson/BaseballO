"""Exercise the H4 candidate without changing the active context or graph."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest

PACKAGE=Path(__file__).resolve().parent
ROOT=next(p for p in PACKAGE.parents if (p/'scripts/pipeline/prepare-rml-context.py').is_file())
ACTIVE=ROOT/'scripts/pipeline/prepare-rml-context.py'
EVIDENCE=json.loads((PACKAGE/'evidence.json').read_bytes())
sha=lambda data:hashlib.sha256(data).hexdigest()
assert sha(ACTIVE.read_bytes())==EVIDENCE['previousContextSha256']
with tempfile.TemporaryDirectory(prefix='h4-review-') as directory:
    work=Path(directory);candidate=work/'Baseball/scripts/pipeline/prepare-rml-context.py'
    candidate.parent.mkdir(parents=True);candidate.write_bytes(ACTIVE.read_bytes())
    subprocess.run(['git','-c','core.autocrlf=false','-C',str(work),'apply',str(PACKAGE/'selection.patch')],check=True)
    code=candidate.read_bytes();assert sha(code)==EVIDENCE['candidateContextSha256']
NEW=types.ModuleType('h4_candidate');NEW.__file__=str(ACTIVE)
exec(compile(code,str(ACTIVE),'exec'),NEW.__dict__)
OLD=types.ModuleType('h4_previous');OLD.__file__=str(ACTIVE)
exec(compile(ACTIVE.read_bytes(),str(ACTIVE),'exec'),OLD.__dict__)
SOURCES={}
for case in EVIDENCE['cases']:
    raw=Path(case['sourceWitness']['path']).read_bytes()
    assert sha(raw)==case['sourceWitness']['sha256']
    SOURCES[case['gamePk']]=(raw,json.loads(raw))


class RunnerReviewCompletion(unittest.TestCase):
    def test_named_halves_reconcile_without_changing_existing_histories(self):
        for case in EVIDENCE['cases']:
            with self.subTest(game=case['gamePk']):
                raw,doc=SOURCES[case['gamePk']]
                before=OLD.personal_runner_histories(raw)
                after=NEW.personal_runner_histories(raw,previous=before)
                half=next(h for h in after['halves'] if h['inning']==9 and h['half']=='top')
                self.assertEqual(half,case['candidateHalf'])
                self.assertEqual(half['status'],'reconciled')
                old={h['lifetimeKey']:h for h in before['histories']}
                new={h['lifetimeKey']:h for h in after['histories']}
                self.assertTrue(old.keys()<=new.keys())
                self.assertTrue(all(new[k]==v for k,v in old.items()))
                self.assertEqual(len(new)-len(old),half['personalHistories'])
                self.assertEqual(raw,Path(case['sourceWitness']['path']).read_bytes())

    def test_hbp_foul_tip_rejects_unfinished_or_changed_effects(self):
        play=next(p for p in SOURCES['823200'][1]['liveData']['plays']['allPlays'] if p['atBatIndex']==76)
        for fault in ('pending','count','movement'):
            changed=copy.deepcopy(play);event=changed['playEvents'][0]
            if fault=='pending':event['reviewDetails']['inProgress']=True
            elif fault=='count':event['count']['strikes']=2
            else:changed['runners'][0]['details']['playIndex']=event['index']
            self.assertTrue(NEW.accounted_runner_history_reviews(changed)['issues'],fault)

    def test_catcher_pickoff_rejects_unsupported_associations_and_outcomes(self):
        play=next(p for p in SOURCES['823523'][1]['liveData']['plays']['allPlays'] if p['atBatIndex']==72)
        for fault in ('association','duplicate-association','out','base','pending-review'):
            changed=copy.deepcopy(play);event=changed['playEvents'][-1]
            if fault=='association':event['actionPlayId']='unmatched'
            elif fault=='duplicate-association':changed['playEvents'].insert(0,copy.deepcopy(changed['playEvents'][1]))
            elif fault=='out':changed['runners'][0]['movement']['outNumber']=2
            elif fault=='base':changed['runners'][0]['movement']['start']='2B'
            else:changed['reviewDetails']['inProgress']=True
            self.assertTrue(NEW.accounted_runner_history_reviews(changed)['issues'],fault)


if __name__=='__main__':unittest.main()
