"""An unchanged RML file cannot release a changed source-selection context."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
import hashlib

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_release',ROOT/'scripts/pipeline/check-source-proof-release.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


class ProofContextFreshness(unittest.TestCase):
    def test_current_context_required_alongside_mapping_and_source_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'Baseball';contract=root/'sources/mlb-game/nifi/flow-contract.json'
            contract.parent.mkdir(parents=True)
            context=root/'scripts/pipeline/prepare-rml-context.py'
            context.parent.mkdir(parents=True);context.write_text('current context')
            mapping=root/'mapping.ttl';mapping.write_text('mapping')
            shape=root/'shape.ttl';shape.write_text('shape')
            run=root/'evidence/run';run.mkdir(parents=True)
            manifest=root/'manifest.json'
            value=dict(mappingPath=str(mapping),mappingSha256=C.sha256(mapping),
                shaclShapePath=str(shape),shaclShapeSha256=C.sha256(shape),
                contextBuilderPath=str(context),contextBuilderSha256=C.sha256(context))
            def save():manifest.write_text(json.dumps(value))
            save()
            required=('rml','shacl','promote','materialize','cleanup')
            for action in required:
                (run/(action+'.json')).write_text(json.dumps(dict(action=action,pipelineRunId='run',gamePk='1',
                    rmlManifest=str(manifest),conforms=True,authoritativeRdfRemainsInGraphStore=True)))
            def check():return C.evidence_matches(run,'mlb-game','1',required,{},contract)
            self.assertTrue(check()[0])
            context.write_text('changed source selection')
            self.assertFalse(check()[0]);self.assertIn('artifact changed',check()[1])
            value['contextBuilderSha256']=C.sha256(context);save()
            self.assertTrue(check()[0])
            alternate=root/'alternate.py';alternate.write_text(context.read_text())
            value['contextBuilderPath']=str(alternate);save()
            self.assertFalse(check()[0]);self.assertIn('owning context-builder',check()[1])
            value.pop('contextBuilderPath');save()
            self.assertFalse(check()[0])


if __name__=='__main__':unittest.main()
