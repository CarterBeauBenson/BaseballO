"""Actual D1 one-PA relay RML and source-bound SHACL before a game proof."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from pyshacl import validate
from rdflib import Graph, RDF, URIRef
from test_defensive_mapping import A, RAW, CONTEXT, ROOT, BASE, BFO, CCO

sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR


class DefensiveRmlTests(unittest.TestCase):
    def test_real_relay_rml_and_exact_source_shacl(self):
        workspace=Path(tempfile.mkdtemp(prefix='baseballo-d1-one-pa-'))
        (workspace/'game.json').write_bytes(RAW)
        subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),
            str(workspace/'game.json'),str(workspace/'complete.json')],check=True,capture_output=True)
        d=json.loads((workspace/'complete.json').read_bytes())
        d['liveData']['plays']['allPlays']=[d['liveData']['plays']['allPlays'][26]]
        for key in ('histories','episodeMembership'):d['_baseballO']['runnerHistoryReconciliation'][key]=[]
        for key in ('metricPitchReviews','metricAutomaticAwards'):d['_baseballO'][key]=[]
        source=CONTEXT.defensive_act_context(d);source['game']=BASE+'data/game/822693'
        (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
        maps=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        mapping=materialized_subset(maps,list(maps.subjects(RDF.type,URIRef(RR+'TriplesMap'))),workspace)
        java,mapper=installed_tools();output=workspace/'one-pa.ttl'
        result=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
            '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=workspace,capture_output=True)
        (workspace/'rml.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,str(workspace/'rml.log'))
        g=Graph().parse(output);shapes=Graph().parse(data=A.shape_text(source),format='turtle')
        conforms,report,text=validate(g,shacl_graph=shapes)
        self.assertTrue(conforms,text)
        acts={s for cls in (BASE.FieldingAttemptAct,BASE.CatchAttemptAct,BASE.ThrowAct,BASE.TagAttemptAct) for s in g.subjects(RDF.type,cls)}
        self.assertEqual(len(acts),7)
        self.assertFalse(list(g.subjects(RDF.type,BASE.TagAttemptAct)))
        self.assertFalse([(a,b) for a in acts for b in g.objects(a,BFO.BFO_0000063)])
        self.assertEqual(len({p for a in acts for p in g.objects(a,CCO.ont00001833)}),4)
        report.serialize(destination=workspace/'report.ttl',format='turtle')
        (workspace/'result.json').write_text(json.dumps(dict(scope='one-PA developer proof, no promotion',gamePk='822693',
            atBatIndex=26,triples=len(g),acts=7,agents=4,rmlPassed=True,sourceBoundShaclPassed=True,
            populationComplete=False,strictOrderAsserted=False),indent=2)+'\n',encoding='utf-8')
        print('D1 one-PA proof:',workspace)


if __name__=='__main__':unittest.main()
