"""Real one-PA M4 RML proof, before the whole-game developer proof."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pyshacl import validate
from rdflib import Graph, RDF, URIRef
from test_metric_mapping_completion import ROOT, BASE, BFO, CCO, SHAPE

sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR


class FoulBuntRmlTests(unittest.TestCase):
    def test_real_first_strike_bunt_full_pattern(self):
        workspace=Path(tempfile.mkdtemp(prefix='baseballo-m4-one-pa-'))
        (workspace/'game.json').write_bytes((ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes())
        context=workspace/'complete.json'
        subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),
            str(ROOT/'data/raw/samples/2026-07-20/824087.json'),str(context)],check=True,capture_output=True)
        d=json.loads(context.read_bytes());p=d['liveData']['plays']['allPlays'][72]
        d['liveData']['plays']['allPlays']=[p]
        d['_baseballO']['runnerHistoryReconciliation']['histories']=[]
        d['_baseballO']['runnerHistoryReconciliation']['episodeMembership']=[]
        d['_baseballO']['metricPitchReviews']=[]
        d['_baseballO']['metricAutomaticAwards']=[]
        d['_baseballO']['defensiveActs']=[]
        (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
        maps=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        mapping=materialized_subset(maps,list(maps.subjects(RDF.type,URIRef(RR+'TriplesMap'))),workspace)
        java,mapper=installed_tools();output=workspace/'one-pa.ttl'
        result=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
            '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=workspace,capture_output=True)
        (workspace/'rml.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,str(workspace/'rml.log'))
        g=Graph().parse(output);root='https://baseballontology.org/data/game/824087/'
        pid=p['playEvents'][0]['playId'];u=lambda kind:URIRef(root+kind+'/'+pid)
        for kind,cls in [('process/strike',BASE.StrikeProcess),('judgment/strike',BASE.StrikeJudgmentAct),
            ('decision/strike',BASE.StrikeDecisionICE),('act/bunt',BASE.BuntAct),('process/contact',BASE.BatBallContactProcess),
            ('process/foul-ball',BASE.FoulBallProcess),('pitch',BASE.PitchAct)]:
            self.assertIn((u(kind),RDF.type,cls),g)
            self.assertIn((u('event-record/pitch'),CCO.ont00001808,u(kind)),g)
        self.assertIn((u('act/bunt'),BFO.BFO_0000057,URIRef('https://baseballontology.org/data/player/679845')),g)
        self.assertNotIn((u('process/strike'),RDF.type,BASE.StrikeoutProcess),g)
        shapes=Graph().parse(ROOT/'sources/mlb-game/shacl/authoritative.ttl')
        check=lambda:validate(g,shacl_graph=shapes,use_shapes=[str(SHAPE.CountedFoulStrikeShape)])[0]
        self.assertTrue(check())
        for triple in [(u('judgment/strike'),CCO.ont00001921,BASE['data/rule/strike']),
                       (u('event-record/pitch'),CCO.ont00001808,u('decision/strike'))]:
            g.remove(triple);self.assertFalse(check());g.add(triple)
        (workspace/'result.json').write_text(json.dumps(dict(scope='one-PA developer proof, no promotion',
            gamePk='824087',atBatIndex=72,triples=len(g),rmlPassed=True,focusedShaclPassed=True,
            mutationChecksPassed=True),indent=2)+'\n',encoding='utf-8')
        print('One-PA M4 proof:',workspace)


if __name__=='__main__':unittest.main()
