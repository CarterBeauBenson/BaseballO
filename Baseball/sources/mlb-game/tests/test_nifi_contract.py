from __future__ import annotations

import json
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]


class NifiContractTests(unittest.TestCase):
    def test_work_stages_have_two_total_attempts(self) -> None:
        contract = json.loads(
            (MODULE_ROOT / "nifi" / "flow-contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual(contract["failurePolicy"]["maximumAttemptsPerStage"], 2)
        self.assertNotIn("maximumRetriesPerStage", contract["failurePolicy"])

    def test_provisioner_converts_attempts_to_nifi_retries(self) -> None:
        provisioner = (MODULE_ROOT / "nifi" / "provision.ps1").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "$maximumRetriesPerStage = $maximumAttemptsPerStage - 1", provisioner
        )
        self.assertIn("-MaximumRetries $maximumRetriesPerStage", provisioner)

    def test_proof_readiness_polling_remains_separate(self) -> None:
        contract = json.loads(
            (MODULE_ROOT / "nifi" / "flow-contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual(contract["proofRelease"]["readinessRetryCount"], 60)
        self.assertEqual(contract["proofRelease"]["readinessRetryDelay"], "30 sec")


if __name__ == "__main__":
    unittest.main()
