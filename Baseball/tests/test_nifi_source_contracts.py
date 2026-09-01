from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "sources" / "source-modules.json"
REFERENCE_MODULES = (
    "mlb-teams",
    "mlb-leagues",
    "mlb-divisions",
    "mlb-people",
    "mlb-venues",
    "mlb-transactions",
)


class NifiSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.modules = {item["id"]: item for item in cls.catalog["modules"]}

    def contract(self, module_id: str) -> tuple[dict, Path]:
        module = self.modules[module_id]
        contract_path = ROOT / module["nifiContract"]
        return json.loads(contract_path.read_text(encoding="utf-8")), contract_path

    def test_each_reference_module_owns_one_distinct_process_group(self) -> None:
        groups: list[str] = []
        for module_id in REFERENCE_MODULES:
            contract, _ = self.contract(module_id)
            self.assertEqual(contract["sourceModule"], module_id)
            self.assertEqual(
                self.modules[module_id]["nifiProcessGroups"],
                [contract["sourceProcessGroup"]],
            )
            groups.append(contract["sourceProcessGroup"])
        self.assertEqual(len(groups), len(set(groups)))

    def test_contract_artifacts_do_not_cross_source_boundaries(self) -> None:
        for module_id in REFERENCE_MODULES:
            contract, contract_path = self.contract(module_id)
            module_root = (ROOT / "sources" / module_id).resolve()
            self.assertTrue(contract_path.resolve().is_relative_to(module_root))
            for relative in (
                contract["context"]["builder"],
                contract["mapping"],
                contract["shacl"],
            ):
                artifact = (module_root / relative).resolve()
                self.assertTrue(artifact.is_relative_to(module_root))
                self.assertTrue(artifact.is_file(), artifact)
            provisioner = (ROOT / self.modules[module_id]["nifiProvisioner"]).resolve()
            self.assertTrue(provisioner.is_relative_to(module_root))
            self.assertTrue(provisioner.is_file())

    def test_connectors_are_endpoint_specific(self) -> None:
        required_fragments = {
            "mlb-teams": "/api/v1/teams?",
            "mlb-leagues": "/api/v1/leagues?",
            "mlb-divisions": "/api/v1/divisions?",
            "mlb-people": "/api/v1/people/",
            "mlb-venues": "/api/v1/venues?",
        }
        processor_names: list[str] = []
        for module_id, fragment in required_fragments.items():
            contract, _ = self.contract(module_id)
            acquisitions = contract["acquisitions"]
            self.assertEqual(len(acquisitions), 1)
            self.assertIn(fragment, acquisitions[0]["url"])
            processor_names.append(acquisitions[0]["processorName"])
        self.assertEqual(len(processor_names), len(set(processor_names)))

        people, _ = self.contract("mlb-people")
        self.assertIn("/api/v1/sports/1/players?", people["populationDiscovery"]["url"])
        self.assertNotEqual(
            people["populationDiscovery"]["processorName"],
            people["acquisitions"][0]["processorName"],
        )

        transactions, _ = self.contract("mlb-transactions")
        self.assertEqual(
            [item["key"] for item in transactions["acquisitions"]],
            ["transaction-types", "transactions"],
        )
        self.assertIn("/api/v1/transactionTypes", transactions["acquisitions"][0]["url"])
        self.assertIn("/api/v1/transactions?", transactions["acquisitions"][1]["url"])

        venues, _ = self.contract("mlb-venues")
        self.assertIn("/api/v1/venues?", venues["populationDiscovery"]["url"])
        self.assertNotEqual(
            venues["populationDiscovery"]["processorName"],
            venues["acquisitions"][0]["processorName"],
        )

    def test_reference_sources_own_backfill_and_daily_fanout(self) -> None:
        for module_id in REFERENCE_MODULES:
            contract, _ = self.contract(module_id)
            daily = contract["dailySchedule"]
            self.assertEqual(daily["cron"], "0 0 5 * * ?")
            self.assertEqual(daily["timeZone"], "America/New_York")
            if "populationDiscovery" in contract:
                discovery = contract["populationDiscovery"]
                self.assertIn("backfillRequest", discovery)
                self.assertTrue(discovery["recordsJsonPath"])
                self.assertTrue(discovery["idJsonPath"])
                self.assertTrue(discovery["idAttribute"])
                self.assertEqual(
                    discovery["detailConnector"],
                    contract["acquisitions"][0]["processorName"],
                )
            else:
                self.assertIn("backfillRequest", contract)

    def test_game_schedule_fanout_defers_one_sql_build_per_batch(self) -> None:
        contract, _ = self.contract("mlb-game")
        schedule = contract["scheduleDiscovery"]
        self.assertEqual(schedule["dailyCron"], "0 0 5 * * ?")
        self.assertEqual(schedule["timeZone"], "America/New_York")
        self.assertIn("/api/v1/schedule?", schedule["url"])
        self.assertIn("backfillRequest", schedule)
        parser = ROOT / "sources" / "mlb-game" / schedule["parser"]
        materializer = (
            ROOT
            / "sources"
            / "mlb-game"
            / contract["batchMaterialization"]["processor"]
        )
        self.assertTrue(parser.is_file())
        self.assertTrue(materializer.is_file())

        provisioner = (
            ROOT / "sources" / "mlb-game" / "nifi" / "provision.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn('"materializeMode`":`"immediate`"', provisioner)
        self.assertIn('"materializeMode": "deferred"', parser.read_text(encoding="utf-8"))
        self.assertIn("Check Pending Batch Materialization", provisioner)

    def test_bulk_and_daily_requests_are_proof_gated(self) -> None:
        checker = ROOT / "scripts" / "pipeline" / "check-source-proof-release.py"
        self.assertTrue(checker.is_file())
        common = (ROOT / "scripts" / "infra" / "provision-nifi-source.ps1").read_text(
            encoding="utf-8"
        )
        game = (ROOT / "sources" / "mlb-game" / "nifi" / "provision.ps1").read_text(
            encoding="utf-8"
        )
        for text in (common, game):
            self.assertIn("check-source-proof-release.py", text)
            self.assertIn("Check Proof Release", text)
            self.assertIn("'Proof Release'", text)

        starter = (ROOT / "scripts" / "infra" / "start-nifi.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("-Duser.timezone=America/New_York", starter)

    def test_corpus_submission_only_triggers_existing_nifi_lanes(self) -> None:
        submitter = (
            ROOT / "scripts" / "infra" / "submit-nifi-corpus.ps1"
        ).read_text(encoding="utf-8")
        for module_id in ("mlb-game", *REFERENCE_MODULES):
            self.assertIn(f"'{module_id}'", submitter)
        self.assertIn("state = 'RUN_ONCE'", submitter)
        self.assertIn("does not poll", submitter)
        self.assertNotIn("Start-Sleep", submitter)
        self.assertNotIn("RunBackfill", submitter)

    def test_graph_templates_match_registered_source_namespaces(self) -> None:
        for module_id in REFERENCE_MODULES:
            contract, _ = self.contract(module_id)
            graph = contract["authoritativeGraphTemplate"].replace(
                "{scope.key}", "proof"
            )
            self.assertTrue(
                any(
                    graph.startswith(prefix)
                    for prefix in self.modules[module_id]["authoritativeGraphPrefixes"]
                ),
                (module_id, graph),
            )

    def test_command_stages_require_explicit_zero_exit_gates(self) -> None:
        common = (ROOT / "scripts" / "infra" / "provision-nifi-source.ps1").read_text(
            encoding="utf-8"
        )
        game = (ROOT / "sources" / "mlb-game" / "nifi" / "provision.ps1").read_text(
            encoding="utf-8"
        )
        for text in (common, game):
            self.assertIn("AutoTerminate @('output stream', 'nonzero status')", text)
            self.assertIn("execution.status:equals('0')", text)
            self.assertIn("Ensure-ExitGate", text)
            self.assertIn("Ensure-ExitGate $groupId 'Cleanup'", text)
            self.assertNotRegex(
                text,
                re.compile(
                    r"-SourceId \$processors\.(?:context|rml|shacl|promote|materialize|cleanup) "
                    r"-DestinationId \$processors\.(?:rml|shacl|promote|materialize|cleanup|success) "
                    r"-Relationships @\('original'\)"
                ),
            )

    def test_source_promotion_http_is_safe_in_noninteractive_powershell(self) -> None:
        stage = (ROOT / "scripts" / "pipeline" / "process-source-stage.ps1").read_text(
            encoding="utf-8"
        )
        requests = re.findall(r"Invoke-WebRequest[^\r\n]*", stage)
        self.assertEqual(len(requests), 4)
        for request in requests:
            self.assertIn("-UseBasicParsing", request)


if __name__ == "__main__":
    unittest.main()
