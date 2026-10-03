"""Exercise F6 in a temporary module; do not activate it or write live RDF."""
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
ROOT=PACKAGE.parents[1]
ACTIVE=ROOT/'scripts/pipeline/prepare-rml-context.py'
EVIDENCE=json.loads((PACKAGE/'evidence.json').read_bytes())
WORK=tempfile.TemporaryDirectory(prefix='f6-prefix-check-')
FOLDER=Path(WORK.name)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(ACTIVE)==EVIDENCE['previousContextSha256']
candidate=FOLDER/'Baseball/scripts/pipeline/prepare-rml-context.py'
candidate.parent.mkdir(parents=True);candidate.write_bytes(ACTIVE.read_bytes())
subprocess.run(['git','-c','core.autocrlf=false','-C',str(FOLDER),'apply',str(PACKAGE/'selection.patch')],check=True)
assert sha(candidate)==EVIDENCE['candidateContextSha256']
NEW=types.ModuleType('f6_candidate');NEW.__file__=str(ACTIVE)
exec(compile(candidate.read_bytes(),str(ACTIVE),'exec'),NEW.__dict__)
witness=EVIDENCE['sourceWitness'];assert sha(witness['path'])==witness['sha256']
output=FOLDER/'context.json'
with patch.object(sys,'argv',['context',witness['path'],str(output)]),contextlib.redirect_stdout(io.StringIO()):
    NEW.main()
DOC=json.loads(output.read_bytes())
spec=importlib.util.spec_from_file_location('f6_foul_owner',ROOT/'sources/mlb-game/pipeline/targeted-foul-addition.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


class ErrorPrefix(unittest.TestCase):
    def test_exact_selected_strike_passes_existing_identity_clock_and_outcome_checks(self):
        def context(args,**kwargs):Path(args[-1]).write_text(json.dumps(DOC),encoding='utf-8')
        with patch.object(F.subprocess,'run',side_effect=context):
            selected=F.select(Path(witness['path']).read_bytes(),'823172',EVIDENCE['case'])
        self.assertEqual([e['playId'] for e in selected['events']],['67aeb1a0-e793-3313-b02d-4132d7a338a5'])
        self.assertEqual(selected['unresolvedFouls'],[])

    def test_unreconciled_error_does_not_license_the_later_foul(self):
        for fault in ('counter','runner','movement','outs','review','link','pitch','event-kind'):
            doc=copy.deepcopy(DOC);play=next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==20)
            doc['liveData']['plays']['allPlays']=[play];event=play['playEvents'][2];row=play['runners'][0]
            if fault=='counter':event['count']['strikes']=1
            elif fault=='runner':event['player']['id']=1
            elif fault=='movement':row['movement']['end']='1B'
            elif fault=='outs':event['count']['outs']=2
            elif fault=='review':event['reviewDetails']={'inProgress':True}
            elif fault=='link':event['actionPlayId']='missing'
            elif fault=='pitch':event['isPitch']=True;event['_baseballO']={}
            elif fault=='event-kind':row['details']['eventType']='unknown'
            selected=NEW.metric_pitch_context(doc)['countedFouls']
            self.assertNotIn('67aeb1a0-e793-3313-b02d-4132d7a338a5',{r['playId'] for r in selected},fault)


if __name__=='__main__':unittest.main()
