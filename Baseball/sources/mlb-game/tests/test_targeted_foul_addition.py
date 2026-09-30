"""The repair runs five unchanged maps for exactly the failed foul pitches."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from rdflib import Graph, RDF, URIRef

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('foul_addition',ROOT/'sources/mlb-game/pipeline/targeted-foul-addition.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools


class FoulAddition(unittest.TestCase):
    def test_real_mapping_is_limited_to_recorded_missing_foul(self):
        raw=(ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        source=F.C.census(raw,'824087');pa=next(p for p in source['plateAppearances'] if p['pa'].endswith('/37'))
        event=next(e for e in pa['events'] if e.get('call')=='F' and e['strike'] and e['strikesAfter']==2)
        pid=event['playId'];strike=source['game']+'/process/strike/'+pid
        report=Graph().parse(data=f'''@prefix sh: <http://www.w3.org/ns/shacl#> .
            [] sh:sourceConstraintComponent sh:ClassConstraintComponent ; sh:focusNode <{strike}> .''',format='turtle')
        cases=F.recorded_fouls(source,report)
        self.assertEqual(cases,[dict(atBatIndex='37',playId=pid)])
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary);census=path/'source.json';F.W.atomic(census,source)
            case=dict(gamePk='824087',selected=cases,sourceCensus=str(census),sourceCensusSha256=F.W.sha(census))
            selected=F.select(raw,'824087',case)
            self.assertEqual([e['playId'] for e in selected['events']],[pid])
            context=path/'game-context.json';mapping=path/'addition.ttl'
            F.execution_inputs(raw,'824087',selected,context,mapping)
            maps=Graph().parse(mapping)
            self.assertEqual({str(m).rsplit('#',1)[1] for m in maps.subjects(RDF.type,
                URIRef('http://www.w3.org/ns/r2rml#TriplesMap'))},set(F.MAPS))
            java,mapper=installed_tools();output=path/'delta.ttl'
            run=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=path,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
            graph=Graph().parse(output)
            self.assertEqual(len(graph),14)
            self.assertTrue(all(str(s).endswith('/'+pid) for s in graph.subjects()))
            self.assertIn((URIRef(strike),RDF.type,URIRef('https://baseballontology.org/StrikeProcess')),graph)
            changed=json.loads(raw);changed['liveData']['plays']['allPlays'][37]['playEvents'][3]['startTime']='2026-07-20T00:00:00Z'
            with self.assertRaisesRegex(ValueError,'source is unresolved|outcome changed'):
                F.select(json.dumps(changed).encode(),'824087',case)


if __name__=='__main__':unittest.main()
