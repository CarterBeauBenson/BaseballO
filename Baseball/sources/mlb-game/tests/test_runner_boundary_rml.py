"""Actual C3 RML for one evidenced lifetime of each accepted boundary kind."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from pyshacl import validate
from rdflib import Graph, RDF, URIRef
from test_runner_boundary_anchors import A, ROOT, BASE, BFO

sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR


class RunnerBoundaryRml(unittest.TestCase):
    def test_accepted_boundaries_and_upheld_reviews_use_existing_personal_history_rml(self):
        for game,form,person in ((824233,'action',None),(823259,'replacement',None),(823989,'placement',None),
                                 (823826,'replacement','642201'),(825042,'replacement','699912'),(823585,'placement','666152')):
            with self.subTest(game=game,form=form):
                workspace=Path(tempfile.mkdtemp(prefix=f'baseballo-c3-{game}-{form}-'))
                raw=(ROOT/f'data/raw/samples/2026-08-25/{game}.json').read_bytes()
                (workspace/'game.json').write_bytes(raw)
                subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),
                    str(workspace/'game.json'),str(workspace/'complete.json')],check=True,capture_output=True)
                d=json.loads((workspace/'complete.json').read_bytes());history=d['_baseballO']['runnerHistoryReconciliation']
                row=next(h for h in history['histories'] if (h.get('entryWitness') or h.get('terminationWitness') or {}).get('form')==form
                         and (person is None or h['runnerId']==person))
                history['histories']=[row]
                history['placementAdjudications']=[r for r in history['placementAdjudications'] if r['lifetimeKey']==row['lifetimeKey']]
                history['episodeMembership']=[r for r in history['episodeMembership'] if r['lifetimeKey']==row['lifetimeKey']]
                pas={int(r['atBatIndex']) for r in row['episodes']}
                if row.get('entryAtBatIndex') is not None:pas.add(row['entryAtBatIndex'])
                d['liveData']['plays']['allPlays']=[p for p in d['liveData']['plays']['allPlays'] if p['atBatIndex'] in pas]
                for key in ('metricPitchReviews','metricAutomaticAwards'):d['_baseballO'][key]=[]
                (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
                maps=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
                mapping=materialized_subset(maps,list(maps.subjects(RDF.type,URIRef(RR+'TriplesMap'))),workspace)
                java,mapper=installed_tools();output=workspace/'one-history.ttl'
                result=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                    '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=workspace,capture_output=True,timeout=90)
                (workspace/'rml.log').write_bytes(result.stdout+result.stderr)
                self.assertEqual(result.returncode,0,str(workspace/'rml.log'))
                g=Graph().parse(output)
                census=dict(game=f'https://baseballontology.org/data/game/{game}',history=history)
                conforms,report,text=validate(g,shacl_graph=Graph().parse(data=A.shape_text(census),format='turtle'))
                self.assertTrue(conforms,text)
                whole=URIRef(census['game']+'/runner-trajectory/'+row['lifetimeKey'])
                self.assertEqual(len(list(g.objects(whole,BFO.BFO_0000117))),len(row['episodes'])+bool(row.get('placement')))
                self.assertEqual(list(g.objects(whole,BFO.BFO_0000057)),[URIRef(str(BASE)+'data/player/'+row['runnerId'])])
                report.serialize(destination=workspace/'report.ttl',format='turtle')
                (workspace/'result.json').write_text(json.dumps(dict(gamePk=game,form=form,triples=len(g),
                    episodes=len(row['episodes']),history=row,rmlPassed=True,sourceBoundShaclPassed=True,
                    scope='one-lifetime developer fixture; not game population admission'),indent=2)+'\n',encoding='utf-8')
                self.assertEqual((ROOT/f'data/raw/samples/2026-08-25/{game}.json').read_bytes(),raw)
                print('C3 one-history proof:',workspace)


if __name__=='__main__':unittest.main()
