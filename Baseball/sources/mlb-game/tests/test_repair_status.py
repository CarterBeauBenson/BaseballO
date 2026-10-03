"""NiFi observations must not turn zero recorded failures into full coverage."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

FILE=Path(__file__).resolve().parents[1]/'pipeline/repair-status.py'
spec=importlib.util.spec_from_file_location('repair_status',FILE)
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8')


class RepairStatus(unittest.TestCase):
    def owner(self):
        return SimpleNamespace(cases=lambda:[],DISCOVERY=SimpleNamespace(fingerprint=lambda owner:'worker'),
            completed_case=lambda p,c:p.get('status')=='complete' and
                p.get('repairRequestSha256')==c.get('repairRequestSha256'),
            TX=SimpleNamespace(now=lambda:'now'),atomic=write)

    def test_zero_failures_with_unseen_or_changed_promotion_is_not_clear(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);marker=state/'pipeline/evidence/nifi/game-promotion/1/marker.json'
            self.assertFalse(S.observe(state,self.owner())['recordedWorkClear'])
            write(marker,dict(promotedAtUtc='2026-10-03T00:00:00Z'))
            report=S.observe(state,self.owner())
            self.assertFalse(report['recordedWorkClear'])
            self.assertEqual(report['historyDiscovery']['uninspectedGames'],['1'])
            inventory=state/'pipeline/control/mlb-game/history-discovery/inventory.json'
            write(inventory,dict(games={'1':dict(status='not-applicable',identity=[S.digest(marker),'worker'])}))
            self.assertTrue(S.observe(state,self.owner())['recordedWorkClear'])
            write(inventory,dict(games={'1':dict(status='awaiting-source',identity=[S.digest(marker),'worker'])}))
            report=S.observe(state,self.owner())
            self.assertFalse(report['recordedWorkClear'])
            self.assertEqual(report['historyDiscovery']['awaitingSource'],['1'])
            write(marker,dict(promotedAtUtc='2026-10-03T01:00:00Z'))
            report=S.observe(state,self.owner())
            self.assertFalse(report['recordedWorkClear'])
            self.assertEqual(report['historyDiscovery']['outdatedInspections'],['1'])

    def test_partials_coverage_gaps_and_wrong_request_success_stay_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game'
            write(control/'foul-addition/1.json',dict(status='partial',unresolvedFouls=[dict(reason='UNEXPLAINED_COUNTER_TRANSITION')]))
            write(control/'history-addition/2.json',dict(status='complete',repairRequestSha256='old'))
            write(control/'admission-evidence/5.json',dict(status='current',familyFailures={
                'player-participation':dict(error='A complete unambiguous roster is required')}))
            write(control/'history-discovery/inventory.json',dict(games={
                '2':dict(status='selected',case=dict(repairRequestSha256='current')),
                '3':dict(status='retained-history-census-unavailable')}))
            source_issue=dict(code='SOURCE_RECONCILIATION',detail='ambiguous source')
            write(control/'defensive-addition/inventory.json',dict(inputs={'input':dict(status='unresolved-source',
                gamePk='4',sha256='source',sourceIssues=[source_issue])}))
            report=S.observe(state,self.owner())
            self.assertFalse(report['recordedWorkClear']);self.assertEqual(report['status'],'attention-required')
            self.assertEqual(report['historyDiscovery']['selectedPending'],['2'])
            self.assertEqual(report['coverageLimits']['unavailableHistoryEvidence'],['3'])
            self.assertEqual(report['coverageLimits']['unresolvedDefensiveSources'],['4'])
            self.assertEqual(report['coverageLimits']['defensiveSourceEvidence'],[
                dict(sourcePath='input',gamePk='4',sha256='source',sourceIssues=[source_issue])])
            self.assertEqual(report['issues'][0]['unresolvedFouls'][0]['reason'],'UNEXPLAINED_COUNTER_TRANSITION')
            self.assertEqual(next(i for i in report['issues'] if i['gamePk']=='5')['familyFailures']
                ['player-participation']['error'],'A complete unambiguous roster is required')

    def test_reports_corruption_and_only_supersedes_quarantine_after_later_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game'
            p=control/'history-addition/1.json';p.parent.mkdir(parents=True);p.write_text('{')
            q=state/'pipeline/quarantine/rml/game-1-20261003T010000Z';q.mkdir(parents=True)
            marker=state/'pipeline/evidence/nifi/game-promotion/1/marker.json'
            write(marker,dict(promotedAtUtc='2026-10-03T00:00:00.0000000Z'))
            report=S.observe(state,self.owner())
            self.assertEqual(len(report['observationErrors']),1)
            self.assertEqual(len(report['rmlQuarantine']['withoutLaterPromotion']),1)
            write(marker,dict(promotedAtUtc='2026-10-03T02:00:00.0000000Z'))
            summary=S.publish(state,self.owner())
            report=S.read(control/'repair-status.json')
            self.assertEqual(report['rmlQuarantine']['historicalWithLaterPromotion'],1)
            self.assertFalse(summary['recordedWorkClear'])
            self.assertEqual(p.read_text(),'{')

    def test_foul_diagnostics_preserve_event_counts_and_require_the_exact_witness(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);source=state/'pipeline/quarantine/mlb-game/1/repair/input.json'
            write(source,dict(gamePk=1,liveData=dict(plays=dict(allPlays=[dict(atBatIndex=20,
                playEvents=[dict(index=1,type='no_pitch',count=dict(balls=1,strikes=0))])]))))
            record=dict(sourceWitness=dict(path=str(source),sha256=S.digest(source)),
                unresolvedFouls=[dict(atBatIndex='20')])
            self.assertEqual(S.foul_source_excerpt(state,'1',record)[0]['events'][0]['type'],'no_pitch')
            record['case']=dict(selected=record.pop('unresolvedFouls'))
            self.assertEqual(S.foul_source_excerpt(state,'1',record)[0]['atBatIndex'],20)
            source.write_text('{}')
            with self.assertRaisesRegex(ValueError,'differs from the repair witness'):
                S.foul_source_excerpt(state,'1',record)


if __name__=='__main__':unittest.main()
