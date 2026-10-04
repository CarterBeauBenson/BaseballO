"""Check W3 in a disposable module; no RML, acquisition or graph writes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parent
ROOT = next(p for p in PACKAGE.parents if (p/'scripts/pipeline/prepare-rml-context.py').is_file())
ACTIVE = ROOT/'scripts/pipeline/prepare-rml-context.py'
EVIDENCE = json.loads((PACKAGE/'evidence.json').read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
WORK = tempfile.TemporaryDirectory(prefix='w3-final-award-check-')
FOLDER = Path(WORK.name)
candidate = FOLDER/'Baseball/scripts/pipeline/prepare-rml-context.py'
candidate.parent.mkdir(parents=True)
assert sha(ACTIVE) in {EVIDENCE['previousContextSha256'], EVIDENCE['candidateContextSha256']}
candidate.write_bytes(ACTIVE.read_bytes())
if sha(ACTIVE) == EVIDENCE['previousContextSha256']:
    subprocess.run(['git', '-c', 'core.autocrlf=false', '-C', str(FOLDER), 'apply',
                    str(PACKAGE/'selection.patch')], check=True)
assert sha(candidate) == EVIDENCE['candidateContextSha256']
NEW = types.ModuleType('w3_candidate')
NEW.__file__ = str(ACTIVE)
exec(compile(candidate.read_bytes(), str(ACTIVE), 'exec'), NEW.__dict__)
spec = importlib.util.spec_from_file_location('w3_count_owner', ROOT/'sources/mlb-game/pipeline/pitch-count-admission.py')
COUNT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(COUNT)
CASES = []
for case in EVIDENCE['cases']:
    witness = case['sourceWitness']
    assert sha(witness['path']) == witness['sha256']
    doc = json.loads(Path(witness['path']).read_bytes())
    play = next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex'] == case['atBatIndex'])
    CASES.append((case, doc, play))


def awards(doc, play):
    return NEW.runner_metric_evidence(play, str(play['atBatIndex']),
        str(doc['gameData']['game']['season']), document=doc)['awardAdvances']


class FinalAwardSelection(unittest.TestCase):
    def test_five_exact_awards_preserve_source_and_exclude_earlier_steals(self):
        for case, doc, play in CASES:
            with self.subTest(game=case['gamePk'], pa=case['atBatIndex']):
                before = copy.deepcopy(doc)
                rows = awards(doc, play)
                self.assertEqual([(r['runnerIndex'], r['runnerId']) for r in rows],
                                 [(str(case['runnerIndex']), str(case['runnerId']))])
                self.assertEqual(rows[0]['ruleCode'], '5.05(b)(2)' if case['result']=='hit_by_pitch' else '5.05(b)(1)')
                self.assertEqual(doc, before)
                self.assertEqual([e['playId'] for e in play['playEvents'] if e.get('isPitch') is True], case['physicalPitchIds'])

    def test_incomplete_or_contradictory_awards_remain_excluded(self):
        for case, doc, play in CASES:
            for fault in ('incomplete', 'missing-post-first', 'wrong-post-first', 'runner-out', 'wrong-destination', 'duplicate-runner', 'wrong-terminal-join'):
                with self.subTest(game=case['gamePk'], fault=fault):
                    p = copy.deepcopy(play)
                    row = p['runners'][case['runnerIndex']]
                    if fault == 'incomplete': p['about']['isComplete'] = False
                    elif fault == 'missing-post-first': p['matchup'].pop('postOnFirst')
                    elif fault == 'wrong-post-first': p['matchup']['postOnFirst']['id'] = 1
                    elif fault == 'runner-out': row['movement']['isOut'] = True
                    elif fault == 'wrong-destination': row['movement']['end'] = '2B'
                    elif fault == 'duplicate-runner': p['runners'].append(copy.deepcopy(row))
                    else: row['details']['playIndex'] = 999
                    self.assertEqual(awards(doc, p), [])

    def test_counter_contradictions_and_nonterminal_runner_effects_are_excluded(self):
        for case, doc, play in CASES:
            if case['result'] != 'intent_walk': continue
            for fault in ('gap', 'physical-terminal', 'strike', 'count', 'outs', 'review', 'in-play', 'substitution', 'scoring', 'bool-count'):
                with self.subTest(game=case['gamePk'], fault=fault):
                    p = copy.deepcopy(play)
                    e = p['playEvents'][-1]
                    if fault == 'gap': p['playEvents'][0]['index'] = 999
                    elif fault == 'physical-terminal': e['isPitch'] = True
                    elif fault == 'strike': e['details']['isStrike'] = True
                    elif fault == 'count': e['count']['balls'] = 3
                    elif fault == 'outs': e['count']['outs'] = 3
                    elif fault == 'review': e['details']['hasReview'] = True
                    elif fault == 'in-play': e['details']['isInPlay'] = True
                    elif fault == 'substitution': e['isSubstitution'] = True
                    elif fault == 'scoring': e['details']['isScoringPlay'] = True
                    else: e['count']['strikes'] = False
                    self.assertEqual(awards(doc, p), [])
            if len(play['playEvents']) > 4:
                p = copy.deepcopy(play)
                row = copy.deepcopy(p['runners'][case['runnerIndex']])
                row['details']['playIndex'] = p['playEvents'][-2]['index']
                p['runners'].append(row)
                self.assertIsNone(NEW.intentional_walk_award_terminal(p))

    def test_unresolved_or_contradictory_hbp_review_is_not_accepted(self):
        for case, doc, play in CASES:
            if case['result'] != 'hit_by_pitch': continue
            for fault in ('pending', 'missing-disposition', 'contradictory-disposition', 'wrong-call'):
                with self.subTest(game=case['gamePk'], fault=fault):
                    p = copy.deepcopy(play)
                    if fault == 'pending': p['reviewDetails']['inProgress'] = True
                    elif fault == 'missing-disposition': p.pop('reviewDetails')
                    elif fault == 'contradictory-disposition': p['reviewDetails']['isOverturned'] = not p['reviewDetails']['isOverturned']
                    else: p['playEvents'][-1]['details']['call']['code'] = 'B'
                    self.assertEqual(awards(doc, p), [])

    def test_mixed_pitch_walks_are_not_reclassified_as_zero_pitch(self):
        for case, doc, play in CASES:
            if case['result'] != 'intent_walk' or not case['physicalPitchIds']: continue
            with self.subTest(game=case['gamePk']), patch.object(COUNT, 'CONTEXT', NEW):
                self.assertIsNotNone(NEW.intentional_walk_award_terminal(play))
                self.assertFalse(COUNT.virtual_intentional_walk(play, doc['gameData']['game']['season'], doc))


if __name__ == '__main__':
    unittest.main()
