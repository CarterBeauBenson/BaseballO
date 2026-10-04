"""Exercise F7 in a temporary module; do not activate it or write live RDF."""
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
WORK=tempfile.TemporaryDirectory(prefix='f7-prefix-check-')
FOLDER=Path(WORK.name)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(ACTIVE)==EVIDENCE['candidateContextSha256']:
    candidate=ACTIVE
else:
    assert sha(ACTIVE)==EVIDENCE['previousContextSha256']
    candidate=FOLDER/'Baseball/scripts/pipeline/prepare-rml-context.py'
    candidate.parent.mkdir(parents=True);candidate.write_bytes(ACTIVE.read_bytes())
    subprocess.run(['git','-c','core.autocrlf=false','-C',str(FOLDER),'apply',str(PACKAGE/'selection.patch')],check=True)
assert sha(candidate)==EVIDENCE['candidateContextSha256']
NEW=types.ModuleType('f7_candidate');NEW.__file__=str(ACTIVE)
exec(compile(candidate.read_bytes(),str(ACTIVE),'exec'),NEW.__dict__)
witness=EVIDENCE['sourceWitness'];assert sha(witness['path'])==witness['sha256']
output=FOLDER/'context.json'
with patch.object(sys,'argv',['context',witness['path'],str(output)]),contextlib.redirect_stdout(io.StringIO()):
    NEW.main()
DOC=json.loads(output.read_bytes())
spec=importlib.util.spec_from_file_location('f7_foul_owner',ROOT/'sources/mlb-game/pipeline/targeted-foul-addition.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


class BatterChain(unittest.TestCase):
    def test_named_foul_keeps_its_exact_identity_clocks_and_outcome(self):
        def context(args,**kwargs):Path(args[-1]).write_text(json.dumps(DOC),encoding='utf-8')
        with patch.object(F.subprocess,'run',side_effect=context):
            selected=F.select(Path(witness['path']).read_bytes(),'823312',EVIDENCE['case'])
        self.assertEqual([e['playId'] for e in selected['events']],['b42bce27-908d-3f43-9387-3eb07f1ef7f3'])
        self.assertEqual(selected['unresolvedFouls'],[])

    def test_contradictory_chains_do_not_select_the_foul(self):
        for fault in ('count','outs','chain','roster','pitch-participant','review','movement','late-ph'):
            doc=copy.deepcopy(DOC);play=next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==73)
            doc['liveData']['plays']['allPlays']=[play];event=play['playEvents'][3]
            if fault=='count':event['count']['balls']=1
            elif fault=='outs':event['count']['outs']=1
            elif fault=='chain':event['replacedPlayer']['id']=609280
            elif fault=='roster':doc['liveData']['boxscore']['teams']['home']['players'].pop('ID657757')
            elif fault=='pitch-participant':play['playEvents'][4]['_baseballO']['batterId']='657757'
            elif fault=='review':event['reviewDetails']={'inProgress':True}
            elif fault=='movement':play['runners'][0]['details']['playIndex']=3
            elif fault=='late-ph':play['playEvents'].append(copy.deepcopy(event))
            selected=NEW.metric_pitch_context(doc)['countedFouls']
            self.assertNotIn('b42bce27-908d-3f43-9387-3eb07f1ef7f3',{r['playId'] for r in selected},fault)


if __name__=='__main__':unittest.main()
