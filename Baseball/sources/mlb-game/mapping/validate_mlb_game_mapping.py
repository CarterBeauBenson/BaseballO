#!/usr/bin/env python3
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import json
import re

from rdflib import Graph, RDF, RDFS, URIRef
from rdflib.namespace import OWL

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[2]

parser = ArgumentParser(
    description="Statically validate the MLB game feed/live RML mapping."
)
parser.add_argument(
    "source",
    nargs="?",
    type=Path,
    default=HERE / "game.json",
    help="completed raw MLB feed/live JSON (default: ./game.json)",
)
args = parser.parse_args()

mapping = HERE / "mlb-game.rml.ttl"
ontology = REPOSITORY_ROOT / "ontology" / "BaseballO.ttl"
source = args.source.resolve()

errors = []
notes = []

g = Graph()
try:
    g.parse(mapping, format="turtle")
except Exception as e:
    errors.append(f"RML Turtle parse failed: {e}")
else:
    RR = "http://www.w3.org/ns/r2rml#"
    RML = "http://semweb.mmlab.be/ns/rml#"
    triples_map = URIRef(RR + "TriplesMap")
    logical_source_class = URIRef(RML + "LogicalSource")
    logical_source = URIRef(RML + "logicalSource")
    iterator = URIRef(RML + "iterator")
    rml_source = URIRef(RML + "source")
    subject_map = URIRef(RR + "subjectMap")
    parent_triples_map = URIRef(RR + "parentTriplesMap")
    rr_class = URIRef(RR + "class")

    tms = set(g.subjects(RDF.type, triples_map))
    logical_sources = set(g.subjects(RDF.type, logical_source_class))
    notes.append(f"Triples maps: {len(tms)}")
    notes.append(f"Logical sources: {len(logical_sources)}")
    for tm in sorted(tms, key=str):
        if not any(g.objects(tm, logical_source)):
            errors.append(f"Triples map has no rml:logicalSource: {tm}")
        if not any(g.objects(tm, subject_map)):
            errors.append(f"Triples map has no rr:subjectMap: {tm}")
    unknown_parents = sorted(
        {parent for parent in g.objects(None, parent_triples_map) if parent not in tms},
        key=str,
    )
    if unknown_parents:
        errors.append(
            "Referencing object maps name non-existent parent triples maps: "
            + ", ".join(map(str, unknown_parents))
        )
    used_logical_sources = set(g.objects(None, logical_source))
    unknown_sources = sorted(used_logical_sources - logical_sources, key=str)
    unused_sources = sorted(logical_sources - used_logical_sources, key=str)
    if unknown_sources:
        errors.append(
            "Triples maps reference undeclared logical sources: "
            + ", ".join(map(str, unknown_sources))
        )
    if unused_sources:
        errors.append(
            "Logical sources are declared but unused: "
            + ", ".join(map(str, unused_sources))
        )
    for source_node in sorted(logical_sources, key=str):
        if len(list(g.objects(source_node, iterator))) != 1:
            errors.append(f"Logical source must have exactly one iterator: {source_node}")
        if len(list(g.objects(source_node, rml_source))) != 1:
            errors.append(f"Logical source must have exactly one source: {source_node}")
    notes.append(f"Referencing-object-map joins: {len(list(g.triples((None, parent_triples_map, None))))}")

    ontology_graph = Graph()
    try:
        ontology_graph.parse(ontology, format="turtle")
    except Exception as e:
        errors.append(f"BaseballO Turtle parse failed: {e}")
    else:
        declared_classes = set(ontology_graph.subjects(RDF.type, OWL.Class))
        declared_classes.update(ontology_graph.subjects(RDF.type, RDFS.Class))
        baseball_namespace = "https://baseballontology.org/"
        used_baseball_classes = {
            term
            for term in g.objects(None, rr_class)
            if str(term).startswith(baseball_namespace)
        }
        undeclared = sorted(used_baseball_classes - declared_classes, key=str)
        if undeclared:
            errors.append(
                "Mapping uses undeclared BaseballO classes: "
                + ", ".join(map(str, undeclared))
            )
        notes.append(
            f"BaseballO classes used: {len(used_baseball_classes)}; "
            f"undeclared: {len(undeclared)}"
        )

    mapping_text = mapping.read_text(encoding="utf-8")
    required_event_maps = (
        "PitchBallMotionMap",
        "BattedBallPlayMap",
        "BuntActMap",
        "BuntActContactSequenceMap",
        "BuntContactRecordAboutMap",
        "BuntFairBallRecordAboutMap",
        "BallJudgmentMap",
        "StrikeJudgmentMap",
        "FairBallAdjudicationMap",
        "FoulBallAdjudicationMap",
        "FoulTipAdjudicationMap",
        "PlateAppearanceResultJudgmentMap",
        "PlateAppearanceResultContainmentMap",
        "RunnerOutJudgmentMap",
        "RunnerReachJudgmentMap",
        "RunnerAdvanceJudgmentMap",
        "StolenBaseJudgmentMap",
        "SeasonMap",
        "SeasonPhaseMap",
        "GameSeasonPhaseMap",
        "SeasonSegmentCategoryMap",
        "SeasonSegmentReferenceSystemMap",
        "PitchEventRecordIdentifierMap",
        "PitchTypeReferenceSystemMap",
        "PitchTypeClassificationMap",
        "PitchTypeCategoryMap",
        "PitchTypeClassificationRecordMap",
        "BattedTrajectoryReferenceSystemMap",
        "BattedTrajectoryClassificationMap",
        "BattedTrajectoryCategoryMap",
        "BattedTrajectoryClassificationRecordMap",
        "ReviewOnFieldJudgmentMap",
        "ReviewOnFieldDecisionMap",
        "ReviewOnFieldAdjudicatedProcessMap",
        "ReviewChallengeMap",
        "ReviewPlayerChallengeMap",
        "PitchReviewOnFieldUmpireMap",
        "ReplayReviewActMap",
        "ChallengedReplayReviewActMap",
        "ReplayDecisionMap",
        "ReplayAdjudicatedProcessMap",
        "ReplayReviewResultMap",
        "ReviewEventRecordMap",
        "ChallengedReviewEventRecordAboutMap",
        "PitchReviewEventRecordAboutMap",
        "ReviewAffirmingResultMap",
        "ReviewOverturningResultMap",
        "ReviewBallToBallActMap",
        "ReviewStrikeToStrikeActMap",
        "ReviewOutToOutActMap",
        "ReviewSafeToSafeActMap",
        "ReviewBallToStrikeActMap",
        "ReviewStrikeToBallActMap",
        "ReviewOutToSafeActMap",
        "ReviewSafeToOutActMap",
    )
    missing_event_maps = [
        name for name in required_event_maps if f"<#{name}>" not in mapping_text
    ]
    if missing_event_maps:
        errors.append(
            "Required event-pattern Triples Maps are missing: "
            + ", ".join(missing_event_maps)
        )

    if (
        "@.result.eventType == 'walk'" not in mapping_text
        or "@.result.eventType == 'intent_walk'" not in mapping_text
    ):
        errors.append("Walk result mapping must cover both walk and intent_walk source tokens.")

    prohibited_fragments = (
        "/runner-act/out/",
        "/runner-act/score/",
        "/runner-act/reach/",
        "/runner-act/advance/",
        "SuccessfulSwingAct",
        "FailedSwingAct",
        "SuccessfulStealAttemptAct",
        "ActualHitProcess",
        "ActualErrorProcess",
        "plateAppearanceIsSacBunt",
        "rr:class base:PitchBallControlFailureProcess",
        "rr:class base:BaseTouchingProcess",
        "BattedCoordinateSource",
        "BattedBallLocationSiteMap",
        "BattedBallCoordinateICEMap",
        "BattedBallMotionLocationMap",
        "rr:predicate dcterms:identifier",
        "rr:predicate dcterms:type",
    )
    present_prohibited = [
        fragment for fragment in prohibited_fragments if fragment in mapping_text
    ]
    if present_prohibited:
        errors.append(
            "Mapping contains prohibited legacy or outcome-defined patterns: "
            + ", ".join(present_prohibited)
        )

    prohibited_execution_fragments = (
        'rr:parent "playEvents[*].playId"',
        "playEvents[-1:].playId",
        'rml:iterator "$.liveData.plays.allPlays[-1:]"',
        "{details.runner.id}/{details.playIndex}/{details.eventType}",
    )
    present_execution_fragments = [
        fragment
        for fragment in prohibited_execution_fragments
        if fragment in mapping_text
    ]
    if present_execution_fragments:
        errors.append(
            "Mapping contains processor-incompatible nested or slice references: "
            + ", ".join(present_execution_fragments)
        )

    required_context_fragments = (
        'rml:source "game-context.json"',
        "{_baseballO.atBatIndex}",
        "{_baseballO.batterId}",
        "{_baseballO.pitcherId}",
        "{_baseballO.runnerIndex}",
        "@._baseballO.isBuntAttempt",
        "@._baseballO.matchesBuntContactSource == true",
        "@._baseballO.hasReviewStatus == true",
        "@._baseballO.hasReviewChallengerId == true",
        "@._baseballO.hasPitchTypeCategory == true",
        "@._baseballO.hasBattedTrajectoryCategory == true",
        "@._baseballO.hasPlateAppearanceStructure == true",
        "@._baseballO.hasCompletedPlateAppearanceResult == true",
        "@._baseballO.endsAtScore",
        "@._baseballO.hasSupportedStartBase",
        "{_baseballO.terminalPitchPlayId}",
        '@._baseballO.reviewOutcome',
        '@._baseballO.reviewOriginalDecision',
        '@._baseballO.reviewFinalDecision',
        '@._baseballO.reviewPattern',
        '{_baseballO.reviewChallengerId}',
        'rml:reference "_baseballO.gameEndTime"',
        'rml:iterator "$._baseballO.seasonPhase"',
        'rml:reference "_baseballO.pitchTypeCategoryIri"',
        'rml:reference "pitchTypeReferenceSystemIri"',
        'rml:reference "_baseballO.battedTrajectoryCategoryIri"',
        'rml:reference "battedTrajectoryReferenceSystemIri"',
        'rml:iterator "$._baseballO.schedulePostponements[*]"',
        "rr:class base:BaseballGamePostponementAct",
        "rr:class base:BaseballGameSchedulePlan",
        "rr:predicate cco:ont00001833",
        "rr:predicate cco:ont00001942",
    )
    missing_context_fragments = [
        fragment for fragment in required_context_fragments if fragment not in mapping_text
    ]
    if missing_context_fragments:
        errors.append(
            "Mapping is missing required execution-context references: "
            + ", ".join(missing_context_fragments)
        )

if not source.exists():
    notes.append(f"Source is not present; source-specific checks skipped: {source}")
else:
    try:
        with source.open(encoding="utf-8") as source_file:
            j = json.load(source_file)
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"Source JSON could not be read: {e}")
        j = {}

    plays = j.get("liveData", {}).get("plays", {}).get("allPlays", [])
    game_pk = j.get("gamePk")
    notes.append(f"source: {source}")
    notes.append(f"gamePk: {game_pk}")
    notes.append(f"allPlays: {len(plays)}")
    if game_pk is None:
        errors.append("The source has no root gamePk.")
    if not plays:
        errors.append("The source has no canonical liveData.plays.allPlays records.")

    abstract_state = (
        j.get("gameData", {}).get("status", {}).get("abstractGameState")
    )
    if abstract_state != "Final":
        errors.append(
            "The direct mapping requires a completed game; "
            f"abstractGameState is {abstract_state!r}, not 'Final'."
        )

    at_bat_indexes = [p.get("about", {}).get("atBatIndex") for p in plays]
    if any(index is None for index in at_bat_indexes):
        errors.append("At least one play lacks about.atBatIndex.")
    duplicate_at_bats = [
        (key, count)
        for key, count in Counter(at_bat_indexes).items()
        if key is not None and count > 1
    ]
    if duplicate_at_bats:
        errors.append(f"Duplicate about.atBatIndex values: {duplicate_at_bats[:10]}")

    batter_ids = [p.get("matchup", {}).get("batter", {}).get("id") for p in plays]
    unsafe_batter_ids = sorted(
        {value for value in batter_ids if not str(value or "").isdigit()},
        key=str,
    )
    if unsafe_batter_ids:
        errors.append(
            "At least one play lacks a safe numeric matchup.batter.id: "
            + ", ".join(map(repr, unsafe_batter_ids[:10]))
        )

    pitches = [
        event
        for play in plays
        for event in play.get("playEvents", [])
        if event.get("isPitch") is True
    ]
    ids = [event.get("playId") for event in pitches]
    if any(value is None for value in ids):
        errors.append("At least one pitch lacks playId.")
    duplicate_pitch_ids = [
        (key, count)
        for key, count in Counter(ids).items()
        if key is not None and count > 1
    ]
    if duplicate_pitch_ids:
        errors.append(f"Duplicate pitch playId values: {duplicate_pitch_ids[:10]}")
    notes.append(f"pitches: {len(pitches)}; unique pitch playIds: {len(set(ids))}")

    specifically_mapped = set(
        re.findall(r"result\.eventType == '([^']+)'", mapping_text)
    )
    observed = {play.get("result", {}).get("eventType") for play in plays}
    generic_only = sorted(
        value for value in observed if value and value not in specifically_mapped
    )
    if generic_only:
        notes.append(
            "Observed result types with generic-only mapping: "
            + ", ".join(generic_only)
        )

    runner_keys = []
    legacy_runner_keys = []
    unsafe_runner_ids = set()
    supported_start_bases = {"1B", "2B", "3B"}
    unexpected_start_bases = set()
    for p in plays:
        at_bat_index = p.get("about", {}).get("atBatIndex")
        for runner_index, r in enumerate(p.get("runners", [])):
            m = r.get("movement", {})
            d = r.get("details", {})
            start_base = m.get("start")
            if start_base is not None and start_base not in supported_start_bases:
                unexpected_start_bases.add(start_base)
            rid = d.get("runner", {}).get("id")
            if not str(rid or "").isdigit():
                unsafe_runner_ids.add(rid)
            pi = d.get("playIndex")
            et = d.get("eventType")
            if m.get("isOut") is True:
                legacy_key = ("out", rid, pi, et, m.get("outBase"), m.get("outNumber"))
            elif (
                m.get("isOut") is False
                and m.get("end") == "score"
                and m.get("start") is None
            ):
                legacy_key = ("score-origin", rid, pi, et)
            elif m.get("isOut") is False and m.get("end") == "score":
                legacy_key = ("score-base", rid, pi, et, m.get("start"))
            elif m.get("isOut") is False and m.get("start") is None:
                legacy_key = ("reach", rid, pi, et, m.get("end"))
            else:
                legacy_key = ("advance", rid, pi, et, m.get("start"), m.get("end"))
            runner_keys.append((at_bat_index, runner_index))
            legacy_runner_keys.append(legacy_key)
    if unexpected_start_bases:
        errors.append(
            "Runner movement.start contains values outside the supported base set: "
            + ", ".join(sorted(map(str, unexpected_start_bases)))
        )
    if unsafe_runner_ids:
        errors.append(
            "At least one runner record lacks a safe numeric details.runner.id: "
            + ", ".join(map(repr, sorted(unsafe_runner_ids, key=str)[:10]))
        )
    duplicates = [(key, count) for key, count in Counter(runner_keys).items() if count > 1]
    if duplicates:
        errors.append(f"Runner structural-key collisions: {duplicates[:20]}")
    legacy_duplicates = [
        (key, count)
        for key, count in Counter(legacy_runner_keys).items()
        if count > 1
    ]
    notes.append(
        f"runner records: {len(runner_keys)}; "
        f"unique structural keys: {len(set(runner_keys))}; "
        f"legacy composite collisions handled: {len(legacy_duplicates)}"
    )

print("\n".join(notes))
if errors:
    print("\nERRORS:")
    print("\n".join("- " + error for error in errors))
    raise SystemExit(1)
print("Validation passed.")
