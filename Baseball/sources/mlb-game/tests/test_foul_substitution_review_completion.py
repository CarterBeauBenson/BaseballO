"""F8 regression against the active selector and exact retained witnesses."""
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
    # Only historical witness tests need the temporary NiFi inputs. Code/proof
    # compatibility must remain testable after successful input cleanup.
    for case in EVIDENCE['cases']:
        raw=Path(case['sourceWitness']['path']).read_bytes()
        assert sha(raw)==case['sourceWitness']['sha256']
        SOURCES[case['gamePk']]=raw
        with tempfile.TemporaryDirectory(prefix='f8-context-') as directory:
            source=Path(directory)/'input.json';output=Path(directory)/'context.json';source.write_bytes(raw)
            with patch.object(sys,'argv',[str(ACTIVE),str(source),str(output)]),contextlib.redirect_stdout(io.StringIO()):NEW.main()
            CONTEXTS[case['gamePk']]=json.loads(output.read_bytes())


def play(document,index):
    return next(p for p in document['liveData']['plays']['allPlays'] if p['atBatIndex']==index)


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

    def test_eight_fouls_pass_existing_owner_with_unchanged_source_census(self):
        total=0
        for row in EVIDENCE['cases']:
            pk=row['gamePk']
            def context_run(command,**kwargs):
                self.assertEqual(Path(command[1]),ACTIVE)
                Path(command[3]).write_text(json.dumps(CONTEXTS[pk]),encoding='utf-8')
                return subprocess.CompletedProcess(command,0)
            with self.subTest(game=pk),patch.object(OWNER.subprocess,'run',context_run):
                result=OWNER.select(SOURCES[pk],pk,row['case'])
                self.assertFalse(result['unresolvedFouls'])
                self.assertEqual({e['playId'] for e in result['events']},{e['playId'] for e in row['case']['selected']})
                total+=len(result['events'])
        self.assertEqual(total,8)

    def test_lineup_replacement_does_not_supply_pitcher_identity(self):
        for fault in ('batting-slot','lineup-person','incoming','outgoing','count','outs','movement'):
            doc=copy.deepcopy(CONTEXTS['823452']);pa=play(doc,65)
            event=next(e for e in pa['playEvents'] if e.get('details',{}).get('eventType')=='pitching_substitution')
            if fault=='batting-slot':event['battingOrder']='900'
            elif fault=='lineup-person':event['replacedPlayer']['id']=999999999
            elif fault=='incoming':event['player']['id']=999999999
            elif fault=='outgoing':event['details']['description']=event['details']['description'].replace('William Kempner','Unknown Pitcher')
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
            pa=copy.deepcopy(play(CONTEXTS['823396'],80));pitch=pa['playEvents'][1];tag=pa['playEvents'][2]
            if fault=='pending-pitch':pitch['reviewDetails']['inProgress']=True
            elif fault=='pending-tag':tag['reviewDetails']['inProgress']=True
            elif fault=='association':tag['actionPlayId']='unmatched'
            elif fault=='duplicate':pa['playEvents'].insert(1,copy.deepcopy(pitch))
            else:tag['reviewDetails']['isOverturned']=True
            self.assertTrue(NEW.accounted_runner_history_reviews(pa)['issues'],fault)


if __name__=='__main__':unittest.main()
