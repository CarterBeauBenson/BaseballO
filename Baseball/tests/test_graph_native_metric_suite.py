import importlib.util
from fractions import Fraction as F
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('metric_suite', ROOT/'serving/metric_suite.py')
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


def value(result):
    assert result['status']=='available', result
    return M.fraction(result['value'])


class MetricCalculations(unittest.TestCase):
    def calc(self, id, rows):
        return M.calculate(id, [dict(key='scope', **r) for r in rows])

    def test_all_twenty_kernels_parse(self):
        self.assertEqual(len(M.catalog()['metrics']),20)
        for entry in M.catalog()['metrics']:
            with self.subTest(metric=entry['id']):
                M.run_kernel(entry['id'], [])

    def test_fifteen_accepted_tfs_examples(self):
        spec=importlib.util.spec_from_file_location('examples',ROOT/'tests/test_tfs_policy_arithmetic.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for name,(outs,delta,participants,expected) in module.EXAMPLES.items():
            with self.subTest(example=name):
                facts=[dict(participant=str(i),start=s,end=e,terminal=t,creditProgress=p,creditOut=o,
                            evidence=['urn:test:resolution:'+str(i)]) for i,(s,e,t,p,o) in enumerate(participants)]
                result=M.trajectories(facts,outs,delta)
                self.assertEqual(value(result),F(expected[3]))
                self.assertEqual([M.fraction(result['components'][k]) for k in ['progress','destruction','erosion']],
                                 [F(v) for v in expected[:3]])

    def test_tfs_unknown_and_inconsistent_outs(self):
        self.assertEqual(M.trajectories([],0,0)['status'],'unavailable')
        unknown=[dict(participant='r',start=1,end=None,terminal='unknown',creditProgress=False,creditOut=False)]
        self.assertEqual(M.trajectories(unknown,0,0)['status'],'unavailable')
        with self.assertRaises(M.EvidenceError):
            M.trajectories([dict(participant='r',start=1,end=None,terminal='out',creditProgress=False,creditOut=True)],0,0)

    def test_exact_percentile_ties_and_incomplete_population(self):
        rows=[dict(key='a',score='-1/4'),dict(key='b',score='1/3'),dict(key='c',score='2/6'),dict(key='d',score='1/2')]
        result=M.percentiles(rows,complete_population=True)
        self.assertEqual([value(result[k]) for k in ['a','b','c','d']],[0,50,50,100])
        self.assertTrue(all(v['status']=='unavailable' for v in M.percentiles(rows).values()))
        single=M.percentiles(rows[:1],complete_population=True)['a']
        self.assertEqual(single['gaps'],['EMPTY_DENOMINATOR'])

    def test_paq_a_separate_cohorts_and_rational_order(self):
        rows=[dict(key='a',cohort='0:empty',score='1/3'),dict(key='b',cohort='0:empty',score='333333333333333334/1000000000000000000'),
              dict(key='c',cohort='1:third',score='-3/4'),dict(key='d',cohort='1:third',score='-1/4')]
        result=M.percentiles(rows,metric_id='paq-a',complete_population=True)
        self.assertEqual([value(result[k]) for k in ['a','b','c','d']],[0,100,0,100])

    def test_lexicographic_recovery_never_rescues_worse_tfs(self):
        rows=[dict(key='bad',score='-3/4',recovery=100,depth=20),
              dict(key='good',score='3/2',recovery=0,depth=1),
              dict(key='tie',score='3/2',recovery=0,depth=2)]
        result=M.percentiles(rows,metric_id='paq-2.1',complete_population=True)
        self.assertEqual([value(result[k]) for k in ['bad','good','tie']],[0,50,100])

    def test_player_mean_median_quartiles_and_distribution(self):
        result=M.player_paq([M.available(v) for v in [0,25,50,100]])
        self.assertEqual(value(result),F(175,4))
        self.assertEqual(M.fraction(result['components']['median']),F(75,2))
        self.assertEqual(M.fraction(result['components']['topQuartileRate']),F(1,4))
        self.assertEqual(M.fraction(result['components']['bottomQuartileRate']),F(1,2))

    def test_reach_hidden_help_rally_and_erosion(self):
        self.assertEqual(value(self.calc('offensive-reach',[dict(participant='b',progress36=18),dict(participant='r',progress36=36)])),2)
        hh=[dict(pa='a',batterProgress36=0,otherProgress36=18),dict(pa='b',batterProgress36=0,otherProgress36=0),dict(pa='c',batterProgress36=9,otherProgress36=0)]
        self.assertEqual(value(self.calc('hidden-help-rate',hh)),F(1,2))
        self.assertEqual(value(self.calc('rally-kill-rate',[dict(pa='a',runnerOnBase=True,existingRunnerOuts=1),dict(pa='b',runnerOnBase=True,existingRunnerOuts=0),dict(pa='c',runnerOnBase=False,existingRunnerOuts=0)])),F(1,2))
        self.assertEqual(value(self.calc('rally-kill-severity',[dict(pa='a',runnerOnBase=True,existingDestruction36=12),dict(pa='b',runnerOnBase=True,existingDestruction36=0)])),F(1,6))
        self.assertEqual(value(self.calc('opportunity-erosion',[dict(pa='a',erosion36=18),dict(pa='b',erosion36=12)])),F(5,12))

    def test_empty_rate_damage_and_independent_damage(self):
        self.assertEqual(value(self.calc('empty-game-rate',[dict(game='a',plateAppearances=1,positiveEpisodes=0),dict(game='b',plateAppearances=1,positiveEpisodes=2),dict(game='c',plateAppearances=0,positiveEpisodes=0)])),F(1,2))
        self.assertEqual(value(self.calc('empty-game-damage',[dict(game='g',episode='a',empty=True,score36=-9),dict(game='g',episode='b',empty=True,score36=-12),dict(game='g',episode='c',empty=True,score36=0)])),F(7,12))
        result=M.empty_game_damage([M.available(F(-1,4))],[M.available(F(-1,3))],empty=True,complete=True)
        self.assertEqual(value(result),F(7,12))
        self.assertEqual(M.empty_game_damage([],[],empty=None,complete=False)['status'],'unavailable')

    def test_diversity_and_breadth_are_not_value(self):
        rows=[dict(play=str(i),channel=c) for i,c in enumerate(['batter_self','batter_other','runner_self'])]
        result=self.calc('contribution-path-diversity',rows)
        self.assertAlmostEqual(result['approximateValue'],1)
        self.assertIsNone(result['value'])
        self.assertEqual(result['components']['pathBreadth'],3)
        one=self.calc('contribution-path-diversity',rows[:1])
        self.assertAlmostEqual(one['approximateValue'],0)

    def test_recovery_counts_each_later_nonterminal_pitch_once(self):
        pitches=[dict(pitch=str(i),strikesAfter=s,terminal=i==5) for i,s in enumerate([0,1,2,2,2,3])]
        self.assertEqual(value(M.recovery_steps(pitches)),2)
        no_two=[dict(pitch='x',strikesAfter=0,terminal=True)]
        self.assertEqual(M.recovery_steps(no_two)['gaps'],['NOT_TWO_STRIKE_ELIGIBLE'])
        ranks=M.percentiles([dict(key='a',score=0),dict(key='b',score=2)],metric_id='recovery-quality',complete_population=True)
        self.assertEqual(value(ranks['b']),100)

    def test_defensive_graph_paths_agents_and_cycles(self):
        rows=[dict(act='field',next='throw',agent='a'),dict(act='throw',next='catch',agent='a'),dict(act='catch',next=None,agent='b')]
        self.assertEqual(value(self.calc('resolution-depth',rows)),3)
        self.assertEqual(value(self.calc('defender-breadth',[dict(act=r['act'],agent=r['agent']) for r in rows])),2)
        rows[-1]['next']='field'
        self.assertEqual(self.calc('resolution-depth',rows)['gaps'],['CYCLIC_DEFENSIVE_ORDER'])
        self.assertEqual(value(M.defensive_depth([dict(act='catch',agent='a',next=[])])),1)

    def test_run_construction_and_roles(self):
        self.assertEqual(value(self.calc('run-construction-depth',[dict(episode=str(i),changesState=True) for i in range(4)])),4)
        self.assertEqual(value(self.calc('run-construction-breadth',[dict(episode=str(i),supporter=s) for i,s in enumerate(['a','a','b','c'])])),3)
        self.assertEqual(value(self.calc('role-realization-breadth',[dict(act='a',roleType='https://baseballontology.org/BatterRole'),dict(act='b',roleType='https://baseballontology.org/BatterRole'),dict(act='c',roleType='https://baseballontology.org/BaserunnerRole')])),2)

    def test_review_rates_count_entities_once_and_handle_empty_denominators(self):
        rows=[dict(review='a',resolved=True,reversed=True),dict(review='b',resolved=True,reversed=False),dict(review='c',resolved=False,reversed=False)]
        self.assertEqual(value(self.calc('adjudication-volatility',rows+[rows[0]])),F(1,2))
        self.assertEqual(value(self.calc('review-dependence-rate',[dict(outcome='a',eligible=True,reviewed=True),dict(outcome='b',eligible=True,reviewed=False)])),F(1,2))
        self.assertEqual(self.calc('adjudication-volatility',rows[-1:])['status'],'unavailable')

    def test_unknown_conflicting_or_float_input_is_not_zero(self):
        with self.assertRaises(M.EvidenceError):
            self.calc('offensive-reach',[dict(participant='r',progress36=None)])
        with self.assertRaises(M.EvidenceError):
            self.calc('offensive-reach',[dict(participant='r',progress36=1),dict(participant='r',progress36=2)])
        with self.assertRaises(M.EvidenceError):
            self.calc('offensive-reach',[dict(participant='r',progress36=0.0)])
        with self.assertRaises(M.EvidenceError):
            self.calc('contribution-path-diversity',[dict(play='e',channel='unknown')])

    def test_complete_aggregates_and_explicit_cohort_and_count_requirements(self):
        summary=M.summarize([M.available(n) for n in [0,1,2,3]],threshold=2)
        self.assertEqual(value(summary),F(3,2))
        self.assertEqual(M.fraction(summary['components']['atOrAboveThresholdRate']),F(1,2))
        self.assertEqual(M.summarize([M.available(1),M.unavailable('unknown')])['status'],'unavailable')
        self.assertEqual(M.percentiles([dict(key='a',score=1)],metric_id='paq-a',complete_population=True)['a']['gaps'],['PAQ_A_STATE'])
        with self.assertRaises(M.EvidenceError):
            M.recovery_steps([dict(pitch='a',strikesAfter=2,terminal=False),dict(pitch='b',strikesAfter=1,terminal=True)])

    def test_actual_end_state_passed_ball_has_no_batter_progress_or_survivor_erosion(self):
        rows = [dict(participant='b',start=0,end=None,terminal='out',creditProgress=False,creditOut=True),
                dict(participant='r',start=3,end=4,terminal='scored',creditProgress=False,creditOut=False)]
        result = M.trajectories(rows,1,1)
        self.assertEqual(value(result),F(-1,4))
        self.assertEqual(M.fraction(result['components']['progress']),0)
        self.assertEqual(M.fraction(result['components']['erosion']),0)

    def test_independent_runner_damage_includes_surviving_teammate(self):
        rows = [dict(participant='caught',start=1,end=None,terminal='out',creditOut=True),
                dict(participant='third',start=3,end=3,terminal='safe',creditOut=False)]
        result = M.independent_runner_damage(rows,0,1)
        self.assertEqual(value(result),F(2,3))
        self.assertEqual(M.fraction(result['components']['destruction']),F(1,3))
        self.assertEqual(M.fraction(result['components']['erosion']),F(1,3))

    def test_zero_pa_runner_is_not_an_empty_game(self):
        self.assertFalse(M.empty_game_eligible(0))
        self.assertTrue(M.empty_game_eligible(1))
        self.assertIsNone(M.empty_game_eligible(None))
        result = self.calc('empty-game-rate',[dict(game='g',plateAppearances=0,positiveEpisodes=0)])
        self.assertEqual(result['gaps'],['EMPTY_DENOMINATOR'])
        with self.assertRaises(M.EvidenceError):
            self.calc('empty-game-rate',[dict(game='g',plateAppearances=None,positiveEpisodes=0)])
        self.assertTrue(M.policies()['zeroPaRunnerEligibleForBaserunning'])

    def test_cpd_counts_a_shared_play_once_per_channel(self):
        rows = [dict(play='single',channel='batter_other'),dict(play='single',channel='batter_other'),
                dict(play='single',channel='batter_self'),dict(play='steal',channel='runner_self')]
        self.assertEqual(self.calc('contribution-path-diversity',rows)['components']['channelCounts'],[1,1,1])

    def test_four_acts_two_agents_and_two_run_contributors(self):
        rows = [dict(act='field',next='throw',agent='a'),dict(act='throw',next='catch',agent='a'),
                dict(act='catch',next='tag',agent='b'),dict(act='tag',next=None,agent='b')]
        self.assertEqual(value(self.calc('resolution-depth',rows)),4)
        self.assertEqual(value(self.calc('defender-breadth',[dict(act=r['act'],agent=r['agent']) for r in rows])),2)
        support = [dict(episode='single',supporter='scorer'),dict(episode='steal',supporter='scorer'),
                   dict(episode='double',supporter='teammate')]
        self.assertEqual(value(self.calc('run-construction-breadth',support)),2)

    def test_role_breadth_counts_only_the_four_realized_kinds(self):
        rows = [dict(act=str(i),roleType=role) for i,role in enumerate(M.policies()['countedRoleTypes'])]
        rows += [dict(act='parent',roleType='https://baseballontology.org/BaseballPlayerRole'),rows[0]]
        self.assertEqual(value(self.calc('role-realization-breadth',rows)),4)

    def test_paq21_distinguishes_inapplicable_from_missing(self):
        rows = [dict(key=k,score=s,recovery=10,depth=2,twoStrikeEligible=True,defensiveApplicable=True)
                for k,s in [('low',0),('high',1)]]
        excluded = dict(key='no-two-strikes',score=2,twoStrikeEligible=False,defensiveApplicable=None)
        result = M.paq21_population(rows+[excluded],complete_population=True)
        self.assertEqual([value(result[k]) for k in ['low','high']],[0,100])
        self.assertEqual(result['no-two-strikes']['gaps'],['PAQ21_NOT_APPLICABLE'])
        ordinary = M.percentiles([dict(key=r['key'],score=r['score']) for r in rows+[excluded]],complete_population=True)
        self.assertEqual(value(ordinary['no-two-strikes']),100)
        unknown = dict(excluded,key='unknown',twoStrikeEligible=None)
        result = M.paq21_population(rows+[unknown],complete_population=True)
        self.assertEqual(result['unknown']['gaps'],['PAQ21_ELIGIBILITY_UNKNOWN'])
        self.assertEqual(result['low']['gaps'],['REFERENCE_POPULATION_INCOMPLETE'])
        rows[1]['depth'] = None
        result = M.paq21_population(rows,complete_population=True)
        self.assertEqual(result['low']['gaps'],['MISSING_LEXICOGRAPHIC_DIMENSION'])


if __name__=='__main__': unittest.main()
