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

    def test_acquisition_does_not_require_a_completed_sample_game(self) -> None:
        contract = json.loads(
            (MODULE_ROOT / "nifi" / "flow-contract.json").read_text(encoding="utf-8")
        )

        self.assertFalse(contract['scheduleDiscovery']['requiresCompletedProof'])
        self.assertNotIn('proofRelease', contract)
        provisioner = (MODULE_ROOT / 'nifi/provision.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("-Name '01 schedule batch to acquisition' -SourceId $processors.prepareSchedule -DestinationId $processors.scheduleHttp", provisioner)
        self.assertNotIn('check-source-proof-release.py', provisioner)
        self.assertIn("'09 RML passed to SHACL'", provisioner)
        self.assertIn("'11 SHACL passed to promotion'", provisioner)

    def test_quarantine_replay_proves_five_exact_inputs_before_remainder(self) -> None:
        contract = json.loads(
            (MODULE_ROOT / "nifi" / "flow-contract.json").read_text(encoding="utf-8")
        )
        replay = contract["quarantineReplay"]

        self.assertEqual(len(replay["proofGames"]), 5)
        self.assertEqual(len({item["gamePk"] for item in replay["proofGames"]}), 5)
        self.assertEqual(
            replay["releasePolicy"],
            "all-five-exact-input-hashes-promoted-before-remainder",
        )
        self.assertEqual(replay["readinessRetryCount"], 960)
        self.assertEqual(replay["readinessRetryDelay"], "30 sec")

        provisioner = (MODULE_ROOT / "nifi" / "provision.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("Check Quarantine Replay Proof", provisioner)
        self.assertIn("Emit Quarantine Replay Remainder", provisioner)
        self.assertIn("Resolve Quarantine Replay", provisioner)


if __name__ == "__main__":
    unittest.main()
