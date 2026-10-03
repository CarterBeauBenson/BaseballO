"""D1 uses only existing act maps; retries retain the selected source witness."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rdflib import Graph,RDF,URIRef
from test_defensive_mapping import ROOT,RAW,BASE

spec=importlib.util.spec_from_file_location('d1_addition',ROOT/'sources/mlb-game/pipeline/targeted-defensive-addition.py')
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)


class DefensiveAddition(unittest.TestCase):
    def test_bounded_drain_runs_serially_and_stops_at_memory_or_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);witness=dict(gamePk='1',path='source',sha256='source')
            with patch.object(D,'next_witness',return_value=witness), \
                    patch.object(D,'tick',return_value=dict(status='complete')) as tick, \
                    patch.object(D.W.A.MEMORY,'available_memory',side_effect=[2*1024**3,512*1024**2]):
                result=D.drain(state,None,None,None)
                self.assertEqual(result['outcomes'],{'complete':1,'waiting-for-memory':1});tick.assert_called_once()
            with patch.object(D,'next_witness',return_value=witness), \
                    patch.object(D,'tick',return_value=dict(status='failed')) as tick, \
                    patch.object(D.W.A.MEMORY,'available_memory',return_value=2*1024**3):
                self.assertEqual(D.drain(state,None,None,None)['outcomes'],{'failed':1});tick.assert_called_once()

    def test_recorded_failure_precedes_old_success_and_keeps_its_retry_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);repo=state/'repo';control=state/'pipeline/control/mlb-game/defensive-addition'
            successful=repo/'data/raw/samples/2026-08-25/822693.json';failed=repo/'data/raw/999999.json'
            for source in (successful,failed):
                D.W.atomic(source,dict(gamePk=int(source.stem)))
                (state/'pipeline/evidence/nifi/game-promotion'/source.stem).mkdir(parents=True)
            D.W.atomic(control/'822693.json',dict(status='complete',implementationSha256='older'))
            failure=dict(status='failed',implementationSha256='older',attempts=2,sourceSha256=D.W.sha(failed))
            D.W.atomic(control/'999999.json',failure)
            D.W.atomic(control/'inventory.json',dict(inputs={str(failed):dict(status='retry-exhausted',
                gamePk='999999',sha256=D.W.sha(failed),identity=['old'])}))
            with patch.object(D,'ROOT',repo),patch.object(D,'fingerprint',return_value='current'), \
                    patch.object(D,'select',return_value=dict(acts=[{}])):
                self.assertEqual(D.next_witness(state,limit=1)['gamePk'],'999999')
                D.W.atomic(control/'999999.json',dict(failure,implementationSha256='current'))
                self.assertEqual(D.next_witness(state,limit=1)['gamePk'],'822693')

    def test_legacy_promotion_gets_current_proof_without_skipping_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence=Path(temp);marker=dict(rawSha256='original-source')
            selected=dict(populationComplete=False)
            with patch.object(D.W,'revalidate',return_value=dict(retained=True)) as retained, \
                    patch.object(D.D,'prove',return_value=dict(graphConforms=True,status='withheld')) as prove:
                result=D.revalidate(marker,{},evidence/'game.ttl',evidence,None,None,selected,'822693',set())
                retained.assert_called_once();prove.assert_called_once()
                proof=D.W.read(Path(result['defensiveAdmission']))
                self.assertEqual(proof['status'],'withheld')
                self.assertIsNone(proof['graphRevalidation']['originalProofSha256'])
            with patch.object(D.D,'prove') as prove:
                with self.assertRaisesRegex(ValueError,'reference is incomplete'):
                    D.revalidate(dict(marker,defensiveAdmission='missing'),{},None,evidence,None,None,selected,'822693',set())
                prove.assert_not_called()

    def test_selected_mapping_contains_only_reviewed_defensive_facts(self):
        selected=D.select(RAW,'822693')
        self.assertEqual(len(selected['acts']),59);self.assertFalse(selected['populationComplete'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);context=root/'game-context.json';mapping=root/'addition.rml.ttl'
            D.execution_inputs(RAW,'822693',selected,context,mapping)
            graph=Graph().parse(mapping)
            maps=list(graph.subjects(RDF.type,URIRef('http://www.w3.org/ns/r2rml#TriplesMap')))
            self.assertEqual({str(m).split('#')[-1] for m in maps},set(D.MAPS))
            value=json.loads(context.read_text());self.assertNotIn('liveData',value)
            self.assertEqual(value['_baseballO']['defensiveActs'],selected['acts'])
            Graph().parse(data=D.shapes('822693',selected),format='turtle')

    def test_selected_witness_survives_a_failed_attempt_and_stops_after_success(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);(state/'pipeline/evidence/nifi/game-promotion/822693').mkdir(parents=True)
            first=D.next_witness(state);self.assertEqual(first['gamePk'],'822693')
            control=state/'pipeline/control/mlb-game/defensive-addition/822693.json'
            D.W.atomic(control,dict(status='failed',implementationSha256=D.fingerprint(),attempts=1))
            self.assertEqual(D.next_witness(state),first)
            D.W.atomic(control,dict(status='complete',implementationSha256=D.fingerprint(),sourceSha256=first['sha256']))
            self.assertIsNone(D.next_witness(state))

    def test_new_selection_version_revisits_old_success_without_blocking_other_games(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);(state/'pipeline/evidence/nifi/game-promotion/822693').mkdir(parents=True)
            control=state/'pipeline/control/mlb-game/defensive-addition/822693.json'
            D.W.atomic(control,dict(status='complete',implementationSha256='old-version'))
            witness=D.next_witness(state)
            self.assertEqual(witness['gamePk'],'822693')
            with patch.object(D.W,'add_game',return_value=dict(status='already-present',rdfChanged=False)) as add:
                result=D.tick(state,witness,None,None,None)
                add.assert_called_once();self.assertEqual(result['status'],'already-present')
            self.assertIsNone(D.next_witness(state))

    def test_failed_first_fixture_does_not_block_an_independent_witness(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);repo=state/'repo'
            for pk in ('822693','999999'):
                (state/'pipeline/evidence/nifi/game-promotion'/pk).mkdir(parents=True)
                source=repo/'data/raw/samples/2026-08-25'/(pk+'.json')
                D.W.atomic(source,dict(gamePk=int(pk)))
            control=state/'pipeline/control/mlb-game/defensive-addition/822693.json'
            D.W.atomic(control,dict(status='failed',implementationSha256=D.fingerprint(),attempts=2,
                sourceSha256=D.W.sha(repo/'data/raw/samples/2026-08-25/822693.json')))
            with patch.object(D,'ROOT',repo),patch.object(D,'select',return_value=dict(acts=[{}])):
                self.assertEqual(D.next_witness(state)['gamePk'],'999999')


if __name__=='__main__':unittest.main()
