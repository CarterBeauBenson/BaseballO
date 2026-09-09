"""Exact accepted choices; no source continuity or completeness is inferred."""
import unittest
from fractions import Fraction as F
from test_metric_suite_serving import M


def advance(start, end):
    return dict(participant='runner', start=start, end=end,
                terminal='scored' if end == 4 else 'safe', creditProgress=True, creditOut=False)


class September9Answers(unittest.TestCase):
    def test_exact_additive_running_gains_and_separate_net_components(self):
        results = [M.independent_runner_contribution([advance(a,b)],0,0)
                   for a,b in [(1,2),(2,3),(3,4),(1,3),(1,4)]]
        self.assertEqual([M.fraction(r['value']) for r in results], [F(1,3),F(1,2),1,F(5,6),F(11,6)])
        self.assertEqual(sum(M.fraction(r['value']) for r in results[:3]), M.fraction(results[-1]['value']))
        for result in results:
            self.assertEqual(result['components']['damage'], M.exact(0))
            self.assertEqual(result['components']['advancement'], result['components']['net'])
        rows=[dict(participant='caught',start=1,end=None,terminal='out',creditOut=True,creditProgress=True),
              dict(participant='third',start=3,end=3,terminal='safe',creditOut=False,creditProgress=False)]
        result=M.independent_runner_contribution(rows,0,1)
        self.assertEqual(result['components']['advancement'],M.exact(0))
        self.assertEqual(result['components']['damage'],M.exact(F(2,3)))
        self.assertEqual(result['components']['net'],M.exact(F(-2,3)))

    def test_running_helper_does_not_join_segments_or_assume_credit(self):
        with self.assertRaises(M.EvidenceError):
            M.independent_runner_contribution([advance(1,2),advance(2,3)],0,0)
        with self.assertRaises(M.EvidenceError):
            M.independent_runner_contribution([dict(advance(1,2),creditProgress=None)],0,0)
        with self.assertRaises(M.EvidenceError):
            M.independent_runner_contribution([advance(0,1)],0,0)
        result=M.independent_runner_contribution([dict(advance(1,2),creditProgress=False)],0,0)
        self.assertEqual(result['value'],M.exact(0))

    def test_paq_a_uses_immediate_state_and_requires_the_whole_cohort(self):
        def entry(key, score, bases):
            return dict(key=key,score=score,referencePopulation='MLB-2026-cutoff',
                        comparisonState=dict(boundary='immediately-before-batter-consequence',
                                             occupiedBases=bases,outs=0,evidence=['urn:boundary:'+key]))
        # The PA that began on first joins the second-base cohort after the steal.
        rows=[entry('steal-then-single',1,[2]),entry('second-base-peer',0,[2]),entry('first-base-peer',2,[1])]
        result=M.paq_a_population(rows,complete_population=True)
        self.assertEqual(result['steal-then-single']['value'],M.exact(100))
        self.assertEqual(result['second-base-peer']['value'],M.exact(0))
        self.assertEqual(result['first-base-peer']['gaps'],['EMPTY_DENOMINATOR'])
        rows[0]['comparisonState']['boundary']='plate-appearance-start'
        self.assertTrue(all(r['gaps']==['PAQ_A_STATE'] for r in M.paq_a_population(rows,complete_population=True).values()))

    def test_review_denominators_include_unreviewed_and_separate_mechanisms(self):
        replay, challenge=M.policies()['reviewDependenceMechanisms']
        rows=[dict(mechanism=m,outcome=str(i),eligible=True,reviewDependent=(i==0))
              for m,n in [(replay,2),(challenge,3)] for i in range(n)]
        rows.append(dict(mechanism=replay,outcome='ineligible',eligible=False,reviewDependent=None))
        complete={replay:True,challenge:True}
        result=M.review_dependence_by_mechanism(rows,complete_populations=complete)
        self.assertEqual(result[replay]['value'],M.exact(F(1,2)))
        self.assertEqual(result[challenge]['value'],M.exact(F(1,3)))
        rows[0]['reviewDependent']=None
        result=M.review_dependence_by_mechanism(rows,complete_populations=complete)
        self.assertEqual(result[replay]['gaps'],['OPERATIVE_REVIEW'])
        self.assertEqual(result[challenge]['value'],M.exact(F(1,3)))
        rows[0]['eligible']=None
        self.assertEqual(M.review_dependence_by_mechanism(rows,complete_populations=complete)[replay]['gaps'],['OUTCOME_POPULATION'])
        self.assertEqual(M.review_dependence_by_mechanism([],complete_populations=complete)[replay]['gaps'],['EMPTY_DENOMINATOR'])
        self.assertEqual(M.review_dependence_by_mechanism(rows,complete_populations={})[challenge]['gaps'],['OUTCOME_POPULATION'])


if __name__=='__main__':
    unittest.main()
