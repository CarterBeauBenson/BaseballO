"""Q7 keeps complete histories while retaining every unresolved history."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('q7_addition', ROOT / 'sources/mlb-game/pipeline/targeted-history-addition.py')
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)


class HistoryIsolation(unittest.TestCase):
    def fixture(self, case):
        half = dict(inning=case['inning'], half=case['half'], issues=case['issues'],
            completedCandidates=case['scoringCandidates'] + case['zeroEpisodeCandidates'])
        return dict(inputSha256=case['inputSha256'], sourceConsistency='consistent',
            histories=[], episodeMembership=[], placementAdjudications=[], withheldHistories=[half],
            halves=[dict(inning=case['inning'], half=case['half'], status='withheld', personalHistories=0)])

    def test_both_approved_cases_keep_identity_episodes_and_withheld_population(self):
        for case in Q.read(Q.PACKAGE / 'source-evidence.json')['cases']:
            with self.subTest(game=case['gamePk']):
                original = self.fixture(case)
                history, delta = Q.select_history(dict(runnerHistoryReconciliation=original), case)
                self.assertEqual(history['histories'], case['scoringCandidates'])
                self.assertEqual(history['withheldHistories'][0]['completedCandidates'], original['withheldHistories'][0]['completedCandidates'])
                self.assertEqual(history['halves'][0]['status'], 'withheld')
                self.assertEqual(original['histories'], [])
                self.assertEqual(Q.H.CONTEXT.isolate_zero_episode_histories(copy.deepcopy(history)), history)
                self.assertEqual(len(delta['episodeMembership']), sum(len(h['episodes']) for h in case['scoringCandidates']))

    def test_other_issue_still_withholds_the_whole_half(self):
        case = Q.read(Q.PACKAGE / 'source-evidence.json')['cases'][0]
        history = self.fixture(case)
        history['withheldHistories'][0]['issues'] = history['withheldHistories'][0]['issues'] + [dict(code='UNRESOLVED_REVIEW_EFFECT')]
        self.assertEqual(Q.H.CONTEXT.isolate_zero_episode_histories(history)['histories'], [])

    def test_named_repair_cannot_expand_to_another_half_or_changed_candidate(self):
        case = Q.read(Q.PACKAGE / 'source-evidence.json')['cases'][0]
        history = self.fixture(case)
        history['withheldHistories'][0]['completedCandidates'] = copy.deepcopy(history['withheldHistories'][0]['completedCandidates'])
        history['withheldHistories'][0]['completedCandidates'][0]['inning'] = '1'
        with self.assertRaisesRegex(ValueError, 'scope'):
            Q.select_history(dict(runnerHistoryReconciliation=history), case)

    def test_existing_rml_maps_serialize_only_selected_histories(self):
        from rdflib import Graph, URIRef
        runtime = Path.home() / 'AppData/Local/BaseballO/runtimes'
        java = next(runtime.glob('*/bin/java.exe'), None)
        mapper = next(runtime.glob('*/rmlmapper-*.jar'), None)
        if java is None or mapper is None:
            self.skipTest('Installed RMLMapper runtime required')
        case = Q.read(Q.PACKAGE / 'source-evidence.json')['cases'][0]
        _, delta = Q.select_history(dict(runnerHistoryReconciliation=self.fixture(case)), case)
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            document = dict(gamePk=int(case['gamePk']), _baseballO=dict(runnerHistoryReconciliation=delta))
            (work / 'game-context.json').write_text(json.dumps(document), encoding='utf-8')
            mapping = work / 'mapping.ttl'
            Q.subset_mapping(case['gamePk'], mapping)
            rdf = work / 'delta.ttl'
            Q.command([java, '-Xmx512m', '-jar', mapper, '-m', mapping, '-o', rdf, '-s', 'turtle',
                '-b', 'https://baseballontology.org/mapping/mlb-game/', '--strict'], work, work / 'rml.log')
            graph = Graph().parse(rdf)
            result = Q.V.verify(document, graph)
            self.assertEqual(result['personalHistories'], 1)
            self.assertEqual(len(graph), 7)  # process, interval, participant, half and two existing episodes
            whole = URIRef('https://baseballontology.org/data/game/' + case['gamePk'] + '/runner-trajectory/' + delta['histories'][0]['lifetimeKey'])
            self.assertEqual(len(list(graph.predicate_objects(whole))), 6)


if __name__ == '__main__':
    unittest.main()
