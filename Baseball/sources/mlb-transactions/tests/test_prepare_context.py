from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph


MODULE = Path(__file__).resolve().parents[1]
PREPARE = MODULE / "mapping" / "prepare-context.py"
MAPPING = MODULE / "mapping" / "mlb-transactions.rml.ttl"
FIXTURE = MODULE / "fixtures" / "one-record-transactions.json"
TYPE_FIXTURE = MODULE / "fixtures" / "transaction-types.json"


class TransactionsContextTests(unittest.TestCase):
    def run_builder(
        self,
        transactions: dict,
        transaction_types: list[dict[str, str]],
        *,
        death_pin: dict | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        transactions_path = root / "transactions.json"
        types_path = root / "transaction-types.json"
        output_path = root / "transactions-context.json"
        transactions_path.write_text(
            json.dumps(transactions, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        types_path.write_text(
            json.dumps(transaction_types, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        command = [
            sys.executable,
            str(PREPARE),
            str(transactions_path),
            str(types_path),
            str(output_path),
        ]
        if death_pin is not None:
            pin_path = root / "death-code-pin.json"
            pin_path.write_text(
                json.dumps(death_pin, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            command.extend(["--death-code-pin", str(pin_path)])
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        context = None
        if output_path.is_file():
            context = json.loads(output_path.read_text(encoding="utf-8"))
        return completed, context

    def fixture_documents(self) -> tuple[dict, list[dict[str, str]]]:
        return (
            json.loads(FIXTURE.read_text(encoding="utf-8")),
            json.loads(TYPE_FIXTURE.read_text(encoding="utf-8")),
        )

    def test_one_record_context_preserves_accepted_grains(self) -> None:
        transactions, transaction_types = self.fixture_documents()
        before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        completed, context = self.run_builder(transactions, transaction_types)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), before)
        self.assertEqual(context["source"]["sourceRowCount"], 1)
        self.assertEqual(context["source"]["uniqueRowCount"], 1)
        self.assertFalse(context["source"]["deathMappingEnabled"])
        self.assertEqual(len(context["groups"]), 1)
        self.assertEqual(len(context["rows"]), 1)
        self.assertEqual(len(context["aboutness"]), 3)
        self.assertEqual(len(context["descriptions"]), 1)
        self.assertEqual(len(context["dates"]), 3)
        self.assertEqual(context["deaths"], [])
        self.assertEqual(len(context["trades"]), 1)
        self.assertEqual(len(context["tradeAgents"]), 2)
        self.assertEqual(len(context["tradeLegs"]), 1)
        self.assertEqual(context["signings"], [])
        self.assertEqual(
            {item["fieldKeyText"] for item in context["dates"]},
            {"date", "effectiveDate", "resolutionDate"},
        )
        self.assertEqual(
            {item["dateValue"] for item in context["dates"]},
            {"2026-07-31", "2026-08-01", "2026-08-02"},
        )
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertNotIn("fullName", serialized)
        self.assertNotIn("Fixture From Team", serialized)
        self.assertIn("Synthetic fixture — structured trade", serialized)
        self.assertEqual(
            transactions["transactions"][0]["person"]["fullName"],
            "Eugenio Suárez",
        )

        selected = {
            "id": 9000001,
            "personId": 553993,
            "fromTeamId": 109,
            "toTeamId": 135,
            "date": "2026-07-31",
            "effectiveDate": "2026-08-01",
            "resolutionDate": "2026-08-02",
            "typeCode": "TR",
            "typeDesc": "Trade",
            "description": "Synthetic fixture — structured trade evidence.",
        }
        canonical = json.dumps(
            selected,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(context["rows"][0]["rowSha256"], digest)
        self.assertEqual(
            context["rows"][0]["rowIri"],
            f"https://baseballontology.org/data/source/mlb-transactions/row/{digest}",
        )

    def test_pre_mapping_gate_rejects_source_and_code_list_errors(self) -> None:
        base, transaction_types = self.fixture_documents()
        mutations = []

        unknown = copy.deepcopy(base)
        unknown["transactions"][0]["typeCode"] = "UNKNOWN"
        mutations.append(("unknown typeCode", unknown, transaction_types))

        mismatch = copy.deepcopy(base)
        mismatch["transactions"][0]["typeDesc"] = "Wrong Description"
        mutations.append(("code description mismatch", mismatch, transaction_types))

        malformed_date = copy.deepcopy(base)
        malformed_date["transactions"][0]["effectiveDate"] = "2026-02-30"
        mutations.append(("malformed date", malformed_date, transaction_types))

        malformed_id = copy.deepcopy(base)
        malformed_id["transactions"][0]["id"] = "9000001"
        mutations.append(("malformed identifier", malformed_id, transaction_types))

        malformed_optional_id = copy.deepcopy(base)
        malformed_optional_id["transactions"][0]["toTeam"]["id"] = "135"
        mutations.append(
            ("malformed present optional identifier", malformed_optional_id, transaction_types)
        )

        corrupted_unicode = copy.deepcopy(base)
        corrupted_unicode["transactions"][0]["person"]["fullName"] = "Eugenio Su\ufffdrez"
        mutations.append(("corrupt Unicode", corrupted_unicode, transaction_types))

        for label, transactions, codes in mutations:
            with self.subTest(label=label):
                completed, context = self.run_builder(transactions, codes)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIsNone(context)
                self.assertIn("input validation failed", completed.stdout)

    def test_absent_optional_fields_emit_nothing(self) -> None:
        transactions, transaction_types = self.fixture_documents()
        row = transactions["transactions"][0]
        for key in ("person", "fromTeam", "toTeam", "resolutionDate", "description"):
            row.pop(key)
        completed, context = self.run_builder(transactions, transaction_types)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert context is not None
        self.assertEqual(context["aboutness"], [])
        self.assertEqual(context["descriptions"], [])
        self.assertEqual(context["deaths"], [])
        self.assertEqual(len(context["dates"]), 2)
        self.assertEqual(
            {item["fieldKeyText"] for item in context["dates"]},
            {"date", "effectiveDate"},
        )

    def test_exact_duplicate_rows_reuse_one_content_identity(self) -> None:
        transactions, transaction_types = self.fixture_documents()
        transactions["transactions"].append(
            copy.deepcopy(transactions["transactions"][0])
        )
        completed, context = self.run_builder(transactions, transaction_types)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert context is not None
        self.assertEqual(context["source"]["sourceRowCount"], 2)
        self.assertEqual(context["source"]["uniqueRowCount"], 1)
        self.assertEqual(len(context["groups"]), 1)
        self.assertEqual(len(context["rows"]), 1)

    def test_repeated_id_and_person_do_not_collapse_changed_content(self) -> None:
        transactions, transaction_types = self.fixture_documents()
        second = copy.deepcopy(transactions["transactions"][0])
        second["description"] = "A distinct semantic row version."
        transactions["transactions"].append(second)
        completed, context = self.run_builder(transactions, transaction_types)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert context is not None
        self.assertEqual(len(context["groups"]), 1)
        self.assertEqual(len(context["rows"]), 2)
        self.assertEqual(len({row["rowSha256"] for row in context["rows"]}), 2)

    def test_death_is_disabled_without_an_accepted_pin(self) -> None:
        transactions, _ = self.fixture_documents()
        transactions["transactions"][0]["typeCode"] = "TEST-DEATH"
        transactions["transactions"][0]["typeDesc"] = "Death"
        codes = [{"code": "TEST-DEATH", "description": "Death"}]
        completed, context = self.run_builder(transactions, codes)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert context is not None
        self.assertFalse(context["source"]["deathMappingEnabled"])
        self.assertEqual(context["deaths"], [])

        unreviewed_pin = {
            "artifactType": "baseballo-mlb-transactions-death-code-pin",
            "contractVersion": 1,
            "codeListSha256": "0" * 64,
            "deathCode": "TEST-DEATH",
            "deathDescription": "Death",
            "decisionArtifact": "Baseball/archive/design-records/example/review.json",
            "decisionSha256": "0" * 64,
        }
        rejected, rejected_context = self.run_builder(
            transactions, codes, death_pin=unreviewed_pin
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIsNone(rejected_context)

    def test_trade_requires_exact_code_and_structured_parties(self) -> None:
        transactions, _ = self.fixture_documents()
        row = transactions["transactions"][0]
        row["typeCode"] = "TR"
        row["typeDesc"] = "Trade"
        completed, context = self.run_builder(
            transactions, [{"code": "TR", "description": "Trade"}]
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert context is not None
        self.assertEqual(len(context["trades"]), 1)
        self.assertEqual(len(context["tradeAgents"]), 2)
        self.assertEqual(len(context["tradeLegs"]), 1)
        leg = context["tradeLegs"][0]
        self.assertIn("/loss-of-player-role", leg["lossIri"])
        self.assertIn("/gain-of-player-role", leg["gainIri"])

        del row["fromTeam"]
        completed, incomplete = self.run_builder(
            transactions, [{"code": "TR", "description": "Trade"}]
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert incomplete is not None
        self.assertEqual(incomplete["trades"], [])
        self.assertEqual(incomplete["tradeLegs"], [])

    def test_signing_maps_contract_and_player_role_gain_without_free_agent_inference(self) -> None:
        transactions, _ = self.fixture_documents()
        row = transactions["transactions"][0]
        row["typeCode"] = "SGN"
        row["typeDesc"] = "Signed"
        completed, context = self.run_builder(
            transactions, [{"code": "SGN", "description": "Signed"}]
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        assert context is not None
        self.assertEqual(len(context["signings"]), 1)
        self.assertNotIn("free-agent", json.dumps(context))

    def test_rml_contains_only_approved_world_mappings(self) -> None:
        mapping = MAPPING.read_text(encoding="utf-8")
        self.assertIn("BaseballPersonnelTradeAct", mapping)
        self.assertNotIn("UniformNumberAssignmentAct", mapping)
        self.assertIn("base:PlayerRole", mapping)
        self.assertNotIn("MajorLeagueFreeAgentRole", mapping)
        self.assertNotIn("BaseballPlayerReleaseAct", mapping)
        self.assertNotIn("RetirementDeclarationAct", mapping)
        self.assertIn("cco:ont00000920", mapping)
        self.assertGreater(len(Graph().parse(MAPPING, format="turtle")), 0)

    def test_all_module_json_files_parse(self) -> None:
        for path in MODULE.rglob("*.json"):
            with self.subTest(path=path.relative_to(MODULE)):
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
