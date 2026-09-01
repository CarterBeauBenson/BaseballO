#!/usr/bin/env python3
"""Validate one generated BaseballO game graph without modifying the ontology."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef


BASE = Namespace("https://baseballontology.org/")
DATA = Namespace("https://baseballontology.org/data/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
CCO = Namespace("https://www.commoncoreontologies.org/")


def require_typed_link(
    graph: Graph,
    subjects: set[URIRef],
    predicate: URIRef,
    object_classes: tuple[URIRef, ...],
    label: str,
) -> None:
    missing = []
    for subject in subjects:
        objects = set(graph.objects(subject, predicate))
        if not any(
            (object_, RDF.type, object_class) in graph
            for object_ in objects
            for object_class in object_classes
        ):
            missing.append(subject)
    if missing:
        raise ValueError(
            f"{label}: {len(missing)} subject(s) lack the required typed link; "
            f"examples: {', '.join(map(str, missing[:5]))}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("rdf_file", type=Path)
    parser.add_argument("game_pk")
    parser.add_argument("--expected-plate-appearances", type=int)
    parser.add_argument("--expected-player-participants", type=int)
    parser.add_argument("--expected-batter-acts", type=int)
    parser.add_argument("--expected-pitches", type=int)
    parser.add_argument("--expected-batting-acts", type=int)
    parser.add_argument("--expected-contacts", type=int)
    parser.add_argument("--expected-runner-records", type=int)
    parser.add_argument("--expected-runner-resolutions", type=int)
    parser.add_argument("--expected-pitch-ball-control-failures", type=int)
    parser.add_argument("--expected-passed-balls", type=int)
    parser.add_argument("--expected-wild-pitches", type=int)
    parser.add_argument("--expected-uncaught-third-strikes", type=int)
    parser.add_argument("--expected-game-end")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = Graph()
    graph.parse(args.rdf_file, format="turtle")
    if not graph:
        raise ValueError("Generated RDF graph is empty")

    game = URIRef(f"{DATA}game/{args.game_pk}")
    if (game, RDF.type, BASE.BaseballGame) not in graph:
        raise ValueError(f"Expected BaseballGame assertion is missing for {game}")

    if any(graph.triples((None, RDF.type, BASE.BaseballParticipantRole))):
        raise ValueError("Generated RDF still contains the retired BaseballParticipantRole")

    persistent_role_patterns = {
        BASE.PlayerRole: re.compile(r"^https://baseballontology\.org/data/player/(\d+)/team/(\d+)/role/player$"),
        BASE.PitcherRole: re.compile(r"^https://baseballontology\.org/data/player/(\d+)/role/pitcher$"),
        BASE.FielderRole: re.compile(r"^https://baseballontology\.org/data/player/(\d+)/role/fielder$"),
        BASE.CatcherRole: re.compile(r"^https://baseballontology\.org/data/player/(\d+)/role/catcher$"),
        BASE.BaserunnerRole: re.compile(r"^https://baseballontology\.org/data/player/(\d+)/role/baserunner$"),
        BASE.UmpireRole: re.compile(r"^https://baseballontology\.org/data/person/(\d+)/role/umpire$"),
        BASE.OfficialScorerRole: re.compile(r"^https://baseballontology\.org/data/person/(\d+)/role/official-scorer$"),
        BASE.ManagerRole: re.compile(r"^https://baseballontology\.org/data/person/(\d+)/team/(\d+)/role/manager$"),
    }
    for role_class, pattern in persistent_role_patterns.items():
        for role in set(graph.subjects(RDF.type, role_class)):
            match = pattern.fullmatch(str(role))
            if match is None:
                raise ValueError(
                    f"{role_class.split('/')[-1]} does not use its approved role-scope IRI: {role}"
                )
            bearer_kind = "player" if "/data/player/" in str(role) else "person"
            expected_bearer = URIRef(f"{DATA}{bearer_kind}/{match.group(1)}")
            bearers = set(graph.objects(role, BFO.BFO_0000197))
            if bearers != {expected_bearer}:
                raise ValueError(
                    f"Persistent role bearer does not match its IRI: {role}; "
                    f"expected {expected_bearer}, got {sorted(map(str, bearers))}"
                )
            if role_class in (BASE.PlayerRole, BASE.ManagerRole):
                expected_team = URIRef(f"{DATA}team/{match.group(2)}")
                contexts = set(graph.objects(role, CCO.ont00001992))
                if contexts != {expected_team}:
                    raise ValueError(
                        f"Team-scoped occupation role context does not match its IRI: {role}; "
                        f"expected {expected_team}, got {sorted(map(str, contexts))}"
                    )
            expected_stasis = URIRef(f"{role}/stasis")
            stases = set(graph.objects(role, BFO.BFO_0000056))
            if stases != {expected_stasis}:
                raise ValueError(
                    f"Persistent role must participate in its open role stasis: {role}"
                )
            if (expected_stasis, RDF.type, CCO.ont00000824) not in graph:
                raise ValueError(f"Role stasis lacks CCO Stasis of Role typing: {expected_stasis}")
            if (expected_stasis, BFO.BFO_0000057, role) not in graph:
                raise ValueError(f"Role stasis does not have its role as participant: {expected_stasis}")
            if (expected_stasis, BFO.BFO_0000057, expected_bearer) not in graph:
                raise ValueError(f"Role stasis does not have the role bearer as participant: {expected_stasis}")
            expected_interval = URIRef(f"{expected_stasis}/temporal-interval")
            intervals = set(graph.objects(expected_stasis, BFO.BFO_0000199))
            if intervals != {expected_interval} or (
                expected_interval,
                RDF.type,
                BFO.BFO_0000038,
            ) not in graph:
                raise ValueError(
                    f"Role stasis must occupy its open Temporal Interval: {expected_stasis}"
                )

    player_roles = set(graph.subjects(RDF.type, BASE.PlayerRole))
    if (
        args.expected_player_participants is not None
        and len(player_roles) != args.expected_player_participants
    ):
        raise ValueError(
            "PlayerRole count does not match the accepted game roster: "
            f"expected {args.expected_player_participants}, got {len(player_roles)}"
        )
    for role in player_roles:
        bearer = next(iter(graph.objects(role, BFO.BFO_0000197)))
        team = next(iter(graph.objects(role, CCO.ont00001992)))
        if (game, BFO.BFO_0000057, bearer) not in graph:
            raise ValueError(f"Game does not have PlayerRole bearer as a participant: {bearer}")
        if (game, BFO.BFO_0000055, role) not in graph:
            raise ValueError(f"Game does not realize the team-scoped PlayerRole: {role}")
        if (role, BFO.BFO_0000054, game) not in graph:
            raise ValueError(f"Team-scoped PlayerRole lacks its game realization: {role}")
        if (game, BFO.BFO_0000057, team) not in graph:
            raise ValueError(f"PlayerRole team context does not participate in the game: {team}")

    for role_class in (BASE.UmpireRole, BASE.OfficialScorerRole):
        for role in set(graph.subjects(RDF.type, role_class)):
            bearer = next(iter(graph.objects(role, BFO.BFO_0000197)))
            if (game, BFO.BFO_0000057, bearer) not in graph:
                raise ValueError(f"Game does not have occupational-role bearer as participant: {bearer}")
            if (game, BFO.BFO_0000055, role) not in graph:
                raise ValueError(f"Game does not realize persistent occupational role: {role}")
            if (role, BFO.BFO_0000054, game) not in graph:
                raise ValueError(f"Persistent occupational role lacks its game realization: {role}")

    for territory_class in (BASE.FairTerritorySite, BASE.FoulTerritorySite):
        for territory in set(graph.subjects(RDF.type, territory_class)):
            if (territory, RDF.type, BASE.BaseballFieldSite) in graph:
                raise ValueError(f"Territory site is incorrectly typed as a BaseballFieldSite: {territory}")
            fields = {
                field
                for field in graph.objects(territory, BFO.BFO_0000176)
                if (field, RDF.type, BASE.BaseballFieldSite) in graph
            }
            if len(fields) != 1:
                raise ValueError(
                    f"Territory site must be continuant part of exactly one BaseballFieldSite: {territory}"
                )

    plate_appearances = len(set(graph.subjects(RDF.type, BASE.PlateAppearance)))
    batter_acts = len(set(graph.subjects(RDF.type, BASE.BatterAct)))
    pitches = len(set(graph.subjects(RDF.type, BASE.PitchAct)))
    if (
        args.expected_plate_appearances is not None
        and plate_appearances != args.expected_plate_appearances
    ):
        raise ValueError(
            "PlateAppearance count does not match the source: "
            f"expected {args.expected_plate_appearances}, got {plate_appearances}"
        )
    if args.expected_batter_acts is not None and batter_acts != args.expected_batter_acts:
        raise ValueError(
            "BatterAct count does not match the source: "
            f"expected {args.expected_batter_acts}, got {batter_acts}"
        )
    if args.expected_pitches is not None and pitches != args.expected_pitches:
        raise ValueError(
            "PitchAct count does not match the source: "
            f"expected {args.expected_pitches}, got {pitches}"
        )

    pitch_subjects = set(graph.subjects(RDF.type, BASE.PitchAct))
    require_typed_link(
        graph,
        pitch_subjects,
        BFO.BFO_0000063,
        (BASE.PitchBallMotionProcess,),
        "PitchAct to PitchBallMotionProcess chain",
    )
    require_typed_link(
        graph,
        pitch_subjects,
        BFO.BFO_0000132,
        (BASE.PlateAppearance,),
        "PitchAct to PlateAppearance context",
    )
    require_typed_link(
        graph,
        pitch_subjects,
        BFO.BFO_0000057,
        (CCO.ont00001262,),
        "PitchAct to pitcher Person participation",
    )
    require_typed_link(
        graph,
        pitch_subjects,
        BFO.BFO_0000055,
        (BASE.PitcherRole,),
        "PitchAct to PitcherRole realization",
    )

    for pitch in pitch_subjects:
        people = {
            participant
            for participant in graph.objects(pitch, BFO.BFO_0000057)
            if (participant, RDF.type, CCO.ont00001262) in graph
        }
        roles = {
            role
            for role in graph.objects(pitch, BFO.BFO_0000055)
            if (role, RDF.type, BASE.PitcherRole) in graph
        }
        if not any((role, BFO.BFO_0000197, person) in graph for role in roles for person in people):
            raise ValueError(
                f"PitchAct pitcher Person and PitcherRole bearer do not agree: {pitch}"
            )

    batting_acts = {
        subject
        for class_ in (BASE.SwingAct, BASE.BuntAct)
        for subject in graph.subjects(RDF.type, class_)
    }
    if (
        args.expected_batting_acts is not None
        and len(batting_acts) != args.expected_batting_acts
    ):
        raise ValueError(
            "SwingAct/BuntAct count does not match the source: "
            f"expected {args.expected_batting_acts}, got {len(batting_acts)}"
        )
    contact_subjects = set(graph.subjects(RDF.type, BASE.BatBallContactProcess))
    if args.expected_contacts is not None and len(contact_subjects) != args.expected_contacts:
        raise ValueError(
            "BatBallContactProcess count does not match the source: "
            f"expected {args.expected_contacts}, got {len(contact_subjects)}"
        )
    require_typed_link(
        graph,
        contact_subjects,
        BFO.BFO_0000132,
        (BASE.PlateAppearance,),
        "BatBallContactProcess to PlateAppearance context",
    )
    require_typed_link(
        graph,
        contact_subjects,
        BFO.BFO_0000063,
        (BASE.BattedBallMotionProcess,),
        "BatBallContactProcess to BattedBallMotionProcess chain",
    )

    baserunning_acts = set(graph.subjects(RDF.type, BASE.BaserunningAct))
    runner_resolutions = set(graph.subjects(RDF.type, BASE.RunnerResolutionProcess))
    runner_records = {
        subject
        for subject in graph.subjects(RDF.type, BASE.BaseballEventRecord)
        if f"{DATA}game/{args.game_pk}/runner-record/" in str(subject)
    }
    if args.expected_runner_records is not None and len(runner_records) != args.expected_runner_records:
        raise ValueError(
            "runner BaseballEventRecord count does not match the source: expected "
            f"{args.expected_runner_records}, got {len(runner_records)}"
        )
    if args.expected_runner_resolutions is not None:
        for label, subjects in (
            ("BaserunningAct", baserunning_acts),
            ("RunnerResolutionProcess", runner_resolutions),
        ):
            if len(subjects) != args.expected_runner_resolutions:
                raise ValueError(
                    f"{label} count does not match resolved source movements: expected "
                    f"{args.expected_runner_resolutions}, got {len(subjects)}"
                )
    require_typed_link(
        graph,
        baserunning_acts,
        BFO.BFO_0000132,
        (BASE.PlateAppearance,),
        "BaserunningAct to PlateAppearance context",
    )
    require_typed_link(
        graph,
        runner_resolutions,
        BFO.BFO_0000132,
        (BASE.PlateAppearance,),
        "RunnerResolutionProcess to PlateAppearance context",
    )
    require_typed_link(
        graph,
        runner_resolutions,
        BFO.BFO_0000062,
        (BASE.BaserunningAct,),
        "RunnerResolutionProcess from BaserunningAct chain",
    )
    missing_contact_acts = []
    for contact in contact_subjects:
        preceding = set(graph.subjects(BFO.BFO_0000063, contact))
        if not any(
            (act, RDF.type, act_class) in graph
            for act in preceding
            for act_class in (BASE.SwingAct, BASE.BuntAct)
        ):
            missing_contact_acts.append(contact)
    if missing_contact_acts:
        raise ValueError(
            "BatBallContactProcess lacks a preceding SwingAct or BuntAct: "
            + ", ".join(map(str, missing_contact_acts[:5]))
        )

    institutional_patterns = (
        (BASE.BallProcess, (BASE.BallJudgmentAct,)),
        (BASE.StrikeProcess, (BASE.StrikeJudgmentAct, BASE.FoulTipJudgmentAct)),
        (BASE.FairBallProcess, (BASE.FairBallJudgmentAct,)),
        (BASE.FoulBallProcess, (BASE.FoulBallJudgmentAct,)),
        (BASE.FoulTipProcess, (BASE.FoulTipJudgmentAct,)),
        (BASE.OutProcess, (BASE.OutJudgmentAct,)),
        (BASE.SafeProcess, (BASE.SafeJudgmentAct,)),
        (BASE.RunProcess, (BASE.RunJudgmentAct,)),
        (BASE.StolenBaseProcess, (BASE.StolenBaseJudgmentAct,)),
        (BASE.PassedBallProcess, (BASE.PassedBallJudgmentAct,)),
        (BASE.WildPitchProcess, (BASE.WildPitchJudgmentAct,)),
        (BASE.UncaughtThirdStrikeProcess, (BASE.UmpireJudgmentAct,)),
    )
    for process_class, judgment_classes in institutional_patterns:
        process_subjects = set(graph.subjects(RDF.type, process_class))
        require_typed_link(
            graph,
            process_subjects,
            BFO.BFO_0000117,
            judgment_classes,
            f"{process_class.split('/')[-1]} adjudication",
        )

    exact_new_pattern_counts = (
        # The accepted MLB-game contract requires this count to be zero.
        # Authoritative SHACL independently rejects every such instance.
        (
            BASE.PitchBallControlFailureProcess,
            args.expected_pitch_ball_control_failures,
            "PitchBallControlFailureProcess",
        ),
        (BASE.PassedBallProcess, args.expected_passed_balls, "PassedBallProcess"),
        (BASE.WildPitchProcess, args.expected_wild_pitches, "WildPitchProcess"),
        (
            BASE.UncaughtThirdStrikeProcess,
            args.expected_uncaught_third_strikes,
            "UncaughtThirdStrikeProcess",
        ),
    )
    for process_class, expected_count, label in exact_new_pattern_counts:
        if expected_count is None:
            continue
        actual_count = len(set(graph.subjects(RDF.type, process_class)))
        if actual_count != expected_count:
            raise ValueError(
                f"{label} count does not match the source: expected "
                f"{expected_count}, got {actual_count}"
            )

    control_failures = set(
        graph.subjects(RDF.type, BASE.PitchBallControlFailureProcess)
    )
    require_typed_link(
        graph,
        control_failures,
        BFO.BFO_0000062,
        (BASE.PitchBallMotionProcess,),
        "PitchBallControlFailureProcess physical predecessor",
    )
    require_typed_link(
        graph,
        control_failures,
        BFO.BFO_0000057,
        (BASE.Baseball,),
        "PitchBallControlFailureProcess Baseball participation",
    )
    for process_class, judgment_class, rule_class in (
        (BASE.PassedBallProcess, BASE.PassedBallJudgmentAct, BASE.PassedBallRule),
        (BASE.WildPitchProcess, BASE.WildPitchJudgmentAct, BASE.WildPitchRule),
    ):
        processes = set(graph.subjects(RDF.type, process_class))
        require_typed_link(
            graph,
            processes,
            BFO.BFO_0000117,
            (judgment_class,),
            f"{process_class.split('/')[-1]} scoring judgment",
        )
        require_typed_link(
            graph,
            processes,
            CCO.ont00001920,
            (rule_class,),
            f"{process_class.split('/')[-1]} governing rule",
        )

    uncaught_third_strikes = set(
        graph.subjects(RDF.type, BASE.UncaughtThirdStrikeProcess)
    )
    require_typed_link(
        graph,
        uncaught_third_strikes,
        BFO.BFO_0000117,
        (BASE.StrikeoutProcess,),
        "UncaughtThirdStrikeProcess strikeout part",
    )
    fair_subjects = set(graph.subjects(RDF.type, BASE.FairBallProcess))
    require_typed_link(
        graph,
        fair_subjects,
        BFO.BFO_0000063,
        (BASE.BaseballInstitutionalProcess,),
        "FairBallProcess to plate-appearance result chain",
    )

    plate_result_subjects = {
        subject
        for subject in graph.subjects(RDF.type, BASE.BaseballInstitutionalProcess)
        if str(subject).endswith("/result")
    }
    require_typed_link(
        graph,
        plate_result_subjects,
        BFO.BFO_0000117,
        (BASE.BaseballAdjudicationAct,),
        "Plate-appearance result adjudication",
    )

    for foul_tip in graph.subjects(RDF.type, BASE.FoulTipProcess):
        if (foul_tip, RDF.type, BASE.StrikeProcess) not in graph:
            raise ValueError(
                f"FoulTipProcess is not the same counted individual as StrikeProcess: {foul_tip}"
            )

    if args.expected_game_end is not None:
        intervals = set(graph.objects(game, BFO.BFO_0000199))
        end_instants = {
            instant for interval in intervals for instant in graph.objects(interval, BFO.BFO_0000224)
        }
        game_end_values = {
            value.toPython()
            for timestamp in graph.subjects(RDF.type, BASE.BaseballTimestampICE)
            if (timestamp, CCO.ont00001808, game) in graph
            and any((timestamp, CCO.ont00001916, instant) in graph for instant in end_instants)
            for value in graph.objects(timestamp, CCO.ont00001767)
        }
        expected_game_end = datetime.fromisoformat(
            args.expected_game_end.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        normalized_game_end_values = {
            value.astimezone(timezone.utc)
            for value in game_end_values
            if isinstance(value, datetime) and value.tzinfo is not None
        }
        if normalized_game_end_values != {expected_game_end} or len(game_end_values) != 1:
            raise ValueError(
                "Game terminal timestamp does not match the final source play: "
                f"expected {args.expected_game_end!r}, "
                f"got {[str(value) for value in game_end_values]!r}"
            )

    record_subjects = set(graph.subjects(RDF.type, BASE.BaseballEventRecord))
    process_or_act_subjects = {
        subject
        for class_ in (
            BASE.PitchAct,
            BASE.SwingAct,
            BASE.BuntAct,
            BASE.BaseballPhysicalProcess,
            BASE.BaseballInstitutionalProcess,
        )
        for subject in graph.subjects(RDF.type, class_)
    }
    collapsed_records = record_subjects & process_or_act_subjects
    if collapsed_records:
        raise ValueError(
            "BaseballEventRecord identity is collapsed with an act or process: "
            + ", ".join(map(str, list(collapsed_records)[:5]))
        )

    subjects = {subject for subject in graph.subjects()}
    predicates = {predicate for predicate in graph.predicates()}
    classes = {class_ for class_ in graph.objects(None, RDF.type)}
    print(f"Generated triples: {len(graph)}")
    print(f"Distinct subjects: {len(subjects)}")
    print(f"Distinct predicates: {len(predicates)}")
    print(f"Distinct asserted classes: {len(classes)}")
    print(f"Plate appearances: {plate_appearances}")
    print(f"Persistent player roles realized by the game: {len(player_roles)}")
    print(f"Batter acts: {batter_acts}")
    print(f"Pitches: {pitches}")
    print(f"Pitches with complete ancestor context: {len(pitch_subjects)}")
    print(f"Swing/bunt acts with complete ancestor context: {len(batting_acts)}")
    print(f"Pitch motions: {len(set(graph.subjects(RDF.type, BASE.PitchBallMotionProcess)))}")
    print(f"Bat-ball contacts: {len(contact_subjects)}")
    print(f"Baserunning acts: {len(baserunning_acts)}")
    print(f"Runner resolutions: {len(runner_resolutions)}")
    print(f"Runner records: {len(runner_records)}")
    print(f"Pitch-ball control failures: {len(control_failures)}")
    print(f"Passed balls: {len(set(graph.subjects(RDF.type, BASE.PassedBallProcess)))}")
    print(f"Wild pitches: {len(set(graph.subjects(RDF.type, BASE.WildPitchProcess)))}")
    print(f"Uncaught third strikes: {len(uncaught_third_strikes)}")
    print(f"Plate-appearance results with adjudication: {len(plate_result_subjects)}")
    print(f"Expected game present: {game}")
    if args.expected_game_end is not None:
        print(f"Game terminal timestamp: {args.expected_game_end}")


if __name__ == "__main__":
    main()
