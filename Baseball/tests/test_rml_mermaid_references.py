"""An IRI-valued reference must not disappear as a presumed literal."""
import importlib.util
from pathlib import Path
import sys
import unittest

from rdflib import BNode, Graph, Literal

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('rml_diagrams',ROOT/'scripts/generate_rml_mermaid.py')
MODULE=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=MODULE
SPEC.loader.exec_module(MODULE)


class ReferenceTests(unittest.TestCase):
    def test_iri_and_literal_references_are_distinct(self):
        g=Graph(); iri=BNode(); literal=BNode()
        for node in (iri,literal): g.add((node,MODULE.RML.reference,Literal('value')))
        g.add((iri,MODULE.RR.termType,MODULE.RR.IRI))
        self.assertEqual(MODULE.term_key(g,iri),('iri-reference','value'))
        self.assertEqual(MODULE.term_key(g,literal),('reference','value'))
        self.assertNotEqual(MODULE.term_key(g,iri,'source-A'),MODULE.term_key(g,iri,'source-B'))

    def test_review_input_reference_is_an_edge(self):
        _,infos=MODULE.parse_mapping(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        info=infos['M2OperativeReviewMap']
        relation=next(r for r in info.relations if str(r.predicate).endswith('ont00001921'))
        self.assertEqual(relation.object.mode,'IRI reference')
        self.assertEqual(relation.object.key,infos['M2OriginalDecisionMap'].subject_key)


if __name__=='__main__': unittest.main()
