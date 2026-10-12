"""Shared metric readers preserve actual consequence ownership after substitution."""
import copy
import unittest

from test_contribution_players import M, fixture, inputs, BATTER, BASE
from test_run_construction_serving import run_fixture
from test_metric_suite_serving import bindings, G1


OTHER=BASE+'data/player/9'


def substituted(rows):
    result=copy.deepcopy(rows)
    for row in list(result):
        if row['kind']=='plate_appearance':
            result.append(dict(row,player=OTHER,act='other-batter-act'))
        elif row['kind']=='runner_movement':
            if row.get('contactPlay'):row['contactBatter']=row['batter']
            duplicate=dict(row,batter=OTHER)
            if row.get('metricOrigin')=='0' and not row.get('originCode'):
                duplicate.pop('metricOrigin',None)
            result.append(duplicate)
    return result


class ConsequenceActors(unittest.TestCase):
    def test_progress_and_contribution_use_contact_actor_without_reassigning_pa_credit(self):
        original=fixture(outs=0,runner_base=None,contact=True)
        changed=substituted(original)
        before=copy.deepcopy(changed)
        self.assertEqual(M.batting_progress_evidence(changed),M.batting_progress_evidence(original))
        self.assertEqual(inputs(changed),inputs(original))
        self.assertEqual(changed,before)
        # Statistical credit is intentionally not the contact actor.
        for row in changed:
            if row['kind']=='plate_appearance':
                row.update(creditedPlayer=OTHER,creditJudgment='cj',creditDecision='cd',creditRecord='cr')
        self.assertEqual(inputs(changed)['plateAppearances'][0]['player'],BATTER)

    def test_missing_or_conflicting_contact_owner_is_not_guessed(self):
        for fault in ('missing','conflicting'):
            rows=substituted(fixture(outs=0,runner_base=None,contact=True))
            for row in rows:
                if row['kind']!='runner_movement':continue
                if fault=='missing':row.pop('contactBatter',None)
                elif row['batter']==OTHER:row['contactBatter']=OTHER
            self.assertEqual(M.batting_progress_evidence(rows)['plateAppearances'],[])
            self.assertEqual(inputs(rows)['plateAppearances'],[])

    def test_award_recipient_identifies_the_actor_from_the_supported_home_entry(self):
        rows=fixture(outs=0,runner_base=None)
        rows[0]['paResultType']=BASE+'WalkProcess'
        rows[-1].update(hasSafeType='true',hasOutType='false',destinationBase='first',
            destinationCode='1B',safeJudgment='sj',safeDecision='sd',award='walk',awardRule='rule')
        changed=substituted(rows)
        self.assertEqual(M.batting_progress_evidence(changed),M.batting_progress_evidence(rows))
        self.assertEqual(inputs(changed),inputs(rows))

    def test_run_history_and_contributors_ignore_only_the_other_batter_join(self):
        rows=M.normalize_bindings(bindings(run_fixture(),[G1]),[G1])
        owners={r['entity']:r.get('player') or BASE+'data/player/'+r['entity'][-1]
                for r in rows if r['kind']=='plate_appearance'}
        for row in rows:
            if row['kind']=='plate_appearance':
                row.update(player=owners[row['entity']],recognizedBattingResult='true',paResultType=BASE+'SingleProcess')
            elif row['kind']=='runner_movement':
                row.update(batter=owners[row['plateAppearance']],contactPlay=row['plateAppearance']+'/contact')
        for metric in ('run-construction-depth','run-construction-breadth'):
            expected=M.run_construction_evidence(rows,metric_id=metric)
            self.assertTrue(expected['runs'],expected)
            self.assertEqual(M.run_construction_evidence(substituted(rows),metric_id=metric),expected)


if __name__=='__main__':unittest.main()
