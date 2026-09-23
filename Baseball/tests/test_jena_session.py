import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from rdflib.compare import isomorphic

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/pipeline'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
S=load('jena_session','jena_session.py')
V=load('existing_shacl','validate-shacl.py')
JAVA=Path(os.environ.get('BASEBALLO_TEST_JAVA','missing-java'))
JENA=Path(os.environ.get('BASEBALLO_TEST_JENA','missing-jar'))


@unittest.skipUnless(JAVA.is_file() and JENA.is_file(),'explicit local Jena runtime required')
class JenaSession(unittest.TestCase):
    def test_profiles_keep_distinct_reports_and_match_existing_jena_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); data=root/'game.ttl'; shape=root/'shape.ttl'
            data.write_text('@prefix ex: <https://example.org/> . ex:a ex:value 1 .')
            with S.Session(data,JAVA,JENA) as session:
                for minimum in (1,2):
                    shape.write_text('@prefix sh: <http://www.w3.org/ns/shacl#> . '
                        '@prefix ex: <https://example.org/> . ex:shape a sh:NodeShape; sh:targetNode ex:a; '
                        'sh:property [ sh:path ex:value; sh:minCount '+str(minimum)+' ] .')
                    args=dict(data_path=data.resolve(),shape_path=shape.resolve(),java=JAVA,classpath=JENA,max_heap='384m')
                    actual=session.validate_with_jena(**args); expected=V.validate_with_jena(**args)
                    self.assertEqual(actual[0],minimum==1); self.assertEqual(actual[0],expected[0])
                    self.assertTrue(isomorphic(actual[1],expected[1]))
                self.assertEqual(session.data_count,1);self.assertEqual(len(session.timings),2)


if __name__=='__main__':unittest.main()
