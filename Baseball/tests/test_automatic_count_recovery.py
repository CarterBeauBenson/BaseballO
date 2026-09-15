"""Recovery counts delivered nonterminal pitches after two strikes, not awards."""
from test_graph_native_metric_suite import M, value
import unittest

class AutomaticCountRecovery(unittest.TestCase):
    def test_automatic_second_strike_qualifies_without_counting_as_pitch(self):
        rows=[dict(pitch='p1',strikesAfter=1,terminal=False),
              dict(countAward='a1',awardKind='strike',strikesAfter=2,terminal=False),
              dict(countAward='a2',awardKind='ball',strikesAfter=2,terminal=False),
              dict(pitch='p2',strikesAfter=2,terminal=False),
              dict(pitch='p3',strikesAfter=3,terminal=True)]
        result=M.recovery_steps(rows)
        self.assertEqual(value(result),1)
        self.assertEqual(set(result['evidence']),{'p1','p2','p3','a1','a2'})

    def test_terminal_automatic_strike_contributes_no_pitch(self):
        rows=[dict(pitch='p1',strikesAfter=1,terminal=False),dict(pitch='p2',strikesAfter=2,terminal=False),
              dict(countAward='a1',awardKind='strike',strikesAfter=3,terminal=True)]
        self.assertEqual(value(M.recovery_steps(rows)),0)

    def test_unknown_or_inconsistent_awards_cannot_supply_count_history(self):
        for award in [dict(countAward='a'),dict(countAward='a',awardKind='strike',strikesAfter=2),
                      dict(countAward='a',awardKind='ball',strikesAfter=1),dict(countAward='a',pitch='p',awardKind='ball',strikesAfter=0)]:
            with self.assertRaises(M.EvidenceError): M.recovery_steps([dict(award,terminal=True)])

if __name__=='__main__': unittest.main()
