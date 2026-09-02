from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
BUILDER = MODULE_ROOT / "mapping" / "prepare-context.py"
FIXTURE = MODULE_ROOT / "schema" / "one-record.synthetic.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreparePeopleContextTests(unittest.TestCase):
    def run_builder(self, source: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(BUILDER),
                str(source),
                str(output),
                "--resource-kind",
                "player",
                "--expected-person-id",
                "660271",
                "--request-scope",
                "https://statsapi.mlb.com/api/v1/people/660271",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_happy_path_preserves_source_bytes_and_unicode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            output = root / "people-context.json"
            shutil.copyfile(FIXTURE, source)
            before = sha256(source)

            result = self.run_builder(source, output)

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(sha256(source), before)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["fullNames"][0]["text"], "Eugenio Suárez")
            self.assertEqual(context["massMeasurements"][0]["pounds"], "213")
            self.assertEqual(context["battingDispositions"][0]["side"], "right")
            self.assertEqual(context["throwingDispositions"][0]["side"], "right")
            self.assertEqual(context["fielderPositionRecords"][0]["positionCode"], "5")
            self.assertEqual(
                context["currentTeamAboutness"][0]["teamIri"],
                "https://baseballontology.org/data/team/135",
            )
            self.assertEqual(list(root.glob(".*.partial")), [])

    def test_switch_side_expands_to_two_real_dispositions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            output = root / "people-context.json"
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["people"][0]["batSide"]["code"] = "S"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.run_builder(source, output)

            self.assertEqual(result.returncode, 0, result.stdout)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                {row["side"] for row in context["battingDispositions"]},
                {"left", "right"},
            )
            self.assertEqual(
                {row["sourceCode"] for row in context["battingDispositions"]},
                {"S"},
            )

    def test_position_tuple_mismatch_is_rejected_before_rml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            output = root / "people-context.json"
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["people"][0]["primaryPosition"]["abbreviation"] = "SS"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.run_builder(source, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match code", result.stdout)

    def test_two_way_position_produces_persistent_pitcher_and_fielder_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            output = root / "people-context.json"
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["people"][0]["primaryPosition"] = {
                "code": "Y",
                "name": "Two-Way Player",
                "type": "Two-Way Player",
                "abbreviation": "TWP",
            }
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.run_builder(source, output)

            self.assertEqual(result.returncode, 0, result.stdout)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["pitcherPositionRecords"], [])
            self.assertEqual(context["fielderPositionRecords"], [])
            self.assertEqual(len(context["twoWayPositionRecords"]), 1)
            row = context["twoWayPositionRecords"][0]
            self.assertEqual(row["positionCode"], "Y")
            self.assertEqual(
                row["pitcherRoleIri"],
                "https://baseballontology.org/data/player/660271/role/pitcher",
            )
            self.assertEqual(
                row["fielderRoleIri"],
                "https://baseballontology.org/data/player/660271/role/fielder",
            )

    def test_generic_outfield_position_uses_existing_fielder_cluster(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            output = root / "people-context.json"
            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            payload["people"][0]["primaryPosition"] = {
                "code": "O",
                "name": "Outfield",
                "type": "Outfielder",
                "abbreviation": "OF",
            }
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = self.run_builder(source, output)

            self.assertEqual(result.returncode, 0, result.stdout)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(context["fielderPositionRecords"]), 1)
            row = context["fielderPositionRecords"][0]
            self.assertEqual(row["positionCode"], "O")
            self.assertEqual(row["positionConcept"], "fielder")
            self.assertEqual(
                row["roleIri"],
                "https://baseballontology.org/data/player/660271/role/fielder",
            )
            self.assertEqual(
                row["fieldingDispositionIri"],
                "https://baseballontology.org/data/player/660271/disposition/fielding/O",
            )
            self.assertEqual(context["pitcherPositionRecords"], [])
            self.assertEqual(context["catcherPositionRecords"], [])
            self.assertEqual(context["twoWayPositionRecords"], [])

    def test_input_output_alias_is_rejected_without_changing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.json"
            shutil.copyfile(FIXTURE, source)
            before = sha256(source)

            result = self.run_builder(source, source)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Refusing to overwrite", result.stdout)
            self.assertEqual(sha256(source), before)


if __name__ == "__main__":
    unittest.main()
