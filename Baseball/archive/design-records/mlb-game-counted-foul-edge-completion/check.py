"""Review-only F9 selector check; never maps or changes authoritative RDF."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

PACKAGE=Path(__file__).resolve().parent
ROOT=next(p for p in PACKAGE.parents if (p/'scripts/pipeline/prepare-rml-context.py').is_file())
ACTIVE=ROOT/'scripts/pipeline/prepare-rml-context.py'
EVIDENCE=json.loads((PACKAGE/'evidence.json').read_bytes())
sha=lambda data:hashlib.sha256(data).hexdigest()
assert sha(ACTIVE.read_bytes())==EVIDENCE['previousContextSha256']
with tempfile.TemporaryDirectory(prefix='f9-review-') as directory:
    work=Path(directory);candidate=work/'Baseball/scripts/pipeline/prepare-rml-context.py'
    candidate.parent.mkdir(parents=True);candidate.write_bytes(ACTIVE.read_bytes())
    subprocess.run(['git','-c','core.autocrlf=false','-C',str(work),'apply',str(PACKAGE/'selection.patch')],check=True)
    code=candidate.read_bytes();assert sha(code)==EVIDENCE['candidateContextSha256']
NEW=types.ModuleType('f9_candidate');NEW.__file__=str(ACTIVE)
exec(compile(code,str(ACTIVE),'exec'),NEW.__dict__)
spec=importlib.util.spec_from_file_location('f9_foul_owner',ROOT/'sources/mlb-game/pipeline/targeted-foul-addition.py')
OWNER=importlib.util.module_from_spec(spec);spec.loader.exec_module(OWNER)
SOURCES={};CONTEXTS={}
for case in EVIDENCE['cases']:
    raw=Path(case['sourceWitness']['path']).read_bytes()
    assert sha(raw)==case['sourceWitness']['sha256']
    SOURCES[case['gamePk']]=raw
    with tempfile.TemporaryDirectory(prefix='f9-context-') as directory:
        source=Path(directory)/'input.json';output=Path(directory)/'context.json';source.write_bytes(raw)
        with patch.object(sys,'argv',[str(ACTIVE),str(source),str(output)]),contextlib.redirect_stdout(io.StringIO()):NEW.main()
        CONTEXTS[case['gamePk']]=json.loads(output.read_bytes())


def play(document,index):
    return next(p for p in document['liveData']['plays']['allPlays'] if p['atBatIndex']==index)


class FoulSelection(unittest.TestCase):
    def test_five_exact_strikes_use_existing_owner_and_census(self):
        total=0
        for row in EVIDENCE['cases']:
            pk=row['gamePk']
            def context_run(command,**kwargs):
                Path(command[3]).write_text(json.dumps(CONTEXTS[pk]),encoding='utf-8')
                return subprocess.CompletedProcess(command,0)
            with self.subTest(game=pk),patch.object(OWNER.subprocess,'run',context_run):
                result=OWNER.select(SOURCES[pk],pk,row['case'])
                self.assertFalse(result['unresolvedFouls'])
                self.assertEqual({e['playId'] for e in result['events']},{e['playId'] for e in row['case']['selected']})
                total+=len(result['events'])
        self.assertEqual(total,5)

    def test_record_keeping_wrapper_cannot_hide_unfinished_or_extra_reviews(self):
        for fault in ('unfinished-wrapper','changed-wrapper','unfinished-call','unknown-call','extra-call','count'):
            pa=copy.deepcopy(play(CONTEXTS['823013'],62));event=pa['playEvents'][2]
            review=event['reviewDetails'];substantive=review['additionalReviews'][0]
            if fault=='unfinished-wrapper':review['inProgress']=True
            elif fault=='changed-wrapper':review['isOverturned']=True
            elif fault=='unfinished-call':substantive['inProgress']=True
            elif fault=='unknown-call':substantive['reviewType']='unknown'
            elif fault=='extra-call':review['additionalReviews'].append(copy.deepcopy(substantive))
            else:event['count']['strikes']=1
            self.assertIsNone(NEW.completed_nonterminal_field_review(pa,2),fault)

    def test_double_steal_keeps_both_runner_joins_and_final_disposition(self):
        for fault in ('unfinished','disposition','runner-name','scoring-flag','counter'):
            pa=copy.deepcopy(play(CONTEXTS['823804'],54));event=pa['playEvents'][3]
            if fault=='unfinished':event['reviewDetails']['inProgress']=True
            elif fault=='disposition':event['reviewDetails']['isOverturned']=False
            elif fault=='runner-name':event['details']['description']=event['details']['description'].replace('James Wood','Unknown Player')
            elif fault=='scoring-flag':next(r for r in pa['runners'] if r['details']['eventType']=='stolen_base_home')['details']['isScoringEvent']=False
            else:event['count']['balls']=2
            self.assertIsNone(NEW.completed_independent_review(pa,3),fault)

    def test_catcher_pickoff_association_does_not_invent_identity_or_movement(self):
        pa=play(CONTEXTS['824118'],35)
        result=NEW.completed_nonterminal_field_review(pa,2)
        self.assertEqual(result['kind'],'completed-no-movement-pickoff-review')
        self.assertNotIn('playId',result)
        for fault in ('unjoined','duplicate','not-catcher','movement','counter','unfinished'):
            mutated=copy.deepcopy(pa);event=mutated['playEvents'][2]
            if fault=='unjoined':event['actionPlayId']='missing'
            elif fault=='duplicate':mutated['playEvents'][0]=copy.deepcopy(mutated['playEvents'][1])
            elif fault=='not-catcher':event['details']['fromCatcher']=False
            elif fault=='movement':mutated['runners'].append(dict(details=dict(playIndex=2)))
            elif fault=='counter':event['count']['outs']=1
            else:event['reviewDetails']['inProgress']=True
            self.assertIsNone(NEW.completed_nonterminal_field_review(mutated,2),fault)

    def test_optional_position_word_does_not_replace_roster_and_pitcher_evidence(self):
        for fault in ('incoming','outgoing','name','pitcher','count','movement'):
            doc=copy.deepcopy(CONTEXTS['824744']);pa=play(doc,62);event=pa['playEvents'][3]
            if fault=='incoming':event['player']['id']=99999999
            elif fault=='outgoing':event['replacedPlayer']['id']=99999999
            elif fault=='name':event['details']['description']=event['details']['description'].replace('Paul Goldschmidt','Unknown Player')
            elif fault=='pitcher':pa['playEvents'][4]['_baseballO']['pitcherId']='99999999'
            elif fault=='count':event['count']['balls']=1
            else:pa['runners'].append(dict(details=dict(playIndex=3)))
            self.assertIsNone(NEW.counted_foul_neutral_event(doc,pa,event,(0,0)),fault)


if __name__=='__main__':unittest.main()

