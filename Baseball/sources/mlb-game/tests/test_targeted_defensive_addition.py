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
            D.W.atomic(control,dict(status='complete'))
            self.assertIsNone(D.next_witness(state))


if __name__=='__main__':unittest.main()
