"""Exact player means and qualification inputs; no source admission is inferred."""
import unittest

from rdflib import Namespace, RDF
from test_metric_suite_serving import M, G1, G2, PREFIX, fixture, bindings, database

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
    def test_b1_proof_and_selected_schedule_are_separate_gates(self):
        import importlib.util
        from rdflib import Dataset
        path=M.ROOT/'sources/mlb-game/tests/test_batting_admission.py'
        spec=importlib.util.spec_from_file_location('b1_fixture',path)
        component=importlib.util.module_from_spec(spec);spec.loader.exec_module(component)
        _,source_graph=component.fixture()
        data=Dataset()
        for triple in source_graph:data.graph(G1).add(triple)
        source=bindings(data,[G1]);rows=M.normalize_bindings(source,[G1])
        admission=dict(status='admitted',sourceReconciled=True,graphConforms=True)
        args=dict(graphs=[G1],admissions={G1:admission},date_scope=SCOPE)
        partial=M.batting_qualification(rows,**args)
        self.assertTrue(partial['officialPlateAppearanceCreditVerified'])
        self.assertFalse(partial['teamGameExposureVerified'])
        self.assertEqual(len(partial['expectedObservations']),1)
        self.assertEqual([p['plateAppearances'] for p in partial['participation']],[1,0])
        full=M.batting_qualification(rows,**args,selected_games_complete=True)
        self.assertTrue(full['teamGameExposureVerified'])
        self.assertTrue(all(p['completeParticipation'] for p in full['participation']))
        denied=M.batting_qualification(rows,**{**args,'admissions':{}},selected_games_complete=True)
        self.assertEqual(denied['participation'],[])
        with database() as connection:
            M.materialize_game(connection,G1,source,batting_admission=admission)
            response=M.query_sql(connection,{'metricId':'offensive-reach'},
                dict(gameSet='regular_season',startDate='2026-08-01',endDate='2026-08-01'))
            self.assertTrue(response['battingQualification']['officialPlateAppearanceCreditVerified'])
            self.assertEqual(response['battingQualification']['officialPlateAppearances'],1)
            self.assertFalse(response['battingQualification']['teamGameExposureVerified'])
            self.assertEqual(response['metric']['status'],'unavailable')

    def test_missing_selected_game_or_day_cannot_lower_minimum(self):
        scope=dict(gameSet='regular_season',startDate='2026-08-01',endDate='2026-08-01')
        def store(connection, games, complete=True):
            text=M._json(dict(completeResponse=complete,games=[dict(gamePk=g,gameType='R',
                                  final=True,unplayed=False) for g in games]))
            connection.execute('INSERT OR REPLACE INTO metric_suite_schedule_coverage VALUES (?,?,?)',
                               ('2026-08-01',text,M._hash(text)))
        with database() as connection:
            self.assertFalse(M.selected_schedule_coverage(connection,scope,[G1])['complete'])
            store(connection,['101','102'])
            self.assertEqual(M.selected_schedule_coverage(connection,scope,[G1])['missingGraphs'],[G2])
            self.assertTrue(M.selected_schedule_coverage(connection,scope,[G1,G2])['complete'])
            store(connection,['101','102'],complete=False)
            self.assertFalse(M.selected_schedule_coverage(connection,scope,[G1,G2])['complete'])
            store(connection,['101'])
            self.assertFalse(M.selected_schedule_coverage(connection,{**scope,'endDate':'2026-08-02'},[G1])['complete'])

    def test_existing_game_roles_include_nonbatters_without_inferred_membership(self):
        data = fixture(decisions=())
        g = data.graph(G1)
        g.parse(data=PREFIX.replace('<urn:test:>', '<urn:test:101:>')+'''
ex:game obo:BFO_0000055 ex:benchRole, ex:unknownTeamRole .
ex:benchRole a base:PlayerRole ; obo:BFO_0000197 ex:bench ; cco:ont00001992 ex:team .
ex:unknownTeamRole a base:PlayerRole ; obo:BFO_0000197 ex:unknown .
ex:teamRole a base:HomeTeamRole ; obo:BFO_0000197 ex:team ; obo:BFO_0000054 ex:game .
ex:unusedRole a base:PlayerRole ; obo:BFO_0000197 ex:unused ; cco:ont00001992 ex:team .
''', format='turtle')
        source = bindings(data, [G1])
        rows = M.normalize_bindings(source, [G1])
        actual = [row for row in rows if row['kind'] == 'player_team_game']
        self.assertEqual(len(actual), 2)
        bench, = [r for r in actual if r['player'].endswith(':bench')]
        self.assertEqual(bench['team'], 'urn:test:101:team')
        self.assertEqual(bench['teamRole'], 'urn:test:101:teamRole')
        unknown, = [r for r in actual if r['player'].endswith(':unknown')]
        self.assertNotIn('team', unknown)
        self.assertFalse(any(r.get('player') == bench['player'] and r['kind'] == 'plate_appearance' for r in rows))
        self.assertFalse(M.batting_participation(rows)['teamGameExposureVerified'])
        # Supply the other named graph locally: RDFLib otherwise dereferences
        # a missing FROM NAMED URI, which is outside this isolated fixture.
        data.graph(G2).parse(data=PREFIX+'ex:unrelated a base:PlayerRole .', format='turtle')
        self.assertEqual(bindings(data, [G2]), [])
        with database() as connection:
            M.materialize_game(connection, G1, source)
            stored = [M.json.loads(row[0]) for row in connection.execute(
                'SELECT binding_json FROM metric_suite_evidence WHERE graph_iri=?', (G1,))]
            self.assertEqual(sorted(stored, key=M._json), sorted(rows, key=M._json))

    def test_adjudicated_result_inventory_does_not_declare_pa_eligibility(self):
        data = fixture(decisions=())
        data.graph(G1).parse(data=PREFIX.replace('<urn:test:>', '<urn:test:101:>')+'''
ex:result a base:BaseballInstitutionalProcess, base:WalkProcess ; obo:BFO_0000132 ex:pa .
ex:judgment a base:BaseballAdjudicationAct ; obo:BFO_0000132 ex:result ; cco:ont00001986 ex:decision .
ex:decision a base:BaseballDecisionICE ; cco:ont00001808 ex:result .
ex:record a base:BaseballEventRecord ; cco:ont00001808 ex:result, ex:judgment, ex:decision .
''', format='turtle')
        source = bindings(data, [G1])
        rows = M.normalize_bindings(source, [G1])
        pas = [r for r in rows if r['kind'] == 'plate_appearance']
        self.assertEqual(len(pas), 2)  # Both asserted types remain visible.
        self.assertEqual({r['paResultType'].rsplit('/', 1)[-1] for r in pas},
                         {'BaseballInstitutionalProcess', 'WalkProcess'})
        self.assertEqual({r['paResultDecision'] for r in pas}, {'urn:test:101:decision'})
        self.assertEqual(M.batting_participation(rows)['observedPlateAppearances'], 1)
        self.assertFalse(M.batting_participation(rows)['officialPlateAppearanceCreditVerified'])
        term = next(b for b in source if 'paResultType' in b)['paResultType']
        term['type'] = 'literal'
        with self.assertRaises(M.EvidenceError):
            M.normalize_bindings(source, [G1])

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
