"""An evidenced runner need not have a movement row to bear the runner role."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from rdflib import Graph, Namespace, RDF, URIRef
from test_rmlmapper_iterator_compatibility import ROOT, RR, installed_tools, materialized_subset


class StartOccupancyRoleRmlTests(unittest.TestCase):
    def test_occupancy_and_movement_reuse_one_persistent_role_without_realization(self):
        source = json.loads((ROOT / 'data/raw/game-566279.json').read_bytes())
        source['liveData']['plays']['allPlays'] = [dict(
            _baseballO=dict(startBaseOccupancies=[dict(runnerId='101'), dict(runnerId='102')]),
            runners=[dict(details=dict(runner=dict(id=102)))])]
        mapping = Graph().parse(ROOT / 'sources/mlb-game/mapping/mlb-game.rml.ttl')
        suffixes = {prefix + name for prefix in ('', 'StartOccupancy') for name in
                    ('BaserunnerRoleMap', 'BaserunnerRoleStasisMap', 'BaserunnerRoleStasisIntervalMap')}
        maps = [m for m in mapping.subjects(RDF.type, URIRef(RR + 'TriplesMap'))
                if str(m).split('#')[-1] in suffixes]
        self.assertEqual(len(maps), 6)
        with tempfile.TemporaryDirectory(prefix='baseballo-occupancy-role-') as temporary:
            workspace = Path(temporary)
            for name in ('game.json', 'game-context.json'):
                (workspace / name).write_text(json.dumps(source), encoding='utf-8')
            subset = materialized_subset(mapping, maps, workspace)
            java, mapper = installed_tools()
            output = workspace / 'roles.ttl'
            result = subprocess.run([str(java), '-Xmx256m', '-jar', str(mapper), '-m', str(subset),
                '-o', str(output), '-s', 'turtle', '-b', 'https://baseballontology.org/mapping/mlb-direct',
                '--strict'], cwd=workspace, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            graph = Graph().parse(output)
        base = Namespace('https://baseballontology.org/')
        bfo = Namespace('http://purl.obolibrary.org/obo/')
        cco = Namespace('https://www.commoncoreontologies.org/')
        self.assertEqual(len(set(graph.subjects(RDF.type, base.BaserunnerRole))), 2)
        for person_id in ('101', '102'):
            person = base['data/player/' + person_id]
            role = URIRef(str(person) + '/role/baserunner')
            stasis = URIRef(str(role) + '/stasis')
            self.assertIn((role, bfo.BFO_0000197, person), graph)
            self.assertIn((role, bfo.BFO_0000056, stasis), graph)
            self.assertIn((stasis, RDF.type, cco.ont00000824), graph)
            self.assertEqual(set(graph.objects(stasis, bfo.BFO_0000057)), {role, person})
            interval = URIRef(str(stasis) + '/temporal-interval')
            self.assertIn((stasis, bfo.BFO_0000199, interval), graph)
            self.assertIn((interval, RDF.type, bfo.BFO_0000038), graph)
        self.assertEqual(list(graph.triples((None, bfo.BFO_0000055, None))), [])
        self.assertEqual(list(graph.triples((None, cco.ont00001833, None))), [])


if __name__ == '__main__':
    unittest.main()
