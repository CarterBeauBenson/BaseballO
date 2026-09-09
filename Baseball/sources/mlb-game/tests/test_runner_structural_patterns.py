"""Source evidence and conformance tests for the user's structural correction."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests'))
from runner_pattern_fixture import BASE, BFO, CCO, movement, award

SPEC = importlib.util.spec_from_file_location('episode_context', ROOT / 'scripts/pipeline/prepare-rml-context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
SHAPE = Namespace('https://w3id.org/baseball/shacl/')
DATA = Namespace('https://baseballontology.org/data/')


class RunnerEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plays = json.loads((ROOT / 'data/raw/game-566279.json').read_bytes())['liveData']['plays']['allPlays']

    def test_mixed_steal_and_score_keep_the_existing_pairs(self):
        evidence = CONTEXT.runner_episode_evidence(self.plays[23], '23')
        self.assertEqual([(r['runnerIndex'], r['baseCode']) for r in evidence['safeDecisionDestinations']], [('0', '2B'), ('1', '1B')])
        self.assertEqual(evidence['runnerEpisodes'][2]['resolutionKind'], 'score')
        self.assertEqual(len({r['runnerIndex'] for r in evidence['runnerEpisodes']}), 3)

    def test_null_and_invalid_runner_rows_do_not_acquire_episodes(self):
        for is_out, runner in [(None, 1), ('false', 1), (False, None), (False, True)]:
            play = {'runners': [{'movement': {'isOut': is_out}, 'details': {'runner': {'id': runner}}}]}
            self.assertEqual(CONTEXT.runner_episode_evidence(play, '1')['runnerEpisodes'], [])

    def test_incomplete_or_unknown_destination_withholds_decision_base(self):
        play = json.loads(json.dumps(self.plays[2]))
        play['about']['isComplete'] = False
        self.assertEqual(CONTEXT.runner_episode_evidence(play, '2')['safeDecisionDestinations'], [])
        play['about']['isComplete'] = True
        play['runners'][0]['movement']['end'] = None
        self.assertEqual(CONTEXT.runner_episode_evidence(play, '2')['safeDecisionDestinations'], [])

    def test_start_and_award_rows_do_not_manufacture_persistence_or_directives(self):
        for play in self.plays:
            result = CONTEXT.runner_episode_evidence(play, str(play['about']['atBatIndex']))
            self.assertEqual(set(result), {'runnerEpisodes', 'safeDecisionDestinations'})


class RunnerPatternShaclTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile = Graph().parse(ROOT / 'sources/mlb-game/shacl/authoritative.ttl')
        cls.shapes = Graph()
        pending = [SHAPE[x] for x in ['RunnerResolutionEpisodeShape', 'SafeDecisionDestinationShape',
                    'SegmentOriginDesignationShape', 'AwardCausedAdvanceShape', 'WithdrawnAwardDirectiveShape', 'WithdrawnRunnerPropertiesShape', 'JudgmentShape', 'DecisionShape',
                    'BaserunnerAtBaseStasisShape']]
        visited = set()
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            for triple in profile.triples((node, None, None)):
                cls.shapes.add(triple)
                if isinstance(triple[2], BNode) or str(triple[2]).startswith(str(SHAPE)):
                    pending.append(triple[2])

    def graph(self):
        g = Graph()
        self.pa = DATA['game/1/plate-appearance/2']
        self.rr = DATA['game/1/runner-resolution/reach/2/0']
        self.act = DATA['game/1/runner-act/movement/2/0']
        self.runner = DATA['player/1']
        self.base = DATA['venue/2/artifact/base/2B']
        self.field = DATA['venue/2/baseball-field']
        self.role = DATA['player/1/role/baserunner']
        self.record = DATA['game/1/runner-record/2/0']
        self.episode, self.judgment, self.decision = movement(g, self.rr, self.act, self.pa, self.runner, destination=self.base)
        code = URIRef(str(self.base) + '/identifier/source-base-code')
        for triple in [(self.pa, RDF.type, BASE.PlateAppearance), (self.rr, BFO.BFO_0000057, self.runner),
                       (self.act, BFO.BFO_0000055, self.role), (self.role, RDF.type, BASE.BaserunnerRole),
                       (self.role, BFO.BFO_0000197, self.runner), (self.act, CCO.ont00001918, self.field),
                       (self.rr, CCO.ont00001918, self.field), (self.record, RDF.type, BASE.BaseballEventRecord),
                       (code, RDF.type, CCO.ont00000649), (code, CCO.ont00001916, self.base),
                       (code, CCO.ont00001765, Literal('2B'))]: g.add(triple)
        for entity in [self.episode, self.act, self.rr, self.decision]:
            g.add((self.record, CCO.ont00001808, entity))
        return g

    def conforms(self, graph):
        ok, _, report = validate(graph, shacl_graph=self.shapes)
        return ok, report

    def test_valid_episode_and_safe_decision(self):
        ok, report = self.conforms(self.graph())
        self.assertTrue(ok, report)

    def test_mismatched_or_ambiguous_paths_are_rejected(self):
        for fault in ['agent', 'two-agents', 'role', 'precedence', 'pa', 'field', 'record', 'duplicate-episode', 'extra-part', 'two-bases', 'wrong-base', 'missing-code', 'extra-about']:
            with self.subTest(fault=fault):
                g = self.graph()
                if fault == 'agent': g.remove((self.act, CCO.ont00001833, None))
                elif fault == 'two-agents': g.add((self.act, CCO.ont00001833, DATA['player/2']))
                elif fault == 'role': g.set((self.role, BFO.BFO_0000197, DATA['player/2']))
                elif fault == 'precedence': g.remove((self.rr, BFO.BFO_0000062, None))
                elif fault == 'pa': g.set((self.act, BFO.BFO_0000132, DATA['game/1/plate-appearance/3']))
                elif fault == 'field': g.set((self.act, CCO.ont00001918, DATA['venue/3/baseball-field']))
                elif fault == 'record': g.remove((self.record, CCO.ont00001808, self.episode))
                elif fault == 'duplicate-episode':
                    g.add((DATA.otherEpisode, RDF.type, BASE.RunnerResolutionEpisode))
                    g.add((DATA.otherEpisode, BFO.BFO_0000117, self.rr))
                elif fault == 'extra-part': g.add((self.episode, BFO.BFO_0000117, DATA.untyped))
                elif fault in {'two-bases', 'wrong-base'}:
                    if fault == 'wrong-base': g.remove((self.decision, CCO.ont00001808, self.base))
                    g.add((DATA.otherBase, RDF.type, BASE.Base))
                    g.add((self.decision, CCO.ont00001808, DATA.otherBase))
                elif fault == 'missing-code': g.remove((None, CCO.ont00001765, None))
                else: g.add((self.decision, CCO.ont00001808, DATA.untyped))
                self.assertFalse(self.conforms(g)[0])

    def origin_graph(self):
        g = self.graph()
        origin = URIRef(str(self.record) + '/origin-designation')
        base = DATA['venue/2/artifact/base/1B']
        identifier = URIRef(str(base) + '/identifier/source-base-code')
        for triple in [(origin, RDF.type, BASE.BaserunningSegmentOriginDesignation),
                       (origin, CCO.ont00001808, self.act), (origin, CCO.ont00001916, base),
                       (origin, BFO.BFO_0000176, self.record), (base, RDF.type, BASE.Base),
                       (identifier, RDF.type, CCO.ont00000649), (identifier, CCO.ont00001916, base),
                       (identifier, CCO.ont00001765, Literal('1B'))]: g.add(triple)
        return g, origin

    def test_designation_requires_its_own_record_and_act(self):
        g, origin = self.origin_graph()
        ok, report = self.conforms(g)
        self.assertTrue(ok, report)
        self.assertEqual(list(g.subjects(RDF.type, BASE.BaserunnerAtBaseStasis)), [])
        g.set((origin, CCO.ont00001808, DATA.otherAct))
        self.assertFalse(self.conforms(g)[0])
        g, origin = self.origin_graph()
        g.set((origin, BFO.BFO_0000176, DATA.otherRecord))
        self.assertFalse(self.conforms(g)[0])

    def test_causal_force_requires_correct_rule_and_next_destination(self):
        g, origin = self.origin_graph()
        source = URIRef(str(self.pa) + '/result')
        rule = award(g, source, self.act, self.pa)
        rule_id = URIRef(str(rule) + '/identifier')
        for triple in [(source, CCO.ont00001918, self.field), (rule, BFO.BFO_0000176, DATA.edition),
                       (DATA.edition, RDF.type, CCO.ont00000965), (rule_id, RDF.type, CCO.ont00000649),
                       (rule_id, CCO.ont00001916, rule), (rule_id, CCO.ont00001765, Literal('5.06(b)(3)(B)')),
                       (DATA.batterAct, RDF.type, BASE.BatterAct), (DATA.batterAct, BFO.BFO_0000132, self.pa),
                       (DATA.batterAct, BFO.BFO_0000055, DATA.batterRole), (DATA.batterRole, RDF.type, BASE.BatterRole),
                       (DATA.batterRole, BFO.BFO_0000197, DATA.batter),
                       (self.record, CCO.ont00001808, source), (self.record, CCO.ont00001808, rule)]: g.add(triple)
        ok, report = self.conforms(g)
        self.assertTrue(ok, report)
        g.set((rule_id, CCO.ont00001765, Literal('5.05(b)(1)')))
        self.assertFalse(self.conforms(g)[0])
        g.set((rule_id, CCO.ont00001765, Literal('5.06(b)(3)(B)')))
        g.remove((rule, CCO.ont00001974, self.act))
        self.assertFalse(self.conforms(g)[0])

    def test_event_specific_directive_is_withdrawn(self):
        g = self.graph()
        g.add((DATA.directive, RDF.type, BASE.BaseAwardDirectiveICE))
        self.assertFalse(self.conforms(g)[0])

    def test_each_withdrawn_predicate_fails_conformance(self):
        for name in ['hasResolvedRunner', 'hasAdjudicatedBase', 'settlesAwardFrom', 'hasBaserunningOriginBase']:
            g = self.graph()
            g.add((self.rr, BASE[name], self.runner))
            self.assertFalse(self.conforms(g)[0], name)

    def test_stasis_does_not_allow_agency_or_realization(self):
        for predicate in [CCO.ont00001833, BFO.BFO_0000055]:
            g = self.graph()
            stasis, interval, site = DATA.stasis, DATA.interval, DATA.site
            for triple in [(stasis, RDF.type, BASE.BaserunnerAtBaseStasis),
                           (stasis, BFO.BFO_0000057, self.runner), (stasis, BFO.BFO_0000057, self.base),
                           (stasis, BFO.BFO_0000057, site), (site, RDF.type, BASE.BaseSite),
                           (stasis, CCO.ont00001918, site), (self.runner, BFO.BFO_0000171, site),
                           (self.base, BFO.BFO_0000171, site),
                           (stasis, BFO.BFO_0000199, interval), (interval, RDF.type, BFO.BFO_0000038)]: g.add(triple)
            self.assertTrue(self.conforms(g)[0])
            g.add((stasis, predicate, self.runner))
            self.assertFalse(self.conforms(g)[0])


if __name__ == '__main__':
    unittest.main()
