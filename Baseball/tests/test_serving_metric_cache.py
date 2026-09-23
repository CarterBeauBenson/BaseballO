"""Focused reuse/invalidation checks; no live source or corpus processing."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metric_cache', ROOT/'scripts/pipeline/serving_metric_cache.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class MetricCache(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)/'cache.sqlite'
        self.cache = M.MetricProductCache(self.path, 'code-a')
        self.inputs = dict(graph='urn:game:1', rows=[{'entity':'urn:pa:1'}],
            admissions={name: {'status':'admitted', 'hash':'a'} for name in
                ('batting', 'scoring', 'resolution', 'count', 'boundary', 'defense')})
        self.compute = Mock(return_value={'score':{'numerator':'9007199254740993', 'denominator':'7'}})

    def calculate(self, **changes):
        return self.cache.calculate(**(self.inputs | changes), compute=self.compute)

    def test_restart_reuses_exact_product_without_mutable_aliases(self):
        first = self.calculate()
        first['score']['numerator'] = 'mutated'
        self.cache = M.MetricProductCache(self.path, 'code-a')
        warm = self.calculate()
        self.assertEqual(warm['score']['numerator'], '9007199254740993')
        warm.clear()
        self.assertIn('score', self.calculate())
        self.assertEqual(self.compute.call_count, 1)
        self.assertEqual(self.cache.stats['hits'], 2)

    def test_every_current_admission_input_invalidates_even_when_withheld(self):
        for name in self.inputs['admissions']:
            with self.subTest(proof=name):
                self.calculate()
                before = self.compute.call_count
                admissions = self.inputs['admissions'] | {name:{'status':'withheld', 'reason':'current-proof-changed'}}
                self.calculate(admissions=admissions)
                self.assertEqual(self.compute.call_count, before + 1)

    def test_evidence_graph_and_calculation_code_invalidate_independently(self):
        self.calculate()
        self.calculate(rows=[{'entity':'urn:pa:2'}])
        self.calculate(graph='urn:game:2')
        self.cache = M.MetricProductCache(self.path, 'code-b')
        self.calculate(graph='urn:game:2')
        self.assertEqual(self.compute.call_count, 4)

    def test_parallel_versions_coexist_and_history_is_bounded(self):
        self.calculate()
        self.calculate(graph='urn:game:2')
        self.calculate(graph='urn:game:2', rows=[])
        self.calculate()
        self.assertEqual(self.compute.call_count, 3)
        self.calculate(graph='urn:game:2')
        self.assertEqual(self.compute.call_count, 3)
        for version in range(5):
            self.calculate(graph='urn:game:2', rows=[{'version':version}])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT graph,count(*) FROM game_product_version GROUP BY graph').fetchall(),
                             [('urn:game:1', 1), ('urn:game:2', 3)])

    def test_corruption_recomputes_and_repairs(self):
        self.calculate()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE game_product_version SET payload=x'00'")
        self.calculate()
        self.calculate()
        self.assertEqual(self.compute.call_count, 2)
        self.assertEqual(self.cache.stats['discarded'], 1)
        self.assertEqual(self.cache.stats['hits'], 1)

    def test_cache_io_failure_does_not_prevent_calculation(self):
        blocked = Path(self.temporary.name)/'ordinary-file'
        blocked.write_text('not a directory')
        self.cache = M.MetricProductCache(blocked/'cache.sqlite', 'code-a')
        self.assertEqual(self.calculate(), self.compute.return_value)
        self.assertEqual(self.cache.stats['bypassed'], 1)

    def test_failed_calculation_is_never_cached(self):
        self.compute.side_effect = ValueError('invalid evidence')
        with self.assertRaisesRegex(ValueError, 'invalid evidence'):
            self.calculate()
        self.compute.side_effect = None
        self.calculate()
        self.assertEqual(self.compute.call_count, 2)
        self.assertEqual(self.cache.stats['hits'], 0)


if __name__ == '__main__':
    unittest.main()
