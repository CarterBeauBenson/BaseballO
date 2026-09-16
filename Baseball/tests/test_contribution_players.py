"""Accepted contribution arithmetic, complete denominators and fail-closed scope."""
import copy
import unittest
from fractions import Fraction

from test_metric_suite_serving import M,G1
from test_batting_progress_players import PROOF,SCOPE

GAME='https://baseballontology.org/data/game/101'
BATTER='https://baseballontology.org/data/player/1'
RUNNER='https://baseballontology.org/data/player/2'
BASE='https://baseballontology.org/'


def fixture(outs=2, runner_base=3, contact=False):
    pa=GAME+'/plate-appearance/0'
    rows=[dict(kind='plate_appearance',graph=G1,game=GAME,entity=pa,player=BATTER,
        paHalf=GAME+'/half',paInterval=pa+'/interval',paStartInstant=pa+'/start',paOutsBefore=str(outs),
        recognizedBattingResult='true',paResultType=BASE+('BattedBallOutProcess' if contact else 'StrikeoutProcess'))]
    if runner_base:
        rows.append(dict(kind='runner_location',graph=G1,game=GAME,entity=pa+'/stasis',stasis=pa+'/stasis',
            runner=RUNNER,plateAppearance=pa,occupiedBase=GAME+'/base/'+str(runner_base),occupiedBaseCode=str(runner_base)+'B',
            baseSite=GAME+'/site/'+str(runner_base),stasisInterval=pa+'/stasis/interval',
            stasisFirstInstant=pa+'/start',paFirstInstant=pa+'/start',paInterval=pa+'/interval'))
    row=dict(kind='runner_movement',graph=G1,game=GAME,entity=pa+'/out',resolution=pa+'/out',plateAppearance=pa,
        runner=BATTER,batter=BATTER,act=pa+'/running',episode=pa+'/episode',record=pa+'/record',metricOrigin='0',
        hasSafeType='false',hasOutType='true',hasRunType='false')
    if contact:row['contactPlay']=pa+'/contact'
    rows.append(row)
    return rows


def inputs(rows,**changes):
    args=dict(graph=G1,batting_admission=PROOF,runner_resolution_admission=PROOF,runner_boundary_admission=PROOF)
    args.update(changes)
    return M.contribution_game_inputs(rows,**args)


def qualification(result):
    return dict(officialPlateAppearanceCreditVerified=True,teamGameExposureVerified=True,
        expectedObservations=[{k:p[k] for k in ('graph','plateAppearance','player')} for p in result['plateAppearances']],
        participation=[dict(player=BATTER,plateAppearances=len(result['plateAppearances']),teamGameExposure=[dict(game=GAME,team='team')])])


class ContributionPlayers(unittest.TestCase):
    def test_third_out_strands_runner_without_invented_destruction(self):
        result=inputs(fixture())
        self.assertTrue(result['complete'],result)
        pa,=result['plateAppearances']
        self.assertEqual(M.fraction(pa['score']['value']),Fraction(-5,4))
        self.assertEqual(pa['score']['components'],dict(progress=M.exact(0),destruction=M.exact(Fraction(1,4)),erosion=M.exact(1)))
        self.assertEqual(pa['existingRunnerOuts'],0)
        stranded,=[p for p in pa['participants'] if p['participant']==RUNNER]
        self.assertEqual(stranded['terminal'],'stranded')
        self.assertFalse(stranded['creditOut'])
        expected={'tfs':Fraction(-5,4),'rally-kill-rate':0,'rally-kill-severity':0,'opportunity-erosion':1}
        for metric,value in expected.items():
            score=M.contribution_players(metric,[result],qualification=qualification(result),date_scope=SCOPE)
            self.assertTrue(score['playerPopulationComplete'])
            self.assertEqual(M.fraction(score['playerResults'][0]['value']),value)

    def test_double_play_counts_one_affected_pa_and_weights_runner_origin(self):
        rows=fixture(outs=1,runner_base=1,contact=True);batter=rows[-1];pa=batter['plateAppearance']
        rows.append(dict(batter,entity=pa+'/runner-out',resolution=pa+'/runner-out',runner=RUNNER,metricOrigin='1',
            act=pa+'/runner-act',episode=pa+'/runner-episode',originDesignation=pa+'/origin',
            originBase=GAME+'/base/1',originCode='1B',originRecord=pa+'/record'))
        result=inputs(rows);self.assertTrue(result['complete'],result)
        item,=result['plateAppearances']
        self.assertEqual(item['attributedOuts'],2)
        self.assertEqual(M.fraction(item['score']['value']),Fraction(-7,12))
        self.assertEqual(M.fraction(item['existingDestruction']),Fraction(1,3))
        for metric,value in [('rally-kill-rate',1),('rally-kill-severity',Fraction(1,3))]:
            score=M.contribution_players(metric,[result],qualification=qualification(result),date_scope=SCOPE)
            self.assertEqual(M.fraction(score['value']),value)

    def test_no_runner_denominator_is_known_inapplicable_not_zero_rate(self):
        result=inputs(fixture(outs=0,runner_base=None))
        self.assertTrue(result['complete'])
        score=M.contribution_players('rally-kill-rate',[result],qualification=qualification(result),date_scope=SCOPE)
        self.assertTrue(score['playerPopulationComplete'])
        self.assertEqual(score['playerResults'],[])
        self.assertEqual(score['gaps'],['EMPTY_DENOMINATOR'])

    def test_missing_proof_mixed_out_ownership_and_boundary_conflicts_withhold(self):
        for key in ('batting_admission','runner_resolution_admission','runner_boundary_admission'):
            self.assertFalse(inputs(fixture(),**{key:{'status':'withheld'}})['complete'])
        for fault in ('out','stasis','independent','origin'):
            rows=fixture(outs=1,runner_base=1,contact=True)
            if fault=='out':rows[0]['paOutsBefore']='3'
            elif fault=='stasis':rows[1]['stasisFirstInstant']='other'
            else:
                row=dict(rows[-1],runner=RUNNER,entity='runner-out',resolution='runner-out',act='runner-act',episode='runner-episode',
                    originDesignation='origin',originBase='base',originCode='2B' if fault=='origin' else '1B')
                if fault=='independent':row.pop('contactPlay');row['independentStealAct']=row['act']
                rows.append(row)
            self.assertFalse(inputs(rows)['complete'],fault)

    def test_all_selected_members_and_schedule_required(self):
        result=inputs(fixture());q=qualification(result)
        for field in ('officialPlateAppearanceCreditVerified','teamGameExposureVerified'):
            changed=dict(q,**{field:False})
            self.assertFalse(M.contribution_players('tfs',[result],qualification=changed,date_scope=SCOPE)['playerPopulationComplete'])
        q['expectedObservations'].append(dict(graph=G1,plateAppearance='omitted',player=BATTER))
        self.assertFalse(M.contribution_players('tfs',[result],qualification=q,date_scope=SCOPE)['playerPopulationComplete'])
        self.assertFalse(M.contribution_players('tfs',[result,result],qualification=qualification(result),date_scope=SCOPE)['playerPopulationComplete'])


if __name__=='__main__':unittest.main()
