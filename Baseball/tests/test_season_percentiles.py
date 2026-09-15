"""Exact season ranking against the retained canonical SPARQL peer kernel."""
import copy
from fractions import Fraction
import random
import unittest
from unittest.mock import patch

from test_metric_suite_serving import M


def canonical(entries, metric):
    inputs=[]
    for e in entries:
        score=M.fraction(e['score'])
        row=dict(key=e['key'],cohort=e.get('cohort','reference'),scoreN=score.numerator,scoreD=score.denominator)
        if metric=='paq-2.1':
            recovery=M.fraction(e['recovery'])
            row.update(recoveryN=recovery.numerator,recoveryD=recovery.denominator,depth=e['depth'])
        inputs.append(row)
    return {r['key']:M.ratio(r['numerator'],r['denominator'],components={
        'population':r['population'],'lower':r['lower'],'ties':r['ties']}) for r in M.run_kernel(metric,inputs)}


class SeasonPercentiles(unittest.TestCase):
    def test_matches_canonical_peer_queries_for_all_four_metrics(self):
        randomizer=random.Random(174)
        entries=[dict(key=str(i),cohort='a' if i%3 else 'b',
                      score=Fraction(randomizer.randrange(-5,6),randomizer.choice([3,4,9,36])),
                      recovery=Fraction(randomizer.randrange(4),3),depth=randomizer.randrange(1,5))
                 for i in range(18)]
        entries.extend([dict(entries[0],key='same'),dict(key='large',cohort='a',
            score=Fraction(10**70+1,10**70),recovery=0,depth=1)])
        for metric in ('paq-2','paq-a','recovery-quality','paq-2.1'):
            with self.subTest(metric=metric):
                expected=canonical(entries,metric)
                self.assertEqual(M.percentiles(entries,metric_id=metric,complete_population=True),expected)
                self.assertEqual(M.percentiles(list(reversed(entries)),metric_id=metric,complete_population=True),expected)

    def test_large_exact_fractions_are_not_rounded_into_a_tie(self):
        entries=[dict(key='lo',score=1),dict(key='hi',score=Fraction(10**100+1,10**100))]
        result=M.percentiles(entries,complete_population=True)
        self.assertEqual(result['lo']['value'],M.exact(0))
        self.assertEqual(result['hi']['value'],M.exact(100))

    def test_complete_population_and_known_small_cohorts_stay_distinct(self):
        entries=[dict(key='a',cohort='a',score=1),dict(key='b',cohort='b',score=1)]
        self.assertTrue(all(r['gaps']==['REFERENCE_POPULATION_INCOMPLETE'] for r in M.percentiles(entries).values()))
        complete=M.percentiles(entries,complete_population=True)
        self.assertTrue(all(r['gaps']==['EMPTY_DENOMINATOR'] for r in complete.values()))
        self.assertTrue(all(r['components']['population']==1 for r in complete.values()))
        self.assertEqual(M.percentiles([],complete_population=True),{})

    def test_tied_results_do_not_share_mutable_values_or_evidence(self):
        result=M.percentiles([dict(key='a',score=1),dict(key='b',score=1)],complete_population=True)
        before=copy.deepcopy(result['b'])
        result['a']['value']['numerator']='123'
        result['a']['components']['ties']=99
        result['a']['evidence'].append('changed')
        self.assertEqual(result['b'],before)

    def test_season_scale_does_not_execute_a_quadratic_peer_join(self):
        entries=[dict(key=str(i),score=Fraction(i%101-50,36)) for i in range(20200)]
        with patch.object(M,'run_kernel',side_effect=AssertionError('Quadratic peer query')):
            result=M.percentiles(entries,complete_population=True)
        self.assertEqual(len(result),20200)
        self.assertEqual(result['0']['components'],dict(population=20200,lower=0,ties=200))
        self.assertEqual(result['50']['value'],M.exact(50))
        self.assertEqual(result['100']['components'],dict(population=20200,lower=20000,ties=200))


if __name__=='__main__':unittest.main()
