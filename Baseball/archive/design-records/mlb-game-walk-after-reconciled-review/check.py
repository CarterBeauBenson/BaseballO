"""Review-only W5 selection check over unchanged retained evidence."""
import copy
import hashlib
import importlib.util
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
with tempfile.TemporaryDirectory(prefix='w5-review-') as directory:
    work=Path(directory);candidate=work/'Baseball/scripts/pipeline/prepare-rml-context.py'
    candidate.parent.mkdir(parents=True);candidate.write_bytes(ACTIVE.read_bytes())
    subprocess.run(['git','-c','core.autocrlf=false','-C',str(work),'apply',str(PACKAGE/'selection.patch')],check=True)
    code=candidate.read_bytes();assert sha(code)==EVIDENCE['candidateContextSha256']
NEW=types.ModuleType('w5_candidate');NEW.__file__=str(ACTIVE)
exec(compile(code,str(ACTIVE),'exec'),NEW.__dict__)
spec=importlib.util.spec_from_file_location('w5_original',ACTIVE)
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
raw=Path(EVIDENCE['sourceWitness']['path']).read_bytes()
assert sha(raw)==EVIDENCE['sourceWitness']['sha256']
DOCUMENT=json.loads(raw)


def play(index):
    return copy.deepcopy(next(p for p in DOCUMENT['liveData']['plays']['allPlays'] if p['atBatIndex']==index))


def awards(module,pa):
    return module.runner_metric_evidence(pa,str(pa['atBatIndex']),'2026',document=DOCUMENT)['awardAdvances']


class WalkReviewSelection(unittest.TestCase):
    def test_two_existing_reviews_keep_only_the_later_batter_award(self):
        for row in EVIDENCE['cases']:
            pa=play(row['atBatIndex'])
            self.assertEqual(awards(OLD,pa),[])
            self.assertFalse(OLD.accounted_runner_history_reviews(pa)['issues'])
            selected=awards(NEW,pa)
            self.assertEqual(len(selected),1)
            self.assertEqual(selected[0]['runnerIndex'],str(row['runnerIndex']))
            self.assertEqual(selected[0]['atBatIndex'],str(row['atBatIndex']))
            self.assertEqual(selected[0]['ruleCode'],'5.05(b)(1)')

    def test_unfinished_or_unknown_reviews_still_withhold(self):
        for index,event in ((11,6),(66,5)):
            for fault in ('unfinished','unknown'):
                pa=play(index);review=pa['playEvents'][event]['reviewDetails']
                review['inProgress']=True if fault=='unfinished' else False
                if fault=='unknown':review['reviewType']='unknown'
                self.assertEqual(awards(NEW,pa),[],(index,fault))

    def test_mismatched_review_counters_still_withhold(self):
        for index,event in ((11,6),(66,5)):
            pa=play(index);pa['playEvents'][event]['count']['outs']+=1
            self.assertEqual(awards(NEW,pa),[],index)

    def test_final_count_destination_and_identity_remain_required(self):
        for fault in ('count','destination','post-occupant','event-join'):
            pa=play(66)
            if fault=='count':pa['playEvents'][-1]['count']['balls']=3
            elif fault=='destination':pa['runners'][0]['movement']['end']='2B'
            elif fault=='post-occupant':pa['matchup']['postOnFirst']['id']=99999999
            else:pa['runners'][0]['details']['playIndex']=0
            self.assertEqual(awards(NEW,pa),[],fault)

    def test_preceding_reviewed_steal_is_not_a_forced_award(self):
        pa=play(11);selected=awards(NEW,pa)
        self.assertEqual({r['runnerIndex'] for r in selected},{'1'})
        self.assertEqual(pa['runners'][0]['details']['eventType'],'stolen_base_2b')


if __name__=='__main__':unittest.main()
