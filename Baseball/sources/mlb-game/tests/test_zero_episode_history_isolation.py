"""Q7 keeps complete histories while retaining every unresolved history."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('q7_addition', ROOT / 'sources/mlb-game/pipeline/targeted-history-addition.py')
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)


class HistoryIsolation(unittest.TestCase):
    def test_first_defensive_proof_uses_its_actual_promotion_source_binding(self):
        decision='archive/design-records/mlb-game-defensive-acts/review.json'
        original=dict(gamePk='831445',sourceSha256='separate-input',status='withheld',
            graphRevalidation=dict(decision=decision,mode='current-defensive-source-census',
                promotionSourceSha256='original-input',originalProofSha256=None))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'defensive-admission.json';Q.atomic(path,original)
            marker=dict(gamePk='831445',rawSha256='original-input',defensiveAdmission=str(path),
                defensiveAdmissionSha256=Q.sha(path),targetedAddition=dict(decision=decision,
                    sourceWitness=dict(gamePk='831445',sha256='separate-input')))
            proof=copy.deepcopy(original)
            Q.retain_source_binding(proof,marker,'defensiveAdmission')
            self.assertEqual(proof['sourceRevalidation']['originalProofSha256'],Q.sha(path))
            self.assertEqual(proof['status'],'withheld')
            self.assertEqual(proof['sourceSha256'],'separate-input')
            self.assertEqual(Q.read(path),original)
            # Later additions keep the first proof binding even though their
            # own promotion is for a different selected product.
            Q.retain_source_binding(proof,dict(marker,targetedAddition={}), 'defensiveAdmission')
            bad=copy.deepcopy(marker);bad['targetedAddition']['sourceWitness']['sha256']='other'
            for changed in (bad,dict(marker,defensiveAdmissionSha256='other'),
                            dict(marker,targetedAddition={}),dict(marker,gamePk='other')):
                with self.assertRaisesRegex(ValueError,'unbound source'):
                    Q.retain_source_binding(copy.deepcopy(original),changed,'defensiveAdmission')

    def test_defensive_source_receipt_survives_multiple_additions(self):
        marker = dict(rawSha256='original-input')
        receipt = dict(decision='archive/design-records/mlb-game-defensive-acts/review.json',
            mode='current-defensive-source-census', promotionSourceSha256='original-input',
            originalProofSha256='original-proof')
        proof = dict(sourceSha256='separate-retained-input', graphRevalidation=receipt)
        Q.retain_source_binding(proof, marker, 'defensiveAdmission')
        proof['graphRevalidation'] = dict(mode='unchanged-source-census')
        Q.retain_source_binding(proof, marker, 'defensiveAdmission')
        self.assertEqual(proof['sourceSha256'], 'separate-retained-input')
        self.assertEqual(proof['sourceRevalidation'], receipt)
        for changed, field in ((dict(receipt, promotionSourceSha256='another-game'), 'defensiveAdmission'),
                               (dict(receipt, decision='unknown'), 'defensiveAdmission'),
                               (receipt, 'runnerHistoryAdmission')):
            with self.assertRaisesRegex(ValueError, 'unbound source'):
                Q.retain_source_binding(dict(sourceSha256='separate-retained-input',
                    graphRevalidation=changed), marker, field)

    def test_existing_graph_export_preserves_literal_terms(self):
        from rdflib import Graph, Literal, URIRef
        date = Literal('2026-09-17T00:09:19.347Z', datatype=URIRef('http://www.w3.org/2001/XMLSchema#dateTime'), normalize=False)
        number = Literal('01', datatype=URIRef('http://www.w3.org/2001/XMLSchema#integer'), normalize=False)
        original = Graph()
        for predicate, value in [('date', date), ('number', number)]:
            original.add((URIRef('urn:original'), URIRef('urn:' + predicate), value))
        parsed = Q.TX.nt_graph(original.serialize(format='nt', encoding='utf-8'))
        delta = Graph().parse(data='<urn:history> <urn:episode> <urn:existing-episode> .', format='nt')
        union = Graph().parse(data=(parsed + delta).serialize(format='nt'), format='nt')
        self.assertEqual(set(union), set(original) | set(delta))
        self.assertEqual(set(original) - set(union), set())

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

    def test_completion_inventory_keeps_exact_histories_and_rejects_scope_drift(self):
        original = Q.read(Q.PACKAGE / 'source-evidence.json')['cases'][0]
        history = self.fixture(original)
        case = dict(inputSha256=original['inputSha256'],
            halves=[dict(inning=original['inning'], half=original['half'])],
            selectedHistoryKeys=[h['lifetimeKey'] for h in original['scoringCandidates']])
        updated, delta = Q.select_history(dict(runnerHistoryReconciliation=history), case)
        self.assertEqual(delta['histories'], original['scoringCandidates'])
        self.assertEqual(updated['halves'][0]['status'], 'withheld')
        for changed in (dict(case, selectedHistoryKeys=[]),
                        dict(case, halves=[dict(inning=1, half='top')]),
                        dict(case, inputSha256='different-source')):
            with self.assertRaises(ValueError):
                Q.select_history(dict(runnerHistoryReconciliation=history), changed)

    def test_next_case_skips_completed_repairs_and_stays_inside_inventory(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(Q, 'cases', return_value=[
                dict(gamePk='822846'), dict(gamePk='822680')]):
            state = Path(temporary)
            Q.atomic(state / 'pipeline/control/mlb-game/history-addition/822846.json', dict(status='complete'))
            self.assertEqual(Q.next_case(state), '822680')
            Q.atomic(state / 'pipeline/control/mlb-game/history-addition/822680.json', dict(status='already-complete'))
            self.assertIsNone(Q.next_case(state))

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
