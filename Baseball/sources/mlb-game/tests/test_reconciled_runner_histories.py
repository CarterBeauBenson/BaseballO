import copy
import importlib.util
import json
import unittest

from rdflib import Graph, URIRef

from test_runner_structural_patterns import CONTEXT, ROOT

SPEC = importlib.util.spec_from_file_location('serialization', ROOT / 'sources/mlb-game/pipeline/verify-runner-history-serialization.py')
V = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(V)


class ReconciledRunnerHistories(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / 'data/raw/game-566279.json').read_bytes()
        cls.source = json.loads(cls.raw)
        cls.result = CONTEXT.personal_runner_histories(cls.raw)

    def changed(self, mutate):
        doc = copy.deepcopy(self.source); mutate(doc)
        return CONTEXT.personal_runner_histories(json.dumps(doc).encode())

    def top_first(self, result):
        return next(h for h in result['halves'] if h['inning'] == 1 and h['half'] == 'top')

    def test_real_histories_join_across_pas_keep_episodes_and_stranding(self):
        self.assertEqual(len(self.result['histories']), 18)
        runner = next(h for h in self.result['histories'] if h['runnerId'] == '527038')
        self.assertEqual(runner['terminal'], 'score')
        self.assertEqual([(r['atBatIndex'], r['runnerIndex']) for r in runner['episodes']], [('2', '0'), ('3', '1'), ('3', '2')])
        stranded = next(h for h in self.result['histories'] if h['runnerId'] == '572233' and h['inning'] == '1')
        self.assertEqual(stranded['terminal'], 'stranded')
        self.assertTrue(all(r['resolutionKind'] not in ('out', 'score') for r in stranded['episodes']))
        self.assertFalse(self.result['graphCoverageVerified'])
        self.assertFalse(self.result['metricPopulationAdmitted'])

    def test_direct_batter_out_does_not_invent_baserunning_lifetime(self):
        self.assertTrue(all(not (e['atBatIndex'] == '1') for h in self.result['histories'] for e in h['episodes']))

    def test_raw_remains_unchanged_and_retry_identity_is_stable(self):
        self.assertEqual(CONTEXT.personal_runner_histories(self.raw), self.result)
        self.assertEqual((ROOT / 'data/raw/game-566279.json').read_bytes(), self.raw)

    def test_row_reordering_keeps_whole_identity_and_remaps_episode_membership(self):
        changed = self.changed(lambda d: d['liveData']['plays']['allPlays'][3]['runners'].reverse())
        self.assertEqual({h['lifetimeKey'] for h in changed['histories']}, {h['lifetimeKey'] for h in self.result['histories']})
        self.assertNotEqual(changed['episodeMembership'], self.result['episodeMembership'])

    def test_missing_source_event_does_not_pass_from_matching_endpoints(self):
        changed = self.changed(lambda d: d['liveData']['plays']['allPlays'][2]['playEvents'].pop())
        self.assertEqual(changed['sourceConsistency'], 'inconsistent')
        self.assertEqual(changed['histories'], [])

    def test_unresolved_review_or_substitution_withholds_affected_half(self):
        for fault in ('review', 'substitution'):
            def mutate(d):
                play = d['liveData']['plays']['allPlays'][4]
                if fault == 'review': play['about']['hasReview'] = True
                else:
                    play['playEvents'][0]['isPitch'] = False
                    play['playEvents'][0]['type'] = 'action'
                    play['playEvents'][0]['details']['eventType'] = 'offensive_substitution'
            changed = self.changed(mutate)
            self.assertEqual(self.top_first(changed)['status'], 'withheld')
            self.assertTrue(any(h['half'] == 'bottom' for h in changed['histories']))

    def test_incompatible_segment_origin_withholds_entire_history(self):
        changed = self.changed(lambda d: d['liveData']['plays']['allPlays'][3]['runners'][1]['movement'].update(start='3B'))
        self.assertEqual(self.top_first(changed)['status'], 'withheld')

    def test_temporal_ambiguity_and_missing_anchor_do_not_create_bounds(self):
        for field, value in [('playId', None), ('startTime', '2019-04-01T00:00:00Z')]:
            changed = self.changed(lambda d: d['liveData']['plays']['allPlays'][4]['playEvents'][-1].update({field: value}))
            self.assertEqual(self.top_first(changed)['status'], 'withheld')

    def test_serialization_detects_missing_and_extra_membership(self):
        document = {'gamePk': 566279, '_baseballO': {'runnerHistoryReconciliation': self.result}}
        root = 'https://baseballontology.org/data/game/566279/'
        graph = Graph()
        for row in self.result['episodeMembership']:
            graph.add((URIRef(root + 'runner-trajectory/' + row['lifetimeKey']), V.BFO.BFO_0000117,
                       URIRef(root + f"runner-episode/{row['atBatIndex']}/{row['runnerIndex']}")))
        self.assertEqual(V.verify(document, graph)['personalHistories'], 18)
        triple = next(iter(graph)); graph.remove(triple)
        with self.assertRaisesRegex(ValueError, 'serialization differs'):
            V.verify(document, graph)
        graph.add(triple)
        graph.add((triple[0], triple[1], URIRef(root + 'runner-episode/999/0')))
        with self.assertRaisesRegex(ValueError, 'serialization differs'):
            V.verify(document, graph)


if __name__ == '__main__': unittest.main()
