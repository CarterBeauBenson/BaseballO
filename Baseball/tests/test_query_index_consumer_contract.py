from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph


ROOT = Path(__file__).resolve().parents[1]
SHAPES = Graph().parse(ROOT / "shacl" / "query-index.ttl", format="turtle")

GRAPH_HEADER = """
@prefix base: <https://baseballontology.org/> .
@prefix idx: <https://w3id.org/baseball/query-index/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://w3id.org/baseball/query-index-build/game/1>
    a idx:QueryIndex ;
    idx:contractVersion "1" ;
    idx:sourceGraph <https://w3id.org/baseball/graph/game/1> ;
    idx:indexedGame <https://baseballontology.org/data/game/1> .

<https://baseballontology.org/data/game/1>
    a idx:GameFact ;
    idx:season 2026 ;
    idx:seasonPhase base:BaseballRegularSeasonPhase ;
    idx:venue <https://baseballontology.org/data/venue/1> ;
    idx:gameStart "2026-08-15T23:05:00Z"^^xsd:dateTime ;
    idx:derivedFrom <https://baseballontology.org/data/game/1> .
"""


def assignment(identifier: str, assignment_type: str, team: str) -> str:
    return f"""
<https://baseballontology.org/data/game/1/assignment/{identifier}>
    a idx:AssignmentFact ;
    idx:game <https://baseballontology.org/data/game/1> ;
    idx:assignmentType idx:{assignment_type} ;
    idx:assignee <{team}> ;
    idx:derivedFrom <https://baseballontology.org/data/game/1/team-role/{identifier}> .
"""


HOME = assignment(
    "home", "HomeTeam", "https://baseballontology.org/data/team/147"
)
AWAY = assignment(
    "away", "AwayTeam", "https://baseballontology.org/data/team/110"
)


def validate_index(*parts: str) -> tuple[bool, str]:
    graph = Graph().parse(data=GRAPH_HEADER + "".join(parts), format="turtle")
    conforms, _, report_text = validate(
        data_graph=graph,
        shacl_graph=SHAPES,
        inference="none",
        advanced=True,
        allow_infos=True,
        allow_warnings=True,
        abort_on_first=False,
    )
    return bool(conforms), str(report_text)


class QueryIndexConsumerContractTests(unittest.TestCase):
    def test_compiler_preserves_typed_literal_lexical_evidence(self) -> None:
        source = GRAPH_HEADER.replace(
            '"2026-08-15T23:05:00Z"^^xsd:dateTime',
            '"2026-08-15T23:05:00.000Z"^^xsd:dateTime',
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "components"
            inputs.mkdir()
            (inputs / "10-game-dimensions.ttl").write_text(
                source, encoding="utf-8", newline="\n"
            )
            output = root / "index.nt"
            stats = root / "stats.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "pipeline" / "compile-query-index.py"),
                    "--inputs",
                    str(inputs),
                    "--output",
                    str(output),
                    "--stats",
                    str(stats),
                    "--game-pk",
                    "1",
                    "--source-graph",
                    "https://w3id.org/baseball/graph/game/1",
                    "--index-resource",
                    "https://w3id.org/baseball/query-index-build/game/1",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            compiled = output.read_text(encoding="utf-8")
            self.assertIn('"2026-08-15T23:05:00.000Z"', compiled)
            self.assertNotIn('"2026-08-15T23:05:00+00:00"', compiled)

    def test_one_distinct_canonical_home_and_away_team_conforms(self) -> None:
        conforms, report = validate_index(HOME, AWAY)
        self.assertTrue(conforms, report)

    def test_missing_and_duplicate_assignments_fail(self) -> None:
        cases = {
            "missing-home": (
                (AWAY,),
                "exactly one HomeTeam AssignmentFact",
            ),
            "duplicate-away": (
                (
                    HOME,
                    AWAY,
                    assignment(
                        "away-duplicate",
                        "AwayTeam",
                        "https://baseballontology.org/data/team/111",
                    ),
                ),
                "exactly one AwayTeam AssignmentFact",
            ),
        }
        for name, (parts, expected_message) in cases.items():
            with self.subTest(name=name):
                conforms, report = validate_index(*parts)
                self.assertFalse(conforms)
                self.assertIn(expected_message, report)

    def test_same_or_noncanonical_team_assignees_fail(self) -> None:
        cases = {
            "same-team": (
                (
                    HOME,
                    assignment(
                        "away",
                        "AwayTeam",
                        "https://baseballontology.org/data/team/147",
                    ),
                ),
                "must identify distinct Teams",
            ),
            "noncanonical-team-iri": (
                (
                    HOME,
                    assignment(
                        "away",
                        "AwayTeam",
                        "https://example.org/provider/team/110",
                    ),
                ),
                "canonical BaseballO Team IRIs",
            ),
        }
        for name, (parts, expected_message) in cases.items():
            with self.subTest(name=name):
                conforms, report = validate_index(*parts)
                self.assertFalse(conforms)
                self.assertIn(expected_message, report)


if __name__ == "__main__":
    unittest.main()
