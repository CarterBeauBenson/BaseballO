"""One-PA proof of the actual M1/M2 RML before the bounded whole-game check.

Run explicitly; this invokes installed RMLMapper. It never promotes a graph.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR
from test_metric_mapping_completion import CONTEXT, SHAPE, BASE, BFO, CCO


class ActualRmlTests(unittest.TestCase):
    def test_one_pa_counted_foul_and_review(self):
        workspace = Path(tempfile.mkdtemp(prefix='baseballo-m1m2-one-pa-'))
        raw=(ROOT/'data/raw/samples/2026-08-23/824315.json').read_bytes()
        (workspace/'game.json').write_bytes(raw)
        subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),
                        str(workspace/'game.json'),str(workspace/'complete-context.json')],check=True,capture_output=True)
        d=json.loads((workspace/'complete-context.json').read_bytes())
        d['liveData']['plays']['allPlays']=[d['liveData']['plays']['allPlays'][36]]
        # This disposable test view is explicitly one PA, never a complete game.
        histories=d['_baseballO']['runnerHistoryReconciliation']
        histories['histories']=[]; histories['episodeMembership']=[]
        d['_baseballO']['metricPitchReviews']=[r for r in d['_baseballO']['metricPitchReviews'] if r['atBatIndex']=='36']
        (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
        mapping_graph=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        maps=list(mapping_graph.subjects(RDF.type,URIRef(RR+'TriplesMap')))
        mapping=materialized_subset(mapping_graph,maps,workspace)
        java,mapper=installed_tools(); output=workspace/'one-pa.ttl'
        command=[str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),'-s','turtle',
                 '-b','https://baseballontology.org/mapping/mlb-direct','--strict']
        result=subprocess.run(command,cwd=workspace,capture_output=True)
        (workspace/'rmlmapper.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,str(workspace/'rmlmapper.log'))
        g=Graph().parse(output); row,=d['_baseballO']['metricPitchReviews']
        self.assertIn((URIRef(row['reviewIri']),RDF.type,BASE.BaseballReplayReviewAct),g)
        self.assertIn((URIRef(row['reviewIri']),CCO.ont00001921,URIRef(row['originalDecisionIri'])),g)
        self.assertIn((URIRef(row['originalJudgmentIri']),CCO.ont00001833,None),g)
        self.assertFalse(list(g.objects(URIRef(row['reviewIri']),BFO.BFO_0000055)))
        foul=URIRef('https://baseballontology.org/data/game/824315/process/strike/c418c4d5-e276-37e7-834c-ddb953da73b2')
        self.assertIn((foul,RDF.type,BASE.StrikeProcess),g)
        shapes=Graph().parse(ROOT/'sources/mlb-game/shacl/authoritative.ttl')
        conforms,_,report=validate(g,shacl_graph=shapes,use_shapes=[str(SHAPE.CountedFoulStrikeShape),
            str(SHAPE.M2OriginalJudgmentTargetShape),str(SHAPE.M2OriginalJudgmentShape),str(SHAPE.M2OperativeReviewShape)])
        self.assertTrue(conforms,report)
        (workspace/'result.json').write_text(json.dumps({'scope':'one-PA developer proof, no promotion',
            'gamePk':'824315','atBatIndex':36,'triples':len(g),'rmlPassed':True,'focusedShaclPassed':True,
            'reviewIri':row['reviewIri'],'countedFoulIri':str(foul)},indent=2)+'\n',encoding='utf-8')
        print(f'One-PA RML and M1/M2 SHACL proof: {workspace}')

        # Synthetic duplicate narrative at the same terminal reviewed pitch.
        # Reuse actual source fields; explicitly not a second real-game proof.
        p=d['liveData']['plays']['allPlays'][0]
        p['playEvents']=p['playEvents'][:6]
        p['about']['hasReview']=True
        p['_baseballO'].update(hasReview=True,hasReviewStatus=True,hasReviewChallengerId=False,
            reviewType='pitch_result',reviewInitiation='umpire_review',reviewStatus='confirmed',
            reviewOutcome='affirming',reviewOriginalDecision='ball',reviewFinalDecision='ball',reviewPattern='ball_to_ball',
            terminalPitchPlayId=p['playEvents'][-1]['playId'])
        CONTEXT.metric_pitch_context(d)
        (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
        duplicate_output=workspace/'duplicate-narrative.ttl'
        duplicate_command=command.copy()
        duplicate_command[duplicate_command.index('-o')+1]=str(duplicate_output)
        result=subprocess.run(duplicate_command,cwd=workspace,capture_output=True)
        (workspace/'duplicate-narrative.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        g=Graph().parse(duplicate_output); row,=d['_baseballO']['metricPitchReviews']
        expected=URIRef('https://baseballontology.org/data/game/824315/review/36/act')
        self.assertEqual(set(g.subjects(RDF.type,BASE.BaseballReplayReviewAct)),{expected})
        self.assertEqual(row['reviewIri'],str(expected))
        self.assertNotIn((URIRef('https://baseballontology.org/data/game/824315/judgment/ball/'+row['playId']),None,None),g)
        conforms,_,report=validate(g,shacl_graph=shapes,use_shapes=[str(SHAPE.M2OriginalJudgmentTargetShape),
            str(SHAPE.M2OriginalJudgmentShape),str(SHAPE.M2OperativeReviewShape)])
        self.assertTrue(conforms,report)
        (workspace/'duplicate-narrative-result.json').write_text(json.dumps({'scope':'synthetic duplicate narrative',
            'rmlPassed':True,'focusedShaclPassed':True,'distinctReviews':1},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    unittest.main()
