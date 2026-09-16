"""Numerical PAQ-2.1 joining without reducing its season reference to the display."""
import copy
import unittest
from test_nonbatting_player_summaries import M,P1,P2,GAME,G1,SCOPE,people


def reference():
    return [dict(graph=G1,game=GAME,plateAppearance='pa-'+str(i),player=P1,season=2026,
        score=M.exact(1),recovery=M.exact(50),depth=i+1,twoStrikeEligible=True,defensiveApplicable=True) for i in range(3)]


class Paq21PlayerMeans(unittest.TestCase):
    def run_score(self,rows=None,selected=None,expected=None,**options):
        rows=reference() if rows is None else rows
        participants=people();participants[0]['plateAppearances']=3
        return M.summarize_paq21_players(rows,expected_reference=rows if expected is None else expected,
            selected_observations=rows[1:] if selected is None else selected,participation=participants,
            date_scope=SCOPE,complete_reference=options.get('complete',True))

    def test_season_ranks_before_selected_mean_and_retains_official_qualification_count(self):
        result=self.run_score();self.assertTrue(result['playerPopulationComplete'])
        player,=result['playerResults']
        self.assertEqual(player['value'],M.exact(75))
        self.assertEqual(player['aggregate'],dict(kind='mean',sum=M.exact(150),count=2))
        self.assertEqual(player['plateAppearances'],3)
        self.assertEqual(player['teamGames'],2)

    def test_known_inapplicability_is_excluded_but_unknown_or_missing_dimension_blocks(self):
        rows=reference();rows[0]['twoStrikeEligible']=False;rows[0]['defensiveApplicable']=None
        rows[0].pop('depth');rows[0].pop('recovery')
        result=self.run_score(rows)
        self.assertEqual(result['playerResults'][0]['value'],M.exact(50))
        rows[0]['twoStrikeEligible']=True
        self.assertFalse(self.run_score(rows)['playerPopulationComplete'])
        rows[0]['defensiveApplicable']=True
        self.assertEqual(self.run_score(rows)['playerSummaryGaps'],['MISSING_LEXICOGRAPHIC_DIMENSION'])

    def test_missing_reference_member_or_unverified_reference_never_ranks(self):
        self.assertFalse(self.run_score(reference()[1:],expected=reference())['playerPopulationComplete'])
        self.assertFalse(self.run_score(complete=False)['playerPopulationComplete'])
        extra=copy.deepcopy(reference()[0]);extra['plateAppearance']='not-in-reference'
        self.assertEqual(self.run_score(selected=[extra])['playerSummaryGaps'],['PAQ_SELECTED_PA_COVERAGE'])

    def test_no_applicable_selected_pa_has_no_invented_zero(self):
        rows=reference();rows[0]['twoStrikeEligible']=False
        result=self.run_score(rows,selected=rows[:1])
        self.assertTrue(result['playerPopulationComplete'])
        self.assertEqual(result['playerResults'],[])
        self.assertEqual(result['gaps'],['EMPTY_DENOMINATOR'])


if __name__=='__main__':unittest.main()
