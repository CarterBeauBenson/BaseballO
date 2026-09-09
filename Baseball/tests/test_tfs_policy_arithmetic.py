"""SPARQL arithmetic against hand-reviewed examples; not graph admission tests."""
import unittest
from fractions import Fraction
from pathlib import Path

from rdflib import Graph, Literal

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / 'tests/fixtures/metrics/tfs-policy-arithmetic.rq'

# Participant tuples: original path start, relevant end, terminal outcome,
# batter progress credit, batter out attribution. An out has no safe end;
# UNDEF verifies that its absent end never suppresses its destruction.
# Expected tuples: positive progress, destruction, erosion, signed total.
# These are hypothetical complete cases. No JSON feed is interpreted here.
EXAMPLES = {
    'bases_empty_double': (0, 0, [(0, 2, 'safe', True, False)], ('1/2', '0', '0', '1/2')),
    'double_scores_second': (0, 0, [(0, 2, 'safe', True, False), (2, 4, 'scored', True, False)], ('3/2', '0', '0', '3/2')),
    'bases_loaded_home_run': (0, 0, [(s, 4, 'scored', True, False) for s in range(4)], ('4', '0', '0', '4')),
    'bases_empty_out': (0, 1, [(0, None, 'out', False, True)], ('0', '1/4', '0', '-1/4')),
    'third_one_out_strikeout': (1, 1, [(0, None, 'out', False, True), (3, 3, 'safe', False, False)], ('0', '1/4', '1/2', '-3/4')),
    'third_two_out_strikeout': (2, 1, [(0, None, 'out', False, True), (3, 3, 'stranded', False, False)], ('0', '1/4', '1', '-5/4')),
    'sacrifice_fly': (1, 1, [(0, None, 'out', False, True), (3, 4, 'scored', True, False)], ('1', '1/4', '0', '3/4')),
    'groundout_advances_second': (0, 1, [(0, None, 'out', False, True), (2, 3, 'safe', True, False)], ('1/2', '1/4', '1/3', '-1/12')),
    'fc_progress_excluded': (0, 1, [(1, None, 'out', False, True), (0, 1, 'safe', False, False)], ('0', '1/3', '1/9', '-4/9')),
    'grounded_double_play': (0, 2, [(0, None, 'out', False, True), (1, None, 'out', False, True)], ('0', '7/12', '0', '-7/12')),
    'continuous_first_second_out': (0, 1, [(1, None, 'out', False, True)], ('0', '1/3', '0', '-1/3')),
    'independent_first_to_second': (1, 1, [(0, None, 'out', False, True), (1, 2, 'safe', False, False)], ('0', '1/4', '1/4', '-1/2')),
    'independent_score_and_third': (1, 1, [(0, None, 'out', False, True), (2, 4, 'scored', False, False), (1, 3, 'safe', False, False)], ('0', '1/4', '1/2', '-3/4')),
    'bases_empty_error': (0, 0, [(0, 1, 'safe', False, False)], ('0', '0', '0', '0')),
    'second_third_stranded': (2, 1, [(0, None, 'out', False, True), (2, 2, 'stranded', False, False), (3, 3, 'stranded', False, False)], ('0', '1/4', '3/2', '-7/4')),
}


class TfsPolicyArithmeticTests(unittest.TestCase):
    def test_accepted_examples_have_exact_components_and_total(self):
        rows = []
        for name, (outs, delta, participants, _) in EXAMPLES.items():
            for start, end, terminal, credit_progress, credit_out in participants:
                values = [Literal(name).n3(), str(outs), str(delta), str(start),
                          'UNDEF' if end is None else str(end), Literal(terminal).n3(),
                          str(credit_progress).lower(), str(credit_out).lower()]
                rows.append('(' + ' '.join(values) + ')')
        query = QUERY.read_text().replace('# EXAMPLE_ROWS', '\n'.join(rows))
        results = {str(row.example): row for row in Graph().query(query)}
        self.assertEqual(set(results), set(EXAMPLES))
        for name, (_, _, _, expected) in EXAMPLES.items():
            with self.subTest(example=name):
                row = results[name]
                self.assertTrue(all(value.datatype == Literal(0).datatype for value in row[1:]))
                self.assertEqual(tuple(Fraction(int(value), 36) for value in row[1:]),
                                 tuple(Fraction(value) for value in expected))

    def test_common_denominator_is_exact_for_every_valid_primitive(self):
        # Exhausts valid denominators instead of assuming a rounded decimal
        # representation is harmless. Means and percentiles are outside this
        # representation and retain their own exact-fraction requirements.
        for start in range(4):
            self.assertEqual(36 % (4 - start), 0)
        for end in range(1, 4):
            for outs in range(3):
                self.assertEqual(36 % ((4 - end) * (3 - outs)), 0)


if __name__ == '__main__':
    unittest.main()
