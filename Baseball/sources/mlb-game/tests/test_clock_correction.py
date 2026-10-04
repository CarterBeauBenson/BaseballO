"""Bound the historical mutation and exercise the shared production clock map."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from rdflib import Graph, Literal, URIRef, XSD
from rdflib.compare import isomorphic

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('clock_correction_test',ROOT/'sources/mlb-game/pipeline/targeted-clock-correction.py')
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, local_root


class ClockCorrection(unittest.TestCase):
    def test_mutation_removes_only_the_verified_old_value_and_is_idempotent(self):
        case=T.case_for('831629');game='https://baseballontology.org/data/game/831629'
        subject=URIRef(game+'/timestamp/end');predicate=URIRef('https://www.commoncoreontologies.org/ont00001767')
        old=(subject,predicate,Literal(case['previousGameEnd'],datatype=XSD.dateTime,normalize=False))
        new=(subject,predicate,Literal(T.compact_fraction(case['gameEnd']),datatype=XSD.dateTime,normalize=False))
        unrelated=(URIRef('urn:existing'),URIRef('urn:predicate'),Literal('preserve'))
        base=Graph();base.add(old);base.add(unrelated)
        delta=Graph();delta.add(new)
        removed=T.removals(base,delta,'831629',dict(game=game))
        self.assertEqual(set(removed),{old})
        combined=(base-removed)+delta
        self.assertEqual(set(combined),{new,unrelated})
        self.assertEqual(len(T.removals(combined,delta,'831629',dict(game=game))),0)
        delta.add((subject,URIRef('urn:extra'),Literal('unapproved')))
        with self.assertRaisesRegex(ValueError,'scope'):T.removals(base,delta,'831629',dict(game=game))
        delta.remove((subject,URIRef('urn:extra'),Literal('unapproved')))
        base.add(new)
        with self.assertRaisesRegex(ValueError,'Existing clock'):T.removals(base,delta,'831629',dict(game=game))

    def test_targeted_update_round_trips_exactly_through_tdb2(self):
        old='2026-03-07T19:39:59.113Z';new='2026-03-07T19:40:45.340Z'
        compact=T.compact_fraction(new)
        self.assertEqual(compact,'2026-03-07T19:40:45.34Z')
        self.assertEqual(Literal(new,datatype=XSD.dateTime).toPython(),Literal(compact,datatype=XSD.dateTime).toPython())
        s,p=URIRef('urn:s'),URIRef('urn:p')
        removed=Graph().add((s,p,Literal(old,datatype=XSD.dateTime,normalize=False)))
        delta=Graph().add((s,p,Literal(compact,datatype=XSD.dateTime,normalize=False)))
        keep=Graph().add((URIRef('urn:keep'),p,Literal('unchanged')))
        with patch.object(T.W.urllib.request,'urlopen') as send:
            send.return_value.__enter__.return_value.status=204
            T.W.apply_delta(Mock(),'urn:game',delta,removed)
            update=send.call_args.args[0].data
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'base.nt';result=root/'result.nt';query=root/'update.ru'
            (removed+keep).serialize(destination=source,format='nt');query.write_bytes(update)
            java,_=installed_tools();jar=local_root()/'runtimes/apache-jena-fuseki-6.1.0/fuseki-server.jar'
            run=subprocess.run([str(java),'-Xmx256m','-cp',str(jar),str(Path(__file__).parent/'fixtures/ClockStoreRoundTrip.java'),
                str(root/'tdb'),str(source),str(query),str(result)],capture_output=True,text=True,timeout=45)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertTrue(isomorphic(Graph().parse(result,format='nt'),delta+keep))

    def test_retained_clock_source_binding_cannot_be_transferred_to_another_game_source(self):
        # Source binding belongs to the shared retained-admission owner.
        h=T.module(T.HERE/'targeted-history-addition.py','clock_binding_test')
        proof=dict(sourceSha256='retained',graphRevalidation=dict(decision=T.DECISION,
            mode='current-clock-source-census',promotionSourceSha256='original',originalProofSha256='proof'))
        h.retain_source_binding(proof,dict(rawSha256='original'),'clockAdmission')
        self.assertEqual(proof['sourceSha256'],'retained')
        self.assertEqual(proof['sourceRevalidation']['originalProofSha256'],'proof')
        with self.assertRaisesRegex(ValueError,'unbound source'):
            h.retain_source_binding(copy.deepcopy(proof),dict(rawSha256='other'),'clockAdmission')

    def test_production_context_and_rml_keep_terminal_pitch_under_advisory(self):
        raw=(ROOT/'data/raw/samples/2026-07-18/824088.json').read_bytes()
        doc=json.loads(raw);doc['gamePk']=9824088
        last=doc['liveData']['plays']['allPlays'][-1]
        last['about']['isComplete']=False;last['result']['eventType']='game_advisory'
        self.assertTrue(any(e.get('isPitch') for e in last['playEvents']))
        with tempfile.TemporaryDirectory() as temporary:
            workspace=Path(temporary);source=workspace/'input.json';context=workspace/'game-context.json'
            source.write_text(json.dumps(doc),encoding='utf-8')
            subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(source),str(context)],
                check=True,capture_output=True,timeout=60)
            prepared=json.loads(context.read_bytes())
            self.assertEqual(prepared['_baseballO']['gameEndClocks'],[dict(value=last['about']['endTime'])])
            census=T.C.census(source.read_bytes(),str(doc['gamePk']))
            self.assertFalse(census['sourceReconciled']);self.assertTrue(census['graphSourceReconciled'])
            mapping=workspace/'mapping.ttl';T.W.A.subset_mapping(str(doc['gamePk']),mapping,('GameEndTimestampMap',))
            java,mapper=installed_tools();output=workspace/'clock.ttl'
            result=subprocess.run([str(java),'-Xmx256m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],
                cwd=workspace,capture_output=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            graph=Graph().parse(output)
            subject=URIRef(census['game']+'/timestamp/end');predicate=URIRef('https://www.commoncoreontologies.org/ont00001767')
            self.assertEqual({str(value) for value in graph.objects(subject,predicate)},
                {str(Literal(last['about']['endTime'],datatype=XSD.dateTime))})


if __name__=='__main__':unittest.main()
