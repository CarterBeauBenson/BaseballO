"""R1 scope and existing-referent regressions; no live graph mutation."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rdflib import Graph, Namespace, RDF, URIRef
from pyshacl import validate

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('r1_worker',ROOT/'sources/mlb-game/pipeline/targeted-runner-addition.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


class TargetedRunnerAddition(unittest.TestCase):
    def test_legacy_history_recovery_adds_only_accepted_boundary_dependencies(self):
        case=R.approved_case('831445')
        state=Path.home()/'AppData/Local/BaseballO/state'
        witness=state/case['retainedInputs'][0]['path']
        if not witness.is_file():self.skipTest('Retained runtime witness has been retired')
        raw=witness.read_bytes();selected=R.select(raw,'831445')
        self.assertEqual(selected['boundaryCensus']['status'],'reconciled')
        self.assertEqual(len(selected['history']['histories']),32)
        plays=selected['context']['liveData']['plays']['allPlays']
        self.assertEqual(len(plays),82)
        self.assertEqual(sum(len(p['_baseballO']['startBaseOccupancies']) for p in plays),51)
        actual={(str(p['about']['atBatIndex']),r['runnerId'],r['baseCode'])
            for p in plays for r in p['_baseballO']['startBaseOccupancies']}
        expected={(b['pa'].rsplit('/',1)[-1],r['player'].rsplit('/',1)[-1],r['base'])
            for b in selected['boundaryCensus']['boundaries'] for r in b['occupants']}
        self.assertEqual(actual,expected)
        self.assertEqual(len(selected['history']['episodeMembership']),
            sum(len(h['episodes']) for h in selected['history']['histories']))
        Graph().parse(data=R.shapes('831445',selected),format='turtle')
        with tempfile.TemporaryDirectory() as directory:
            context=Path(directory)/'game-context.json';mapping=Path(directory)/'addition.ttl'
            R.execution_inputs(raw,'831445',selected,context,mapping)
            rr=Namespace('http://www.w3.org/ns/r2rml#');graph=Graph().parse(mapping)
            self.assertEqual({str(s).rsplit('#',1)[-1] for s in graph.subjects(RDF.type,rr.TriplesMap)},
                set(R.MAPS+R.BOUNDARY_MAPS))
            self.assertNotIn(URIRef('https://baseballontology.org/BaserunningAct'),set(graph.objects(None,rr['class'])))
            self.assertNotIn(URIRef('https://baseballontology.org/SafeProcess'),set(graph.objects(None,rr['class'])))
        with patch.object(R.B,'census',return_value=dict(status='withheld')):
            with self.assertRaisesRegex(ValueError,'boundary source remains unresolved'):R.select(raw,'831445')
        with self.assertRaisesRegex(ValueError,'retained R1 witnesses'):R.select(raw+b' ','831445')
        self.assertEqual(raw,witness.read_bytes())

    def test_scope_keeps_complete_dependencies_and_slices_unchanged_maps(self):
        raw=(ROOT/'data/raw/game-566279.json').read_bytes()
        case=dict(gamePk='566279',plateAppearances=['23'],retainedInputs=[dict(sha256=hashlib.sha256(raw).hexdigest())])
        with patch.object(R,'approved_case',return_value=case):
            selected=R.select(raw,'566279')
            with self.assertRaisesRegex(ValueError,'retained R1 witnesses'):R.select(raw+b' ','566279')
        history=selected['history'];keys={(r['atBatIndex'],r['runnerIndex']) for r in selected['episodes']}
        dependencies={(r['atBatIndex'],r['runnerIndex']) for r in history['episodeMembership']}
        self.assertTrue(dependencies<=keys)
        self.assertTrue(all(pa=='23' or (pa,index) in dependencies for pa,index in keys))
        self.assertEqual(len(history['episodeMembership']),sum(len(h['episodes']) for h in history['histories']))
        self.assertEqual(raw,(ROOT/'data/raw/game-566279.json').read_bytes())
        Graph().parse(data=R.shapes('566279',selected),format='turtle')
        with tempfile.TemporaryDirectory() as directory:
            context=Path(directory)/'game-context.json';mapping=Path(directory)/'addition.ttl'
            R.execution_inputs(raw,'566279',selected,context,mapping)
            rr=Namespace('http://www.w3.org/ns/r2rml#');graph=Graph().parse(mapping)
            self.assertEqual({str(s).rsplit('#',1)[-1] for s in graph.subjects(RDF.type,rr.TriplesMap)},set(R.MAPS))
            self.assertEqual(R.W.read(context),selected['context'])
            self.assertNotIn('{$.gamePk}',mapping.read_text())
            self.assertNotIn('{$.gameData.venue.id}',mapping.read_text())
            # The new referent check cannot be satisfied by manufacturing the
            # pre-existing act, participant or resolution in this RML slice.
            self.assertNotIn(URIRef('https://baseballontology.org/BaserunningAct'),set(graph.objects(None,rr['class'])))
            self.assertNotIn(URIRef('https://baseballontology.org/SafeProcess'),set(graph.objects(None,rr['class'])))

    def test_identity_check_rejects_wrong_existing_player_or_outcome(self):
        values=dict(ACT='urn:act',PA='urn:pa',PLAYER='urn:player',RESOLUTION='urn:resolution',OUTCOME='SafeProcess')
        text=R.SHAPE.read_text()
        for key,value in values.items():text=text.replace('__'+key+'__',value)
        shapes=Graph().parse(data=text,format='turtle');base=Namespace('https://baseballontology.org/')
        bfo=Namespace('http://purl.obolibrary.org/obo/');cco=Namespace('https://www.commoncoreontologies.org/')
        act,pa,player,resolution=[URIRef(values[k]) for k in ('ACT','PA','PLAYER','RESOLUTION')]
        data=Graph()
        for triple in [(act,RDF.type,base.BaserunningAct),(act,bfo.BFO_0000132,pa),
            (act,bfo.BFO_0000057,player),(player,RDF.type,cco.ont00001262),
            (resolution,RDF.type,base.SafeProcess),(resolution,bfo.BFO_0000132,pa),(resolution,bfo.BFO_0000062,act)]:data.add(triple)
        self.assertTrue(validate(data,shacl_graph=shapes)[0])
        for triple in [(act,bfo.BFO_0000057,player),(resolution,RDF.type,base.SafeProcess)]:
            data.remove(triple)
            self.assertFalse(validate(data,shacl_graph=shapes)[0])
            data.add(triple)

    def test_first_game_failure_stops_wider_execution(self):
        cases=[dict(gamePk='823200',retainedInputs=[dict(path='fixture.json',sha256='fixture')]),
               dict(gamePk='822864',retainedInputs=[dict(path='other.json',sha256='other')])]
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);inventory=state/'inventory.json';R.W.atomic(inventory,dict(games=cases))
            (state/'fixture.json').write_text('{}');(state/'other.json').write_text('{}')
            control=state/'pipeline/control/mlb-game/runner-addition/823200.json'
            with patch.object(R,'INVENTORY',inventory),patch.object(R,'approved_case'),patch.object(R,'fingerprint',return_value='v'):
                self.assertEqual(R.next_witness(state)['gamePk'],'823200')
                R.W.atomic(control,dict(status='failed',attempts=2,implementationSha256='v'))
                self.assertIsNone(R.next_witness(state))
                R.W.atomic(control,dict(status='complete'))
                self.assertEqual(R.next_witness(state)['gamePk'],'822864')


if __name__=='__main__':unittest.main()
