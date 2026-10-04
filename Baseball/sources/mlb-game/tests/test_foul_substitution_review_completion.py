"""F8 portable witnesses and synthetic substitution/review controls."""
import contextlib
import copy
from functools import lru_cache
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

ROOT=Path(__file__).resolve().parents[3]
PACKAGE=ROOT/'archive/design-records/mlb-game-foul-substitution-review-completion'
ACTIVE=ROOT/'scripts/pipeline/prepare-rml-context.py'
EVIDENCE=json.loads((PACKAGE/'evidence.json').read_bytes())
sha=lambda data:hashlib.sha256(data).hexdigest()
code=ACTIVE.read_bytes()
NEW=types.ModuleType('f8_candidate');NEW.__file__=str(ACTIVE)
exec(compile(code,str(ACTIVE),'exec'),NEW.__dict__)
spec=importlib.util.spec_from_file_location('f8_foul_owner',ROOT/'sources/mlb-game/pipeline/targeted-foul-addition.py')
OWNER=importlib.util.module_from_spec(spec);spec.loader.exec_module(OWNER)
SOURCES={};CONTEXTS={}

@lru_cache(maxsize=1)
def load_retained_cases():
    # Existing checked-in sources only; no runtime quarantine dependency.
    for case in EVIDENCE['cases']:
        files=list((ROOT/'data/raw/samples').glob('*/'+case['gamePk']+'.json'))
        if not files:continue  # Other historical executions remain archived evidence.
        raw=files[0].read_bytes()
        assert sha(raw)==case['sourceWitness']['sha256']
        SOURCES[case['gamePk']]=raw
        with tempfile.TemporaryDirectory(prefix='f8-context-') as directory:
            source=Path(directory)/'input.json';output=Path(directory)/'context.json';source.write_bytes(raw)
            with patch.object(sys,'argv',[str(ACTIVE),str(source),str(output)]),contextlib.redirect_stdout(io.StringIO()):NEW.main()
            CONTEXTS[case['gamePk']]=json.loads(output.read_bytes())



def play(document,index):
    return next(p for p in document['liveData']['plays']['allPlays'] if p['atBatIndex']==index)


def lineup_case():
    doc=copy.deepcopy(CONTEXTS['823420']);pa=play(doc,38)
    pa['playEvents']=pa['playEvents'][2:]
    # Preserve a preceding neutral count observation for the outs control.
    pa['playEvents'].insert(0,dict(isPitch=False,details=dict(eventType='mound_visit'),
        count=dict(balls=0,strikes=0,outs=pa['playEvents'][0]['count']['outs'])))
    for i,event in enumerate(pa['playEvents']):event['index']=i
    pa['runners']=[]
    event=pa['playEvents'][1];event['count'].update(balls=0,strikes=0)
    side='home' if pa['about']['isTopInning'] else 'away'
    roster=doc['liveData']['boxscore']['teams'][side]
    leaving=next(p['person']['id'] for p in roster['players'].values() if p['person']['id'] not in roster['pitchers'])
    incoming=event['player']['id'];people=doc['gameData']['players']
    event['replacedPlayer']={'id':leaving};event['battingOrder']='900'
    event['details']['description']=(event['details']['description'].rstrip('.')+
        ', batting 9th, replacing shortstop '+people['ID'+str(leaving)]['fullName']+'.')
    return doc,pa,event


class FoulSelection(unittest.TestCase):
    def setUp(self):
        if self._testMethodName!='test_previous_proofs_keep_their_producer_and_changed_selections_require_admission':
            load_retained_cases()

    def test_previous_proofs_keep_their_producer_and_changed_selections_require_admission(self):
        evidence=OWNER.W.module(OWNER.HERE/'admission-evidence.py','f8_compatibility')
        record=evidence.read(evidence.COMPATIBILITY_PATH)
        bridge=next(v for v in record.values() if isinstance(v,dict)
            and v.get('currentContextSha256')==sha(ACTIVE.read_bytes()))
        self.assertEqual(bridge['currentContextSha256'],sha(ACTIVE.read_bytes()))
        for family,item in bridge['families'].items():
            adapter=evidence.module(OWNER.HERE/(family+'-admission.py'),'f8_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),item['currentImplementationSha256'])
            reused=evidence.code_equivalence(family,item['previousImplementationSha256'],adapter.fingerprint())
            self.assertEqual(reused['kind'],item['reuseKind'])
            independent=bridge['independentProofs'][family]
            self.assertEqual(independent['currentImplementationSha256'],evidence.EXISTING_GRAPH.fingerprint(evidence,adapter))
            if family in ('runner-resolution','pitch-count','runner-boundary'):
                original=record['foulPitcherCompletion']['independentProofs'][family]
                self.assertTrue(all(v['requiresOriginalAdmission'] for v in original['previous']))
        self.assertIsNone(evidence.code_equivalence('pitch-count','unrecognized',bridge['families']['pitch-count']['currentImplementationSha256']))

    def test_checked_in_fouls_pass_existing_owner_with_unchanged_source_census(self):
        total=0
        for row in EVIDENCE['cases']:
            pk=row['gamePk']
            if pk not in SOURCES:continue
            def context_run(command,**kwargs):
                self.assertEqual(Path(command[1]),ACTIVE)
                Path(command[3]).write_text(json.dumps(CONTEXTS[pk]),encoding='utf-8')
                return subprocess.CompletedProcess(command,0)
            with self.subTest(game=pk),patch.object(OWNER.subprocess,'run',context_run):
                result=OWNER.select(SOURCES[pk],pk,row['case'])
                self.assertFalse(result['unresolvedFouls'])
                self.assertEqual({e['playId'] for e in result['events']},{e['playId'] for e in row['case']['selected']})
                total+=len(result['events'])
        self.assertEqual(total,4)

    def test_lineup_replacement_does_not_supply_pitcher_identity(self):
        doc,pa,event=lineup_case()
        self.assertIsNotNone(NEW.counted_foul_neutral_event(doc,pa,event,(0,0)))
        for fault in ('batting-slot','lineup-person','incoming','outgoing','count','outs','movement'):
            doc,pa,event=lineup_case()
            if fault=='batting-slot':event['battingOrder']='100'
            elif fault=='lineup-person':event['replacedPlayer']['id']=999999999
            elif fault=='incoming':event['player']['id']=999999999
            elif fault=='outgoing':event['details']['description']=event['details']['description'].replace(' replaces ', ' replaces Unknown ')
            elif fault=='count':event['count']['balls']+=1
            elif fault=='outs':event['count']['outs']+=1
            else:pa['runners'].append(dict(details=dict(playIndex=event['index'])))
            self.assertIsNone(NEW.counted_foul_neutral_event(doc,pa,event,(0,0)),fault)

    def test_mid_pa_change_keeps_count_and_pitch_order_requirements(self):
        for fault in ('count','pitch-overlap','incoming','two-changes'):
            doc=copy.deepcopy(CONTEXTS['823420']);pa=play(doc,38);event=pa['playEvents'][2]
            if fault=='count':event['count']['balls']=0
            elif fault=='incoming':event['player']['id']=999999999
            elif fault=='two-changes':pa['playEvents'][1]=copy.deepcopy(event)
            else:pa['playEvents'][3]['startTime']=pa['playEvents'][0]['startTime']
            NEW.metric_pitch_context(doc)
            selected={r['playId'] for r in doc['_baseballO']['metricMappingEvidence']['countedFouls']}
            wanted=next(r for r in EVIDENCE['cases'] if r['gamePk']=='823420')['case']['selected'][0]['playId']
            self.assertNotIn(wanted,selected,fault)

    def test_linked_reviews_require_each_completed_disposition_and_unique_association(self):
        for fault in ('pending-pitch','pending-tag','association','duplicate','contradictory-tag'):
            pa=json.loads((ROOT/'sources/mlb-game/tests/fixtures/linked-review-play.json').read_bytes())['play']
            self.assertFalse(NEW.accounted_runner_history_reviews(pa)['issues'])
            pitch=pa['playEvents'][1];tag=pa['playEvents'][2]
            if fault=='pending-pitch':pitch['reviewDetails']['inProgress']=True
            elif fault=='pending-tag':tag['reviewDetails']['inProgress']=True
            elif fault=='association':tag['actionPlayId']='unmatched'
            elif fault=='duplicate':pa['playEvents'].insert(1,copy.deepcopy(pitch))
            else:tag['reviewDetails']['isOverturned']=True
            self.assertTrue(NEW.accounted_runner_history_reviews(pa)['issues'],fault)


if __name__=='__main__':unittest.main()
