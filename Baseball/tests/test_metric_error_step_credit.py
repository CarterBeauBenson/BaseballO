"""M1 partial credit, actual state, breadth and terminal-out regressions."""
import copy
import unittest
from fractions import Fraction
from test_contribution_players import M,fixture,inputs,GAME,BATTER,RUNNER,BASE,G1


def path_fixture(*,runner=False,last_end=3,out=False,first_error=False,last_error=True):
    rows=fixture(outs=1,runner_base=1 if runner else 0,contact=True)
    pa=rows[0]['entity'];person=RUNNER if runner else BATTER
    rows[0]['paResultType']=BASE+('BattedBallOutProcess' if runner else 'SingleProcess')
    template=rows[-1];whole=pa+'/history/'+person.rsplit('/',1)[1]
    segments=[]
    for index,(start,end) in enumerate(((1,2),(2,last_end)) if runner else ((0,1),(1,last_end))):
        step=dict(template,runner=person,entity=pa+f'/resolution-{index}',resolution=pa+f'/resolution-{index}',
            episode=pa+f'/episode-{index}',act=pa+f'/act-{index}',record=pa+f'/record-{index}',
            hasOutType='true' if out and index==1 else 'false',
            hasRunType='true' if end==4 and not out else 'false',hasSafeType='true' if end!=4 and not(out and index==1) else 'false',
            metricOrigin='1' if runner else '0',trajectory=whole,trajectoryHalf=GAME+'/half',trajectoryInterval=whole+'/interval')
        if start:
            step.update(originDesignation=pa+f'/origin-{index}',originRecord=step['record'],originBase=GAME+'/base/'+str(start),originCode=str(start)+'B')
        if end<4 and not(out and index==1):step.update(destinationBase=GAME+'/base/'+str(end),destinationCode=str(end)+'B',safeJudgment=pa+f'/safe-judgment-{index}',safeDecision=pa+f'/safe-decision-{index}')
        if (first_error if index==0 else last_error):step.update(secondaryError=pa+f'/error-{index}',errorJudgment=pa+f'/error-judgment-{index}',errorDecision=pa+f'/error-decision-{index}')
        segments.append(step)
    if not runner:rows.pop()
    rows.extend(segments)
    rows.extend(dict(kind='runner_history',graph=G1,game=GAME,player=person,trajectory=whole,
        trajectoryHalf=GAME+'/half',trajectoryInterval=whole+'/interval',episode=r['episode']) for r in segments)
    if last_end==4 and not out:rows.append(dict(kind='run',graph=G1,game=GAME,entity=segments[-1]['resolution']))
    return rows


class ErrorStepCredit(unittest.TestCase):
    def test_partial_distance_keeps_original_denominator_and_actual_erosion(self):
        for runner,expected in ((False,Fraction(1,4)),(True,Fraction(1,3))):
            result=inputs(path_fixture(runner=runner));self.assertTrue(result['complete'],result)
            turn,=result['plateAppearances'];score=turn['score']
            self.assertEqual(M.fraction(score['components']['progress']),expected)
            path=next(r for r in turn['participants'] if r['participant']==(RUNNER if runner else BATTER))
            self.assertEqual((path['end'],path['creditedDistance']),(3,1))
            if runner:self.assertEqual(M.fraction(score['components']['erosion']),Fraction(1,2))

    def test_terminal_out_erases_earlier_credit(self):
        result=inputs(path_fixture(out=True,last_error=False));self.assertTrue(result['complete'],result)
        score=result['plateAppearances'][0]['score']
        self.assertEqual(score['components']['progress'],M.exact(0))
        self.assertEqual(score['components']['destruction'],M.exact(Fraction(1,4)))

    def test_error_only_progress_is_zero_for_reach_and_numeric_readers(self):
        rows=path_fixture(first_error=True)
        result=inputs(rows);self.assertTrue(result['complete'],result)
        self.assertEqual(result['plateAppearances'][0]['score']['components']['progress'],M.exact(0))
        progress=M.batting_progress_evidence(rows)
        self.assertEqual(progress['unresolvedPlateAppearances'],[])
        self.assertEqual(progress['plateAppearances'][0]['reach'],0)
        self.assertEqual(progress['plateAppearances'][0]['positiveChannels'],[])
        rows=path_fixture();progress=M.batting_progress_evidence(rows)
        self.assertEqual(progress['plateAppearances'][0]['reach'],1)
        self.assertEqual(len(progress['plateAppearances'][0]['positiveChannels']),1)

    def test_error_exclusion_keeps_physical_scoring_depth(self):
        rows=path_fixture(last_end=4,first_error=True)
        for metric,expected in (('run-construction-depth',2),('run-construction-breadth',0)):
            result=M.run_construction_evidence(rows,metric_id=metric)
            self.assertEqual(result['runs'][0]['value'],M.exact(expected),result)
            self.assertEqual(len(result['runs'][0]['episodes']),2)
        rows=path_fixture(last_end=4)
        self.assertEqual(M.run_construction_evidence(rows,metric_id='run-construction-breadth')['runs'][0]['value'],M.exact(1))

    def test_partial_or_conflicting_error_join_stays_unknown(self):
        rows=path_fixture();row=next(r for r in rows if r.get('secondaryError'));row.pop('errorDecision')
        self.assertFalse(inputs(rows)['complete'])
        self.assertTrue(M.batting_progress_evidence(rows)['unresolvedPlateAppearances'])
        rows=path_fixture();row=next(r for r in rows if r.get('secondaryError'));rows.append(dict(row,errorDecision='conflicting'))
        self.assertFalse(inputs(rows)['complete'])


if __name__=='__main__':unittest.main()
