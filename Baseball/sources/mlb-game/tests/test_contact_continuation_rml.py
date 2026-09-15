"""Explicit one-record B2 RML proof before the whole-game source gate."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rdflib import Graph, RDF, URIRef

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR
from test_contact_continuation import B2


class ContactContinuationRmlTests(unittest.TestCase):
    def test_real_contact_all_six_resolutions_through_rml_and_shacl(self):
        directory=Path(tempfile.mkdtemp(prefix='baseballo-b2-one-pa-'))
        source=ROOT/'data/raw/samples/2026-08-23/824315.json'
        (directory/'game.json').write_bytes(source.read_bytes())
        subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(source),str(directory/'complete-context.json')],
                       check=True,capture_output=True)
        context=json.loads((directory/'complete-context.json').read_bytes())
        context['liveData']['plays']['allPlays']=[context['liveData']['plays']['allPlays'][6]]
        for key in ('metricPitchReviews','countedFouls'):
            if key in context['_baseballO']: context['_baseballO'][key]=[]
        (directory/'game-context.json').write_text(json.dumps(context),encoding='utf-8')
        mapping_graph=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        mapping=materialized_subset(mapping_graph,list(mapping_graph.subjects(RDF.type,URIRef(RR+'TriplesMap'))),directory)
        java,mapper=installed_tools(); rdf=directory/'one-pa.ttl'
        result=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(rdf),'-s','turtle',
            '-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=directory,capture_output=True)
        (directory/'rmlmapper.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,str(directory/'rmlmapper.log'))
        # Restrict the conformance target to the one-record proof; full-source
        # reconciliation is still computed from the immutable complete source.
        census=B2.census(source.read_bytes(),'824315')
        census['plays']=[p for p in census['plays'] if p['atBatIndex']=='6']
        from pyshacl import validate
        conforms,report,description=validate(Graph().parse(rdf),shacl_graph=Graph().parse(data=B2.shape_text(census),format='turtle'))
        self.assertTrue(conforms,description)
        report.serialize(destination=directory/'report.ttl',format='turtle')
        print('B2 one-record actual RML and owning SHACL passed: '+str(directory))


if __name__=='__main__': unittest.main()
