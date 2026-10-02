"""Offline regression for the recorded F5/D2 failures; no live graph writes.

Requires the exact pre-implementation context and retained failed inputs/RDF.
NiFi remains responsible for RML, full source SHACL and additive promotion.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from rdflib import Graph, Namespace, RDF, URIRef

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
ACTIVE = ROOT / 'scripts/pipeline/prepare-rml-context.py'
EVIDENCE = json.loads((PACKAGE / 'evidence.json').read_bytes())
WORKSPACE = tempfile.TemporaryDirectory(prefix='f5-d2-check-')
FOLDER = Path(WORKSPACE.name)
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(ACTIVE) == EVIDENCE['previousContextSha256']
candidate = FOLDER / 'Baseball/scripts/pipeline/prepare-rml-context.py'
candidate.parent.mkdir(parents=True)
candidate.write_bytes(ACTIVE.read_bytes())
subprocess.run(['git', '-c', 'core.autocrlf=false', '-C', str(FOLDER), 'apply', str(PACKAGE / 'selection.patch')], check=True)
assert sha(candidate) == EVIDENCE['currentContextSha256']
NEW = types.ModuleType('f5_d2_candidate')
NEW.__file__ = str(ACTIVE)
exec(compile(candidate.read_bytes(), str(ACTIVE), 'exec'), NEW.__dict__)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F = module(ROOT / 'sources/mlb-game/pipeline/targeted-foul-addition.py', 'f5_addition')
D = module(ROOT / 'sources/mlb-game/pipeline/defensive-admission.py', 'd2_admission')
D.CONTEXT = NEW
DOCS = {}
for case in EVIDENCE['fouls']:
    witness = case['sourceWitness']
    assert sha(witness['path']) == witness['sha256']
    output = FOLDER / (case['gamePk'] + '.context.json')
    with patch.object(sys, 'argv', ['context', witness['path'], str(output)]), contextlib.redirect_stdout(io.StringIO()):
        NEW.main()
    DOCS[case['gamePk']] = json.loads(output.read_bytes())


def selected(pk, pa, change=lambda p, d: None):
    doc = copy.deepcopy(DOCS[pk])
    play = next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex'] == pa)
    doc['liveData']['plays']['allPlays'] = [play]
    change(play, doc)
    return NEW.metric_pitch_context(doc)['countedFouls']


class RecordedFailures(unittest.TestCase):
    def test_all_recorded_fouls_pass_the_existing_exact_identity_selection(self):
        for case in EVIDENCE['fouls']:
            pk = case['gamePk']
            def context(args, **kwargs):
                Path(args[-1]).write_text(json.dumps(DOCS[pk]), encoding='utf-8')
            with self.subTest(game=pk), patch.object(F.subprocess, 'run', side_effect=context):
                chosen = F.select(Path(case['sourceWitness']['path']).read_bytes(), pk, case['case'])
                self.assertEqual({e['playId'] for e in chosen['events']},
                                 {e['playId'] for e in case['case']['selected']})
                self.assertEqual(chosen['unresolvedFouls'], [])

    def test_each_recorded_defensive_census_matches_retained_rdf(self):
        sh = Namespace('http://www.w3.org/ns/shacl#')
        for case in EVIDENCE['defense']:
            with self.subTest(game=case['gamePk']):
                witness = case['sourceWitness']
                self.assertEqual(sha(witness['path']), witness['sha256'])
                self.assertEqual(sha(case['rdfPath']), case['rdfSha256'])
                source = D.census(Path(witness['path']).read_bytes(), case['gamePk'])
                self.assertEqual(source['status'], 'reconciled')
                shape = Graph().parse(data=D.shape_text(source), format='turtle')
                graph = Graph().parse(case['rdfPath'], format='nt')
                for query in shape.objects(None, sh.select):
                    self.assertEqual(list(graph.query(str(query).replace('$this', '?this'))), [])
                self.assertTrue(all((URIRef(a['actIri']), None, None) in graph for a in source['acts']))

    def test_unchanged_foul_maps_emit_only_the_selected_strike(self):
        case = next(c for c in EVIDENCE['fouls'] if c['gamePk'] == '822794')
        def context(args, **kwargs):
            Path(args[-1]).write_text(json.dumps(DOCS['822794']), encoding='utf-8')
        raw = Path(case['sourceWitness']['path']).read_bytes()
        with patch.object(F.subprocess, 'run', side_effect=context):
            selected = F.select(raw, '822794', case['case'])
        folder = FOLDER / 'mapping'; folder.mkdir()
        mapping = folder / 'addition.rml.ttl'; output = folder / 'addition.ttl'
        F.execution_inputs(raw, '822794', selected, folder / 'game-context.json', mapping)
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_rmlmapper_iterator_compatibility import installed_tools
        java, mapper = installed_tools()
        result = subprocess.run([str(java), '-Xmx256m', '-jar', str(mapper), '-m', str(mapping),
            '-o', str(output), '-s', 'turtle', '-b', 'https://baseballontology.org/mapping/mlb-direct', '--strict'],
            cwd=folder, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        graph = Graph().parse(output)
        pid = case['case']['selected'][0]['playId']
        self.assertEqual(len(graph), 14)
        self.assertTrue(all(str(subject).endswith('/' + pid) for subject in graph.subjects()))
        self.assertIn((URIRef('https://baseballontology.org/data/game/822794/process/strike/' + pid),
                       RDF.type, URIRef('https://baseballontology.org/StrikeProcess')), graph)

    def test_placement_requires_its_exact_existing_witness(self):
        for fault in ('witness', 'judgment', 'runner', 'base', 'counter', 'clock'):
            def change(p, d):
                e = next(e for e in p['playEvents'] if e['details'].get('eventType') == 'runner_placed')
                h = d['_baseballO']['runnerHistoryReconciliation']
                if fault == 'witness': h['boundaryAnchorCensus'] = []
                if fault == 'judgment': h['placementAdjudications'] = []
                if fault == 'runner': e['player']['id'] = 1
                if fault == 'base': e['base'] = 3
                if fault == 'counter': e['count']['strikes'] = 1
                if fault == 'clock': e['endTime'] = e['startTime']
            self.assertFalse(selected('822690', 78, change), fault)

    def test_substitutions_require_the_recorded_participants_and_counts(self):
        for pk, pa, kind in [('822731', 71, 'pitching_substitution'),
                             ('822832', 79, 'pitching_substitution'),
                             ('822854', 9, 'offensive_substitution')]:
            for fault in ('incoming', 'count', 'review', 'agency'):
                def change(p, d):
                    e = next(e for e in p['playEvents'] if e['details'].get('eventType') == kind)
                    if fault == 'incoming': e['player']['id'] = 1
                    if fault == 'count': e['count']['strikes'] += 1
                    if fault == 'review': e['details']['hasReview'] = True
                    if fault == 'agency':
                        pitch = next(v for v in p['playEvents'][e['index']+1:] if v.get('isPitch'))
                        pitch['_baseballO']['pitcherId' if kind == 'pitching_substitution' else 'batterId'] = '1'
                self.assertFalse(selected(pk, pa, change), (pk, fault))

    def test_unfinished_or_contradictory_reviews_still_withhold(self):
        for pk, pa in [('822717', 67), ('822794', 77)]:
            for fault in ('pending', 'code', 'disposition'):
                def change(p, d):
                    r = p['reviewDetails'] if pk == '822717' else p['playEvents'][0]['reviewDetails']
                    if fault == 'pending': r['inProgress'] = True
                    if fault == 'code': r['reviewType'] = 'unknown'
                    if fault == 'disposition': r['isOverturned'] = None
                self.assertFalse(selected(pk, pa, change), (pk, fault))

    def test_administration_does_not_hide_movement_or_pitch_overlap(self):
        for fault in ('counter', 'out', 'movement', 'pitch-overlap'):
            def change(p, d):
                e = next(e for e in p['playEvents'] if e['details'].get('eventType') == 'mound_visit')
                if fault == 'counter': e['count']['strikes'] += 1
                if fault == 'out': e['details']['isOut'] = True
                if fault == 'movement': p['runners'][0]['details']['playIndex'] = e['index']
                if fault == 'pitch-overlap':
                    pitches = [e for e in p['playEvents'] if e.get('isPitch')]
                    pitches[1]['startTime'] = pitches[0]['startTime']
            self.assertFalse(selected('822727', 34, change), fault)

    def test_punctuated_names_still_require_unique_roster_and_putout_support(self):
        case = EVIDENCE['defense'][0]
        original = json.loads(Path(case['sourceWitness']['path']).read_bytes())
        play = next(p for p in original['liveData']['plays']['allPlays']
                    if p['result']['eventType'] == 'field_out'
                    and 'to center fielder A.J. Ewing.' in p['result']['description'])
        for fault in (None, 'credit', 'unknown-name', 'duplicate-name'):
            doc = copy.deepcopy(original)
            doc['liveData']['plays']['allPlays'] = [copy.deepcopy(play)]
            doc['_baseballO'] = dict(runnerHistoryReconciliation=dict(sourceConsistency='consistent', inputSha256=case['sourceWitness']['sha256'], sourceRevision='recorded'))
            p = doc['liveData']['plays']['allPlays'][0]
            if fault == 'credit':
                for r in p['runners']: r['credits'] = []
            if fault == 'unknown-name': p['result']['description'] = p['result']['description'].replace('A.J. Ewing', 'A.J. Unknown')
            if fault == 'duplicate-name':
                side = 'home' if p['about']['isTopInning'] else 'away'
                doc['liveData']['boxscore']['teams'][side]['players']['ID1'] = dict(person=dict(id=1, fullName='A.J. Ewing'))
            self.assertEqual(bool(NEW.defensive_act_context(doc)['acts']), fault is None, fault)


if __name__ == '__main__':
    unittest.main()
