"""Exact player means and qualification inputs; no source admission is inferred."""
import unittest

from rdflib import Namespace, RDF
from test_metric_suite_serving import M, G1, fixture, bindings

SCOPE = dict(startDate='2026-08-01', endDate='2026-08-07', gameSet='regular_season')
PLAYER = 'https://baseballontology.org/data/player/1'


def inputs():
    members = [dict(graph=G1, plateAppearance='https://example.org/pa/'+str(i), player=PLAYER)
               for i in range(3)]
    scores = [dict(row, metricId='offensive-reach', status='available', completePlateAppearance=True,
                   dateScope=SCOPE, value=M.exact(value)) for row, value in zip(members, (1, 2, 4))]
    people = [dict(player=PLAYER, completeParticipation=True, dateScope=SCOPE,
                   plateAppearances=3, teamGameExposure=[dict(game='https://example.org/game/'+str(i),
                       team='https://example.org/team/1') for i in range(7)])]
    return members, scores, people


def summarize(members, scores, people, **kwargs):
    return M.summarize_batting_players('offensive-reach', scores,
        expected_observations=members, participation=people, date_scope=SCOPE,
        population_complete=kwargs.get('population_complete', True))


class BattingPlayerSummaries(unittest.TestCase):
    def test_exact_mean_keeps_missed_games_in_qualification(self):
        members, scores, people = inputs()
        result = summarize(members, scores, people)
        row, = result['playerResults']
        self.assertTrue(result['playerPopulationComplete'])
        self.assertEqual(row['aggregate'], dict(kind='mean', sum=M.exact(7), count=3))
        self.assertEqual(row['value'], M.exact(M.Fraction(7, 3)))
        self.assertEqual(row['teamGames'], 7)  # Not one observed batting game.
        self.assertEqual(row['plateAppearances'], 3)

    def test_duplicate_observations_and_exposures_are_idempotent(self):
        members, scores, people = inputs()
        expected = summarize(members, scores, people)
        people[0]['teamGameExposure'] *= 2
        self.assertEqual(summarize(members*2, scores*2, people), expected)

    def test_missing_extra_partial_and_conflicting_scores_fail_closed(self):
        members, scores, people = inputs()
        for altered in (scores[:-1], [*scores, dict(scores[0], plateAppearance='https://example.org/extra')],
                        [dict(scores[0], completePlateAppearance=False), *scores[1:]],
                        [dict(scores[0], dateScope={**SCOPE, 'endDate':'2026-08-06'}), *scores[1:]]):
            result = summarize(members, altered, people)
            self.assertFalse(result['playerPopulationComplete'])
            self.assertEqual(result['playerResults'], [])
        with self.assertRaises(M.EvidenceError):
            summarize(members, scores+[dict(scores[0], value=M.exact(8))], people)

    def test_matching_rows_do_not_certify_population_or_participation(self):
        members, scores, people = inputs()
        self.assertFalse(summarize(members, scores, people, population_complete=False)['playerPopulationComplete'])
        self.assertFalse(summarize(members, scores, [])['playerPopulationComplete'])
        people[0]['completeParticipation'] = False
        self.assertFalse(summarize(members, scores, people)['playerPopulationComplete'])
        people[0]['completeParticipation'] = True
        people[0]['teamGameExposure'] = []
        self.assertEqual(summarize(members, scores, people)['playerSummaryGaps'], ['TEAM_GAME_EXPOSURE'])

    def test_official_credit_is_not_inferred_from_contribution_membership(self):
        members, scores, people = inputs()
        people[0]['plateAppearances'] = 4
        row, = summarize(members, scores, people)['playerResults']
        self.assertEqual(row['plateAppearances'], 4)
        self.assertEqual(row['aggregate']['count'], 3)
        people[0]['plateAppearances'] = 0
        self.assertEqual(summarize(members, scores, people)['playerResults'], [])

    def test_team_changes_and_doubleheaders_preserve_independent_exposures(self):
        members, scores, people = inputs()
        people[0]['teamGameExposure'][3]['team'] = 'https://example.org/team/2'
        people[0]['teamGameExposure'].append(dict(game='https://example.org/game/second-game',
                                                 team='https://example.org/team/2'))
        row, = summarize(members, scores, people)['playerResults']
        self.assertEqual(row['teamGames'], 8)

    def test_invalid_fractions_and_non_pa_metrics_are_rejected(self):
        members, scores, people = inputs()
        for value in ({'numerator':1, 'denominator':2}, {'numerator':'1', 'denominator':'0'},
                      {'numerator':'2', 'denominator':'2'}):
            with self.assertRaises(M.EvidenceError):
                summarize(members, [dict(scores[0], value=value), *scores[1:]], people)
        with self.assertRaises(M.EvidenceError):
            M.summarize_batting_players('empty-game-rate', [], expected_observations=[],
                participation=[], date_scope=SCOPE, population_complete=True)

    def test_inventory_preserves_missing_and_ambiguous_pa_batters(self):
        data = fixture(decisions=())
        ex = Namespace('urn:test:101:')
        base = Namespace('https://baseballontology.org/')
        obo = Namespace('http://purl.obolibrary.org/obo/')
        g = data.graph(G1)
        g.add((ex.act, RDF.type, base.BatterAct))
        rows = M.normalize_bindings(bindings(data, [G1]), [G1])
        actual = M.batting_participation(rows+rows)
        self.assertEqual(actual['withOneBatter'], 1)
        self.assertFalse(actual['officialPlateAppearanceCreditVerified'])
        self.assertFalse(actual['teamGameExposureVerified'])
        g.add((ex.role, obo.BFO_0000197, ex.other))
        g.add((ex.unassigned, RDF.type, base.PlateAppearance))
        g.add((ex.unassigned, obo.BFO_0000132, ex.half))
        rows = M.normalize_bindings(bindings(data, [G1]), [G1])
        actual = M.batting_participation(rows)
        self.assertEqual(actual['observedPlateAppearances'], 2)
        self.assertEqual(actual['withMultipleBatters'], 1)
        self.assertEqual(actual['withoutBatter'], 1)
        self.assertEqual(len(actual['players']), 2)


if __name__ == '__main__':
    unittest.main()
