"""W1 preserves the award selector and reuses C3 for a neutral PR prefix."""
import copy
import unittest
from test_award_origin_final_decision import CONTEXT, play


def fixture():
    source=play('823585',79)
    outs=source['count']['outs'];about=source['about']
    prefix=dict(index=0,type='action',isPitch=False,isSubstitution=True,
        player={'id':101},replacedPlayer={'id':102},position={'abbreviation':'PR'},base=2,
        startTime='2026-08-25T20:00:00Z',endTime='2026-08-25T20:00:01Z',
        count=dict(balls=0,strikes=0,outs=outs),details=dict(eventType='offensive_substitution',
        isOut=False,isScoringPlay=False,hasReview=False,isBall=False,isStrike=False,isInPlay=False))
    mound=copy.deepcopy(prefix);mound.update(index=1,isSubstitution=False)
    mound['details']['eventType']='mound_visit'
    for event in source['playEvents']:event['index']+=2
    for row in source['runners']:row['details']['playIndex']+=2
    source['playEvents']=[prefix,mound,*source['playEvents']]
    anchor=f"replacement/{about['inning']}/{about['halfInning']}/102/101"
    witness=dict(anchor=anchor,form='replacement',runnerId='101',outgoingRunnerId='102',
        base=2,atBatIndex=about['atBatIndex'],eventIndex=0,
        earliestStartBound=prefix['startTime'],latestEndBound=prefix['endTime'])
    document={CONTEXT.CONTEXT_KEY:dict(runnerHistoryReconciliation=dict(sourceConsistency='consistent',histories=[
        dict(runnerId='102',terminal='replaced',terminationAnchor=anchor,terminationWitness=witness),
        dict(runnerId='101',entryAnchor=anchor,entryWitness=witness)]))}
    return source,document


class ZeroPitchWalkPrefix(unittest.TestCase):
    def test_reconciled_prefix_uses_actual_terminal_join_and_keeps_one_award(self):
        source,document=fixture();before=copy.deepcopy((source,document))
        self.assertEqual(CONTEXT.zero_pitch_walk_terminal(source,document),5)
        rows=CONTEXT.runner_metric_evidence(source,'79','2026',document=document)['awardAdvances']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['ruleCode'],'5.05(b)(1)')
        self.assertEqual((source,document),before)
        source['runners'][0]['details']['playIndex']=3
        self.assertEqual(CONTEXT.runner_metric_evidence(source,'79','2026',document=document)['awardAdvances'],[])

    def test_unknown_or_changed_prefix_and_unreconciled_replacement_stay_withheld(self):
        for fault in ('unknown','pinch-hitter','review','out','score','count','pitch','base','witness','missing-vb','vb-count'):
            source,document=fixture();e=source['playEvents'][0]
            if fault=='unknown':e['details']['eventType']='unknown'
            elif fault=='pinch-hitter':e['position']['abbreviation']='PH'
            elif fault=='review':e['details']['hasReview']=True
            elif fault=='out':e['details']['isOut']=True
            elif fault=='score':e['details']['isScoringPlay']=True
            elif fault=='count':e['count']['balls']=1
            elif fault=='pitch':e['isPitch']=True
            elif fault=='base':e['base']=3
            elif fault=='witness':document[CONTEXT.CONTEXT_KEY]['runnerHistoryReconciliation']['histories'].pop()
            elif fault=='missing-vb':source['playEvents'].pop()
            else:source['playEvents'][3]['count']['balls']=3
            self.assertIsNone(CONTEXT.zero_pitch_walk_terminal(source,document),fault)
            self.assertEqual(CONTEXT.runner_metric_evidence(source,'79','2026',document=document)['awardAdvances'],[],fault)

    def test_mound_only_needs_no_replacement_and_no_prefix_keeps_existing_result(self):
        source,document=fixture();source['playEvents'].pop(0)
        for e in source['playEvents']:e['index']-=1
        for row in source['runners']:row['details']['playIndex']-=1
        self.assertEqual(CONTEXT.zero_pitch_walk_terminal(source),4)
        self.assertEqual(len(CONTEXT.runner_metric_evidence(source,'79','2026')['awardAdvances']),1)
        original=play('823585',79)
        self.assertEqual(CONTEXT.zero_pitch_walk_terminal(original),3)
        self.assertEqual(len(CONTEXT.runner_metric_evidence(original,'79','2026')['awardAdvances']),1)

    def test_zero_episode_runner_keeps_replacement_without_admitting_a_history(self):
        source,document=fixture();h=document[CONTEXT.CONTEXT_KEY]['runnerHistoryReconciliation']
        incoming=h['histories'].pop();incoming['episodes']=[]
        h['boundaryAnchorCensus']=[incoming['entryWitness']]
        h['withheldHistories']=[dict(inning=source['about']['inning'],half=source['about']['halfInning'],
            issues=[dict(code='ZERO_EPISODE_PERSONAL_HISTORY')],completedCandidates=[incoming])]
        before=copy.deepcopy(document)
        self.assertEqual(CONTEXT.zero_pitch_walk_terminal(source,document),5)
        self.assertEqual(document,before)
        h['withheldHistories'][0]['issues'].append(dict(code='UNRESOLVED_RUNNER'))
        self.assertIsNone(CONTEXT.zero_pitch_walk_terminal(source,document))


if __name__=='__main__':unittest.main()
