"""The repair runs five unchanged maps for exactly the failed foul pitches."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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

    def test_exhausted_first_game_does_not_hide_later_recorded_repairs(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game/foul-addition'
            version=F.fingerprint()
            for pk in ('822678','999999'):
                F.W.atomic(state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json',
                           dict(promotedAtUtc='2026-10-01T00:00:00Z'))
            F.W.atomic(control/'822678.json',dict(status='failed',attempts=2,implementationSha256=version))
            marker=state/'pipeline/evidence/nifi/game-promotion/999999/promotion.json'
            case=dict(gamePk='999999',selected=[dict(atBatIndex='1',playId='recorded-foul')])
            F.W.atomic(control/'inventory.json',dict(games={'999999':dict(
                identity=[F.W.sha(marker),version],status='selected',case=case)}))
            self.assertEqual(F.next_case(state),case)

    def test_new_scope_can_follow_success_and_unchanged_failures_stop_at_two(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);case=dict(gamePk='1',selected=[dict(playId='later-foul')])
            control=state/'pipeline/control/mlb-game/foul-addition/1.json'
            F.W.atomic(control,dict(status='complete',implementationSha256=F.fingerprint(),
                caseSha256=F.case_sha(dict(gamePk='1',selected=[]))))
            with patch.object(F,'acquire',side_effect=ValueError('bounded-source-failure')) as acquire:
                self.assertEqual(F.tick(state,case,None,None,None)['attempts'],1)
                self.assertEqual(F.tick(state,case,None,None,None)['attempts'],2)
                self.assertEqual(F.tick(state,case,None,None,None)['attempts'],2)
                self.assertEqual(acquire.call_count,2)
            for pk in ('1','2'):
                F.W.atomic(state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json',dict(promotedAtUtc='now'))
            marker=lambda pk:state/'pipeline/evidence/nifi/game-promotion'/pk/'promotion.json'
            later=dict(gamePk='2',selected=[dict(playId='independent-foul')])
            F.W.atomic(control.parent/'inventory.json',dict(games={pk:dict(
                identity=[F.W.sha(marker(pk)),F.fingerprint()],status='selected',case=value)
                for pk,value in [('1',case),('2',later)]}))
            self.assertEqual(F.next_case(state),later)


if __name__=='__main__':unittest.main()
