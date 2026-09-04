from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTEXT_BUILDER = ROOT / "scripts" / "pipeline" / "prepare-rml-context.py"
SPEC = importlib.util.spec_from_file_location("baseballo_prepare_rml_context", CONTEXT_BUILDER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class EdgeCaseContextTests(unittest.TestCase):
    def test_statusless_pitch_result_review_keeps_only_supported_claims(self) -> None:
        play = {
            "result": {
                "description": "Tyler Heineman challenged (pitch result): Brooks Lee walks."
            }
        }
        pitch_events = [{"details": {"call": {"code": "B"}}}]

        context = MODULE.reviewed_play_context(
            play, pitch_events, {"tyler heineman": "592663"}, "65"
        )

        self.assertTrue(context["hasReview"])
        self.assertEqual(context["reviewType"], "pitch_result")
        self.assertEqual(context["reviewInitiation"], "challenge")
        self.assertEqual(context["reviewChallengerId"], "592663")
        self.assertEqual(context["reviewFinalDecision"], "ball")
        self.assertFalse(context["hasReviewStatus"])
        self.assertNotIn("reviewStatus", context)
        self.assertNotIn("reviewOutcome", context)
        self.assertNotIn("reviewOriginalDecision", context)

    def test_structured_overturn_records_outcome_without_inventing_original_decision(self) -> None:
        play = {
            "result": {
                "description": "Endy Rodríguez challenged (pitch result): Endy Rodríguez walks."
            }
        }
        pitch_events = [
            {
                "details": {"call": {"code": "B"}},
                "reviewDetails": {"isOverturned": True},
            }
        ]

        context = MODULE.reviewed_play_context(
            play, pitch_events, {"endy rodríguez": "665833"}, "59"
        )

        self.assertTrue(context["hasReviewStatus"])
        self.assertEqual(context["reviewStatus"], "overturned")
        self.assertEqual(context["reviewOutcome"], "overturning")
        self.assertEqual(context["reviewFinalDecision"], "ball")
        self.assertTrue(context["hasUnresolvedOriginalDecision"])
        self.assertNotIn("reviewOriginalDecision", context)

    def test_play_level_review_is_not_conflated_with_an_earlier_pitch_review(self) -> None:
        play = {
            "result": {
                "description": (
                    "Willy Adames challenged (pitch result), call on the field "
                    "was confirmed: Willy Adames called out on strikes."
                )
            },
            "reviewDetails": {"isOverturned": False},
        }
        pitch_events = [
            {
                "details": {"call": {"code": "C"}},
                "reviewDetails": {"isOverturned": True},
            },
            {"details": {"call": {"code": "C"}}},
        ]

        context = MODULE.reviewed_play_context(
            play, pitch_events, {"willy adames": "642715"}, "12"
        )

        self.assertEqual(context["reviewStatus"], "confirmed")
        self.assertEqual(context["reviewOutcome"], "affirming")
        self.assertEqual(context["reviewFinalDecision"], "strike")

    def test_upheld_review_is_canonicalized_as_an_affirming_review(self) -> None:
        play = {
            "result": {
                "description": (
                    "Umpire reviewed (home run), call on the field was upheld: "
                    "Kyle Schwarber doubles on a fly ball."
                )
            },
            "reviewDetails": {"isOverturned": False},
        }

        context = MODULE.reviewed_play_context(play, [], {}, "44")

        self.assertEqual(context["reviewStatus"], "confirmed")
        self.assertEqual(context["reviewOutcome"], "affirming")
        self.assertNotIn("reviewOriginalDecision", context)
        self.assertNotIn("reviewFinalDecision", context)

    def test_advisory_with_pitch_keeps_incomplete_plate_appearance_context(self) -> None:
        common = {
            "about": {"atBatIndex": 44},
            "matchup": {"batter": {"id": 1}, "pitcher": {"id": 2}},
            "result": {"eventType": "game_advisory"},
            "runners": [],
        }
        pure_advisory = {
            **common,
            "playEvents": [{"isPitch": False}],
        }
        interrupted_plate_appearance = {
            **common,
            "playEvents": [{"isPitch": True}],
        }

        self.assertFalse(MODULE.play_has_plate_appearance_structure(pure_advisory))
        self.assertTrue(
            MODULE.play_has_plate_appearance_structure(interrupted_plate_appearance)
        )

    def test_missing_official_name_preserves_identifier_and_omits_label_guard(self) -> None:
        document = {
            "liveData": {
                "boxscore": {
                    "officials": [
                        {"official": {"id": 123456}, "officialType": "Home Plate"}
                    ]
                }
            }
        }

        count = MODULE.annotate_officials(document)

        self.assertEqual(count, 1)
        assignment = document["liveData"]["boxscore"]["officials"][0]
        self.assertEqual(assignment["official"]["id"], 123456)
        self.assertFalse(assignment["_baseballO"]["hasOfficialName"])


if __name__ == "__main__":
    unittest.main()
