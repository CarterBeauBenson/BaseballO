"""Accepted participant means, separate review populations, no source admission."""
import copy
import unittest

from test_metric_suite_serving import M,G1

P1='https://baseballontology.org/data/player/1'
P2='https://baseballontology.org/data/player/2'
GAME='https://baseballontology.org/data/game/101'
SCOPE=dict(startDate='2026-08-01',endDate='2026-08-02',gameSet='regular_season')


def people():
    return [dict(player=p,completeParticipation=True,dateScope=SCOPE,plateAppearances=0,
        teamGameExposure=[dict(game=GAME,team='team'),dict(game=GAME+'2',team='team')]) for p in (P1,P2)]


def defensive():
    acts=[dict(act='field',agent=P1,next=['throw']),dict(act='throw',agent=P1,next=['catch']),
          dict(act='catch',agent=P2,next=['tag']),dict(act='tag',agent=P2,next=[])]
    return [dict(graph=G1,game=GAME,resolution='first',completeResolution=True,orderComplete=True,
                 dateScope=SCOPE,acts=acts),
            dict(graph=G1,game=GAME,resolution='second',completeResolution=True,orderComplete=True,
                 dateScope=SCOPE,acts=[dict(act='catch2',agent=P1,next=[])])]


def review_rows():
    return [dict(graph=G1,game=GAME,review='traditional-'+str(i),mechanism='traditional-replay',
                 affectedPlayer=P1,challenger=P2,resolved=True,reversed=i<2,dateScope=SCOPE) for i in range(3)]+[
            dict(graph=G1,game=GAME,review='abs-'+str(i),mechanism='ball-strike-challenge',
                 affectedPlayer=P1,challenger=P2,resolved=True,reversed=i<3,dateScope=SCOPE) for i in range(4)]


class ParticipantSummaries(unittest.TestCase):
    def defense(self,metric,rows=None,**options):
        rows=defensive() if rows is None else rows
        return M.summarize_defensive_players(metric,rows,expected_observations=options.pop('expected',defensive()),
            participation=options.pop('participation',people()),date_scope=SCOPE,
            population_complete=options.pop('complete',True))

    def reviews(self,rows=None,metric='adjudication-volatility',**options):
        rows=review_rows() if rows is None else rows
        return M.summarize_review_players(metric,rows,expected_observations=options.pop('expected',rows),
            participation=options.pop('participation',people()),date_scope=SCOPE,
            complete_populations=options.pop('complete',dict.fromkeys(M.policies()['reviewDependenceMechanisms'],True)))

    def test_participating_defender_receives_one_observation_per_resolution(self):
        for metric,expected in [('resolution-depth',('5/2','4')),('defender-breadth',('3/2','2'))]:
            result=self.defense(metric);self.assertTrue(result['playerPopulationComplete'])
            first,second=result['playerResults']
            self.assertEqual(first['value'],M.exact(M.fraction(expected[0])))
            self.assertEqual(second['value'],M.exact(M.fraction(expected[1])))
            self.assertEqual(first['aggregate']['count'],2)
            self.assertEqual(second['aggregate']['count'],1)
            self.assertEqual(second['teamGames'],2)  # Includes the missed game.

    def test_distinct_repeated_throws_count_but_duplicate_typing_does_not(self):
        rows=defensive();acts=rows[0]['acts']
        acts[-1]['next']=['throw-again'];acts.append(dict(act='throw-again',agent=P2,next=[]))
        acts.append(copy.deepcopy(acts[1]))
        result=self.defense('resolution-depth',rows)
        self.assertEqual(result['playerResults'][1]['value'],M.exact(5))
        self.assertEqual(self.defense('defender-breadth',rows)['playerResults'][1]['value'],M.exact(2))

    def test_breadth_does_not_require_order_but_depth_does(self):
        rows=defensive();rows[0]['orderComplete']=False
        self.assertTrue(self.defense('defender-breadth',rows)['playerPopulationComplete'])
        self.assertEqual(self.defense('resolution-depth',rows)['playerSummaryGaps'],['DEFENSIVE_ORDER'])
        rows[0]['orderComplete']=True;rows[0]['acts'][-1]['next']=['field']
        self.assertEqual(self.defense('resolution-depth',rows)['playerSummaryGaps'],['CYCLIC_DEFENSIVE_ORDER'])

    def test_missing_census_or_participation_never_produces_partial_player_means(self):
        self.assertFalse(self.defense('resolution-depth',complete=False)['playerPopulationComplete'])
        self.assertFalse(self.defense('resolution-depth',defensive()[:-1])['playerPopulationComplete'])
        self.assertFalse(self.defense('resolution-depth',participation=people()[:1])['playerPopulationComplete'])
        rows=defensive();rows[0]['completeResolution']=False
        self.assertFalse(self.defense('defender-breadth',rows)['playerPopulationComplete'])

    def test_overturn_means_pool_decisions_separately_and_use_affected_player(self):
        result=self.reviews();self.assertTrue(result['playerPopulationComplete'])
        self.assertIsNone(result['value']);self.assertEqual(result['playerResults'],[])
        for mechanism,value,count in [('traditional-replay','2/3',3),('ball-strike-challenge','3/4',4)]:
            player,=result['byMechanism'][mechanism]['playerResults']
            self.assertEqual(player['player'],P1)
            self.assertEqual(player['value'],M.exact(M.fraction(value)))
            self.assertEqual(player['aggregate']['count'],count)
            self.assertEqual(player['mechanism'],mechanism)

    def test_independent_review_completeness_and_missing_attribution_are_visible(self):
        result=self.reviews(complete={'traditional-replay':True})
        self.assertTrue(result['byMechanism']['traditional-replay']['playerPopulationComplete'])
        self.assertFalse(result['byMechanism']['ball-strike-challenge']['playerPopulationComplete'])
        rows=review_rows();rows[0].pop('affectedPlayer')
        self.assertEqual(self.reviews(rows)['byMechanism']['traditional-replay']['playerSummaryGaps'],['AFFECTED_PLAYER_EVIDENCE'])
        rows=review_rows();rows[0]['mechanism']='MJ'
        self.assertEqual(self.reviews(rows)['playerSummaryGaps'],['REVIEW_MECHANISM_UNKNOWN'])
        self.assertFalse(self.reviews(participation=people()[1:])['playerPopulationComplete'])

    def test_eligible_never_reviewed_outcomes_remain_in_dependence_denominator(self):
        rows=[dict(graph=G1,game=GAME,outcome='decision-'+str(i),mechanism='ball-strike-challenge',
            affectedPlayer=P1,eligible=i!=3,reviewDependent=i==0,dateScope=SCOPE) for i in range(4)]
        rows[3].pop('affectedPlayer');rows[3].pop('reviewDependent')
        result=self.reviews(rows,metric='review-dependence-rate')
        group=result['byMechanism']['ball-strike-challenge'];player,=group['playerResults']
        self.assertEqual(player['value'],M.exact(M.fraction('1/3')))
        rows[2]['reviewDependent']=None
        self.assertFalse(self.reviews(rows,metric='review-dependence-rate')['byMechanism']['ball-strike-challenge']['playerPopulationComplete'])
        rows[2]['reviewDependent']=False;rows[2]['eligible']=None
        self.assertEqual(self.reviews(rows,metric='review-dependence-rate')['byMechanism']['ball-strike-challenge']['playerSummaryGaps'],['OUTCOME_POPULATION'])


if __name__=='__main__':unittest.main()
