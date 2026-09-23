import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from test_metric_blocks import M, sample, season_database, SEASON_SCOPE, scores

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('references',ROOT/'serving/reference_products.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


class References(unittest.TestCase):
    def test_every_historical_cutoff_matches_exact_existing_math_without_request_ranking(self):
        with season_database([sample(101,0),sample(102,2),sample(103,4)]) as db:
            scopes=[dict(SEASON_SCOPE,endDate=day) for day in ('2026-08-02','2026-08-03','2026-08-04')]
            expected=[scores(M.query_sql(db,{'metricId':'recovery-quality'},scope,_use_blocks=False)) for scope in scopes]
            R.prepare(M,db)
            with R.prepared_ranks(M,db),patch.object(M,'percentiles',side_effect=AssertionError('HTTP rank calculation')):
                for scope,wanted in zip(scopes,expected):
                    self.assertEqual(scores(M.query_sql(db,{'metricId':'recovery-quality'},scope)),wanted)
            db.execute("UPDATE dashboard_reference SET payload_sha256='bad'")
            with R.prepared_ranks(M,db),self.assertRaisesRegex(M.EvidenceError,'checksum'):
                M.query_sql(db,{'metricId':'recovery-quality'},scopes[0])

    def test_missing_preparation_does_not_run_expensive_math_on_request(self):
        with season_database([sample(101,0),sample(102,2)]) as db:
            R.initialize(db)
            with R.prepared_ranks(M,db),patch.object(M,'percentiles',side_effect=AssertionError('request calculation')):
                with self.assertRaisesRegex(M.EvidenceError,'NiFi preparation'):
                    M.query_sql(db,{'metricId':'recovery-quality'},dict(SEASON_SCOPE,endDate='2026-08-02'))


if __name__=='__main__':unittest.main()
