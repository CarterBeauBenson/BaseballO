"""Offline check of F4 against exact retained inputs; never writes live state."""
import ast
import contextlib
import io
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path.cwd() / 'Baseball'
ACTIVE = ROOT / 'scripts/pipeline/prepare-rml-context.py'
PACKAGE = Path(__file__).resolve().parent
WORKSPACE = tempfile.TemporaryDirectory(prefix='f4-review-check-')
FOLDER = Path(WORKSPACE.name)
STATE = Path.home() / 'AppData/Local/BaseballO/state'
CASES = {
    '822682': ('243c7e7ed4d65b5c0dc3708eae57dfe2ba7d9edcd1a210305d84074ab9328caf', {
        50: '839f74ce-afdd-33dd-af88-490a45bcd322',
        58: 'c2e8b154-4bd4-3c13-b6c4-e20702e8e3de'}),
    '822688': ('a9c8d646ab48e1ec980254e49efd057cd2e1532392ad0e65b2521f97cd6e6fb3', {
        53: '32fa7d8b-6fc0-3079-93cd-187d2fb6f991'}),
}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


candidate_path = FOLDER / 'Baseball/scripts/pipeline/prepare-rml-context.py'
candidate_path.parent.mkdir(parents=True)
candidate_path.write_bytes(ACTIVE.read_bytes())
subprocess.run(['git', '-C', str(FOLDER), 'apply', str(PACKAGE / 'selection.patch')], check=True)
(FOLDER / ACTIVE.name).write_bytes(candidate_path.read_bytes())
(FOLDER / 'run-candidate.py').write_text(
    'from pathlib import Path\n__file__=' + repr(str(ACTIVE)) + '\n'
    'exec(compile(Path(' + repr(str(candidate_path)) + ').read_bytes(),__file__,"exec"))\n',
    encoding='utf-8')
OLD = module(ACTIVE, 'f4_baseline')
NEW = types.ModuleType('f4_candidate')
NEW.__file__ = str(ACTIVE)
exec(compile((FOLDER / ACTIVE.name).read_bytes(), str(ACTIVE), 'exec'), NEW.__dict__)
RAW = {pk: (STATE / 'pipeline/quarantine/mlb-game' / pk / 'targeted-foul/input.json').read_bytes()
       for pk in CASES}
DOCS = {}
for pk in CASES:
    source = FOLDER / (pk + '.input.json'); target = FOLDER / (pk + '.context.json')
    source.write_bytes(RAW[pk])
    with patch.object(sys, 'argv', [str(ACTIVE), str(source), str(target)]), contextlib.redirect_stdout(io.StringIO()):
        NEW.main()
    DOCS[pk] = json.loads(target.read_bytes())


def selected(document, pa, context=NEW):
    play = next(p for p in document['liveData']['plays']['allPlays'] if p['atBatIndex'] == pa)
    document['liveData']['plays']['allPlays'] = [play]
    return {r['playId'] for r in context.metric_pitch_context(document)['countedFouls']}


class F4(unittest.TestCase):
    def test_exact_sources_and_all_three_repaired_selections(self):
        for pk, (digest, cases) in CASES.items():
            self.assertEqual(hashlib.sha256(RAW[pk]).hexdigest(), digest)
            for pa, pid in cases.items():
                self.assertNotIn(pid, selected(copy.deepcopy(DOCS[pk]), pa, OLD))
                self.assertEqual(selected(copy.deepcopy(DOCS[pk]), pa), {pid})
        # The two PRs remain absent from the admitted personal histories.
        for pk, runner in [('822682', '683083'), ('822688', '687605')]:
            history = DOCS[pk]['_baseballO']['runnerHistoryReconciliation']
            pa = 50 if pk == '822682' else 53
            play = next(p for p in DOCS[pk]['liveData']['plays']['allPlays'] if p['atBatIndex'] == pa)
            event = play['playEvents'][0]
            self.assertTrue(NEW.zero_episode_replacement_witness(DOCS[pk], play, event))
            anchor = f"replacement/{play['about']['inning']}/{play['about']['halfInning']}/{event['replacedPlayer']['id']}/{runner}"
            self.assertFalse(any(h.get('entryAnchor') == anchor for h in history['histories']))

    def test_changed_or_ambiguous_pinch_runner_evidence_stays_excluded(self):
        faults = ('missing-ended', 'missing-withheld', 'duplicate-anchor', 'inconsistent',
                  'incoming', 'outgoing', 'base', 'time', 'batter', 'count', 'review',
                  'movement', 'strike', 'scoring', 'out', 'pinch-hitter')
        for pk, pa in [('822682', 50), ('822688', 53)]:
            for fault in faults:
                with self.subTest(pk=pk, fault=fault):
                    doc = copy.deepcopy(DOCS[pk])
                    play = next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex'] == pa)
                    event = play['playEvents'][0]
                    history = doc['_baseballO']['runnerHistoryReconciliation']
                    if fault == 'missing-ended': history['histories'] = []
                    elif fault == 'missing-withheld': history['withheldHistories'] = []
                    elif fault == 'duplicate-anchor': history['boundaryAnchorCensus'] *= 2
                    elif fault == 'inconsistent': history['sourceConsistency'] = 'inconsistent'
                    elif fault == 'incoming': event['player']['id'] = 1
                    elif fault == 'outgoing': event['replacedPlayer']['id'] = 1
                    elif fault == 'base': event['base'] = 3
                    elif fault == 'time': event['endTime'] = event['startTime']
                    elif fault == 'batter': play['matchup']['batter']['id'] = event['player']['id']
                    elif fault == 'count': event['count']['strikes'] = 1
                    elif fault == 'review': event['details']['hasReview'] = True
                    elif fault == 'movement': play['runners'][0]['details']['playIndex'] = 0
                    elif fault == 'strike': event['details']['isStrike'] = True
                    elif fault == 'scoring': event['details']['isScoringPlay'] = True
                    elif fault == 'out': event['details']['isOut'] = True
                    elif fault == 'pinch-hitter': event['position']['abbreviation'] = 'PH'
                    self.assertNotIn(CASES[pk][1][pa], selected(doc, pa))

    def test_unsupported_dh_switch_stays_excluded(self):
        for fault in ('roster', 'position', 'count', 'review', 'movement', 'strike', 'out'):
            with self.subTest(fault=fault):
                doc = copy.deepcopy(DOCS['822682'])
                play = next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex'] == 58)
                event = play['playEvents'][0]
                if fault == 'roster': doc['liveData']['boxscore']['teams']['home']['players'] = {}
                elif fault == 'position': event['position']['abbreviation'] = 'UNKNOWN'
                elif fault == 'count': event['count']['strikes'] = 1
                elif fault == 'review': event['details']['hasReview'] = True
                elif fault == 'movement': play['runners'][0]['details']['playIndex'] = 0
                elif fault == 'strike': event['details']['isStrike'] = True
                elif fault == 'out': event['details']['isOut'] = True
                self.assertNotIn(CASES['822682'][1][58], selected(doc, 58))

    def test_no_unrelated_context_definition_or_walk_selection_changes(self):
        def unrelated(raw):
            tree = ast.parse(raw)
            tree.body = [n for n in tree.body if getattr(n, 'name', None) != 'counted_foul_neutral_event']
            return ast.dump(tree)
        self.assertEqual(unrelated(ACTIVE.read_bytes()), unrelated((FOLDER / ACTIVE.name).read_bytes()))
        for doc in DOCS.values():
            for play in doc['liveData']['plays']['allPlays']:
                if play.get('result', {}).get('eventType') == 'intent_walk':
                    self.assertEqual(OLD.zero_pitch_walk_terminal(play, doc), NEW.zero_pitch_walk_terminal(play, doc))

    def test_existing_five_maps_emit_only_the_three_recorded_strikes(self):
        from rdflib import Graph, RDF, URIRef
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_rmlmapper_iterator_compatibility import installed_tools
        worker = module(ROOT / 'sources/mlb-game/pipeline/targeted-foul-addition.py', 'f4_worker')
        java, mapper = installed_tools()
        original_run = subprocess.run
        def context_run(args, **kwargs):
            return original_run([sys.executable, str(FOLDER / 'run-candidate.py'), *args[2:]], **kwargs)
        with tempfile.TemporaryDirectory(prefix='f4-mapping-') as temp:
            triples = 0
            for pk, (_, cases) in CASES.items():
                path = Path(temp) / pk
                path.mkdir()
                census = path / 'source.json'
                worker.W.atomic(census, worker.C.census(RAW[pk], pk))
                case = dict(gamePk=pk, sourceCensus=str(census), sourceCensusSha256=worker.W.sha(census),
                            selected=[dict(atBatIndex=str(pa), playId=pid) for pa, pid in cases.items()])
                with patch.object(worker.subprocess, 'run', side_effect=context_run):
                    delta = worker.select(RAW[pk], pk, case)
                self.assertEqual({e['playId'] for e in delta['events']}, set(cases.values()))
                self.assertEqual(delta['unresolvedFouls'], [])
                context = path / 'game-context.json'; mapping = path / 'addition.ttl'; output = path / 'delta.ttl'
                worker.execution_inputs(RAW[pk], pk, delta, context, mapping)
                result = original_run([str(java), '-Xmx256m', '-jar', str(mapper), '-m', str(mapping),
                    '-o', str(output), '-s', 'turtle', '-b', 'https://baseballontology.org/mapping/mlb-direct',
                    '--strict'], cwd=path, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                graph = Graph().parse(output)
                self.assertEqual(len(graph), 14 * len(cases))
                self.assertTrue(all(str(s).rsplit('/', 1)[-1] in cases.values() for s in graph.subjects()))
                for pid in cases.values():
                    self.assertIn((URIRef('https://baseballontology.org/data/game/' + pk + '/process/strike/' + pid),
                        RDF.type, URIRef('https://baseballontology.org/StrikeProcess')), graph)
                triples += len(graph)
            self.assertEqual(triples, 42)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'sources/mlb-game/tests'))
    import test_c3_count_prefix as c3
    import test_zero_pitch_walk_prefix as w1
    c3.CONTEXT = NEW; w1.CONTEXT = NEW
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(F4),
        unittest.defaultTestLoader.loadTestsFromModule(c3), unittest.defaultTestLoader.loadTestsFromModule(w1)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
