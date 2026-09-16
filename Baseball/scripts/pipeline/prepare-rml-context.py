#!/usr/bin/env python3
"""Create an isolated ancestor-aware JSON context for RMLMapper execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import date, datetime
from collections import defaultdict
from pathlib import Path


SAFE_IRI_SEGMENT = re.compile(r"^[A-Za-z0-9._~-]+$")
CONTEXT_KEY = "_baseballO"
REVIEW_DESCRIPTION = re.compile(
    r"^(?P<initiator>.+?) (?P<action>challenged|reviewed) \((?P<review_type>[^)]+)\)"
    r"(?:, call on the field was (?P<status>confirmed|overturned|upheld))?:",
    re.IGNORECASE,
)
REVIEW_STATUS_BY_NARRATIVE = {
    "confirmed": "confirmed",
    "upheld": "confirmed",
    "overturned": "overturned",
}
PITCH_DECISION_BY_CALL_CODE = {
    "B": "ball",
    "*B": "ball",
    "C": "strike",
}
BUNT_CALL_CODES = {"L", "M", "O"}
BUNT_TRAJECTORIES = {"bunt_grounder", "bunt_popup", "bunt_line_drive"}
ADMINISTRATIVE_EVENT_TYPES = {"game_advisory"}
# A1 and accepted B2 express contact-play membership only. B2 admits the
# bounded other_out continuation after complete C1 source reconciliation.
BATTED_RUNNER_RESULT_TYPES = {
    "single", "double", "triple", "home_run", "field_out", "force_out",
    "grounded_into_double_play", "double_play", "sac_fly", "sac_bunt",
    "fielders_choice", "field_error",
}
PITCH_TYPE_CATEGORY_BY_CODE = {
    "FF": "FourSeamFastballPitchTypeICE",
    "SI": "SinkerPitchTypeICE",
    "FC": "CutterPitchTypeICE",
    "SL": "SliderPitchTypeICE",
    "ST": "SweeperPitchTypeICE",
    "SV": "SlurvePitchTypeICE",
    "CU": "CurveballPitchTypeICE",
    "KC": "KnuckleCurvePitchTypeICE",
    "CS": "SlowCurvePitchTypeICE",
    "CH": "ChangeupPitchTypeICE",
    "FS": "SplitterPitchTypeICE",
    "FO": "ForkballPitchTypeICE",
    "SC": "ScrewballPitchTypeICE",
    "KN": "KnuckleballPitchTypeICE",
    "EP": "EephusPitchTypeICE",
}
BATTED_TRAJECTORY_CATEGORY_BY_TOKEN = {
    "ground_ball": "GroundBallTrajectoryICE",
    "line_drive": "LineDriveTrajectoryICE",
    "fly_ball": "FlyBallTrajectoryICE",
    "popup": "PopUpTrajectoryICE",
}
SEASON_PHASE_BY_GAME_TYPE = {
    "S": ("preseason", "BaseballPreseasonPhase", "PreseasonSegmentTypeICE"),
    "R": ("regular-season", "BaseballRegularSeasonPhase", "RegularSeasonSegmentTypeICE"),
    "F": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "D": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "L": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "W": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "C": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "P": ("postseason", "BaseballPostseasonPhase", "PostseasonSegmentTypeICE"),
    "A": ("all-star", "BaseballAllStarPhase", "AllStarSegmentTypeICE"),
}
OUT_SAFE_REVIEW_TYPES = {
    "catch_or_drop",
    "force_play",
    "play_at_1st",
    "tag_play",
    "tag_up_play",
}


def batted_runner_resolution_links(play: dict, at_bat_index: str, histories: dict | None = None) -> list[dict[str, str]]:
    """Expose evidenced existing resolution identities for A1 RML parthood.

    A PA or event-index join alone is insufficient. Require a completed,
    recognized contact result and a uniquely indexed terminal in-play pitch,
    A1 admits matching result classifications. B2's mixed other_out case
    additionally requires the accepted complete-source/C1 continuation gate.
    This does not calculate attribution, destination, or trajectory state.
    """
    result_type = play.get("result", {}).get("eventType")
    if (
        play.get("about", {}).get("isComplete") is not True
        or result_type not in BATTED_RUNNER_RESULT_TYPES
    ):
        return []
    events = play.get("playEvents", [])
    pitches = [event for event in events if event.get("isPitch") is True]
    if not pitches:
        return []
    terminal = pitches[-1]
    details = terminal.get("details", {})
    event_index = terminal.get("index")
    play_id = terminal.get("playId")
    if (
        details.get("isInPlay") is not True
        or details.get("call", {}).get("code") not in {"X", "D", "E"}
        or type(event_index) is not int
        or event_index < 0
        or not isinstance(play_id, str)
        or not SAFE_IRI_SEGMENT.fullmatch(play_id)
        or sum(event.get("index") == event_index for event in events) != 1
    ):
        return []
    rows = play.get('runners', [])
    mixed = any(row.get('details', {}).get('eventType') == 'other_out' for row in rows)
    if mixed:
        if not contact_continuation_supported(play, at_bat_index, event_index, histories):
            return []  # Never expose only the convenient half of a B2 play.
    links = []
    for position, runner in enumerate(play.get("runners", [])):
        runner_details = runner.get("details", {})
        movement = runner.get("movement", {})
        runner_event_index = runner_details.get("playIndex")
        if (
            type(runner_event_index) is not int
            or runner_event_index != event_index
            or runner_details.get("eventType") not in ({result_type, 'other_out'} if mixed else {result_type})
            or type(movement.get("isOut")) is not bool
        ):
            continue
        # These branches reuse the current Runner*Source identity selection.
        if movement["isOut"]:
            kind = "out"
        elif movement.get("end") == "score":
            kind = "score"
        elif movement.get("start") in {"1B", "2B", "3B"}:
            kind = "advance"
        else:
            kind = "reach"
        links.append({
            "atBatIndex": at_bat_index,
            "runnerIndex": str(position),
            "resolutionKind": kind,
            "playId": play_id,
        })
    return links


def contact_continuation_supported(play, at_bat_index, terminal_index, histories):
    """B2 source selection, never a graph-conformance or score calculation."""
    if not histories or histories.get('sourceConsistency') != 'consistent':
        return False
    if play.get('about', {}).get('hasReview') is not False or play.get('reviewDetails'):
        review = accounted_runner_history_reviews(play)
        if review['issues'] or review.get('accountedFieldReview', {}).get('eventIndex') != terminal_index:
            return False
    events, rows = play.get('playEvents', []), play.get('runners', [])
    if [e.get('index') for e in events] != list(range(len(events))):
        return False
    independent_prefix = {'stolen_base_2b', 'stolen_base_3b', 'stolen_base_home',
                          'wild_pitch', 'passed_ball', 'balk', 'defensive_indiff'}
    prefix_indexes = set()
    for event in events:
        details = event.get('details', {})
        selected = [r for r in rows if r.get('details', {}).get('playIndex') == event['index']]
        before_contact = event['index'] < terminal_index
        independent = (before_contact and details.get('eventType') in independent_prefix and bool(selected)
                       and all(r['details'].get('eventType') == details['eventType'] for r in selected))
        empty_attempt = (before_contact and event.get('type') in {'pickoff', 'stepoff'}
                         and event.get('isPitch') is False and not selected)
        if independent:
            prefix_indexes.add(event['index'])
        if (event.get('reviewDetails') or details.get('hasReview') is True or event.get('isSubstitution') is True
                or (event.get('isPitch') is not True and details.get('eventType') not in {'batter_timeout', 'mound_visit'}
                    and not independent and not empty_attempt)):
            return False
    allowed = {play.get('result', {}).get('eventType'), 'other_out'}
    membership = defaultdict(list)
    for item in histories.get('episodeMembership', []):
        if item['atBatIndex'] == at_bat_index:
            membership[item['runnerIndex']].append(item)
    personal = {}
    for index, row in enumerate(rows):
        details = row.get('details', {})
        matches = membership[str(index)]
        terminal_member = details.get('playIndex') == terminal_index and details.get('eventType') in allowed
        prefix_member = details.get('playIndex') in prefix_indexes and details.get('eventType') in independent_prefix
        if (not (terminal_member or prefix_member) or len(matches) != 1 or not matches[0].get('lifetimeKey')
                or str(details.get('runner', {}).get('id')) != matches[0]['runnerId']):
            return False
        runner, lifetime = matches[0]['runnerId'], matches[0]['lifetimeKey']
        if runner in personal and personal[runner] != lifetime:
            return False
        personal[runner] = lifetime
    return bool(rows)


def runner_episode_evidence(play: dict, at_bat_index: str) -> dict[str, list[dict]]:
    """Select the existing act/resolution pair and supported safe decision content.

    No directive or immediately preceding stasis is inferred from movement rows.
    The RML/SHACL layer expresses and validates the reviewed structural pattern.
    """
    products = {"runnerEpisodes": [], "safeDecisionDestinations": []}
    complete = play.get("about", {}).get("isComplete") is True
    for position, row in enumerate(play.get("runners", [])):
        movement = row.get("movement", {})
        runner_id = row.get("details", {}).get("runner", {}).get("id")
        if type(movement.get("isOut")) is not bool or not str(runner_id).isdigit():
            continue
        kind = ("out" if movement["isOut"] else
                "score" if movement.get("end") == "score" else
                "advance" if movement.get("start") in {"1B", "2B", "3B"} else "reach")
        item = {"atBatIndex": at_bat_index, "runnerIndex": str(position),
                "resolutionKind": kind, "runnerId": str(runner_id)}
        products["runnerEpisodes"].append(item)
        if complete and not movement["isOut"] and movement.get("end") in {"1B", "2B", "3B"}:
            products["safeDecisionDestinations"].append({**item, "baseCode": movement["end"]})
    return products


def supported_walkoff_boundary(document: dict, last_play: dict) -> dict | None:
    """Q8 source boundary only; the caller still reconciles the entire half."""
    plays = document['liveData']['plays']['allPlays']
    about, result = last_play['about'], last_play['result']
    linescore = document['liveData']['linescore']
    scheduled = linescore.get('scheduledInnings')
    status = document['gameData'].get('status', {})
    if (last_play is not plays[-1] or len(plays) < 2 or about.get('halfInning') != 'bottom'
            or type(scheduled) is not int or scheduled < 1 or about.get('inning', 0) < scheduled
            or status.get('abstractGameState') != 'Final' or status.get('codedGameState') != 'F'
            or about.get('isScoringPlay') is not True or last_play.get('count', {}).get('outs') not in (0, 1, 2)):
        return None
    prior = plays[-2]['result']
    scores = [result.get('awayScore'), result.get('homeScore'), prior.get('awayScore'), prior.get('homeScore')]
    if any(type(n) is not int or n < 0 for n in scores):
        return None
    away, home, before_away, before_home = scores
    if (home <= away or before_home > before_away or away != before_away
            or home != linescore.get('teams', {}).get('home', {}).get('runs')
            or away != linescore.get('teams', {}).get('away', {}).get('runs')):
        return None
    scores = [r for r in last_play['runners'] if r['details'].get('isScoringEvent') is True]
    events = last_play['playEvents']
    if not events or not scores or home - before_home != len(scores):
        return None
    terminal = events[-1]
    if (any(r['details']['playIndex'] != terminal['index'] or r['movement'].get('end') != 'score'
            or r['movement'].get('isOut') is not False for r in scores)
            or not SAFE_IRI_SEGMENT.fullmatch(str(terminal.get('playId') or ''))
            or terminal.get('endTime') != about.get('endTime')):
        return None
    return dict(eventId=terminal['playId'], endTime=about['endTime'],
                gameEndInstantIri=f"https://baseballontology.org/data/game/{document['gamePk']}/temporal-instant/end")


def accounted_runner_count_reviews(play: dict) -> dict:
    """E1: reconcile completed operative pitch calls before runner continuity.

    This does not infer an original call or review eligibility. C1 needs the
    final operative effects; M2 separately controls the review RDF pattern.
    Field-play reviews and contradictory/in-progress calls remain unresolved.
    """
    events = play.get('playEvents', [])
    pitches = [e for e in events if e.get('isPitch') is True]
    identified, problems = {}, []
    pa_review = play.get('reviewDetails')
    pa_flag = play.get('about', {}).get('hasReview')
    terminal_review = None
    if pa_flag is not False or pa_review:
        match = REVIEW_DESCRIPTION.search(play.get('result', {}).get('description', ''))
        if (pa_flag is not True or not pitches or not isinstance(pa_review, dict) or pa_review.get('inProgress') is not False
                or type(pa_review.get('isOverturned')) is not bool or not match
                or match.group('review_type').lower() != 'pitch result'):
            problems.append('UNRESOLVED_PA_REVIEW')
        else:
            narrative = match.group('status')
            if narrative and (REVIEW_STATUS_BY_NARRATIVE[narrative.lower()] == 'overturned') != pa_review['isOverturned']:
                problems.append('CONFLICTING_PA_REVIEW')
            else:
                terminal_review = pitches[-1]
    for position, event in enumerate(events):
        details = event.get('details', {})
        event_review = event.get('reviewDetails')
        candidate = event_review or (pa_review if event is terminal_review else None)
        if candidate is None and details.get('hasReview') is not True:
            continue
        code = details.get('call', {}).get('code')
        kind = PITCH_DECISION_BY_CALL_CODE.get(code)
        if (not isinstance(candidate, dict) or candidate.get('inProgress') is not False
                or type(candidate.get('isOverturned')) is not bool or candidate.get('reviewType') != 'MJ'
                or event.get('isPitch') is not True or not kind
                or details.get('isBall') is not (kind == 'ball') or details.get('isStrike') is not (kind == 'strike')
                or details.get('isInPlay') is not False
                or not SAFE_IRI_SEGMENT.fullmatch(str(event.get('playId') or ''))):
            problems.append('UNRESOLVED_EVENT_REVIEW')
            continue
        if event is terminal_review and event_review and any(event_review.get(k) != pa_review.get(k)
                for k in ('inProgress','isOverturned','reviewType')):
            problems.append('CONFLICTING_EVENT_AND_PA_REVIEW')
            continue
        before = events[position-1].get('count', {}) if position else dict(balls=0,strikes=0)
        after = event.get('count', {})
        if (any(type(c.get(key)) is not int or not 0 <= c[key] <= limit
                for c in (before,after) for key,limit in (('balls',4),('strikes',3)))
                or before['balls'] >= 4 or before['strikes'] >= 3
                or after['balls'] != before['balls'] + (kind == 'ball')
                or after['strikes'] != before['strikes'] + (kind == 'strike')):
            problems.append('CONFLICTING_OPERATIVE_REVIEW_COUNT')
            continue
        identified[event['index']] = dict(playId=event['playId'], kind=kind,
            overturned=candidate['isOverturned'], scope='final operative pitch call; original call not inferred')
    return dict(events=identified, issues=problems)


def accounted_runner_history_reviews(play: dict) -> dict:
    """Account for the final effects of a bounded completed field review.

    E1 admits the reconciled final feed, not an inferred original decision or
    affected-player assignment. Count-award selection keeps its stricter
    pitch-review contract. C1 still checks every final movement, out and base.
    """
    review = play.get('reviewDetails')
    match = REVIEW_DESCRIPTION.search(play.get('result', {}).get('description', ''))
    events = play.get('playEvents', [])
    terminal = events[-1] if events else {}
    details = terminal.get('details', {})
    field_type = {'tag play': 'MA', 'play at 1st': 'MF'}
    label = match.group('review_type').lower() if match else None
    disposition = match.group('status') if match else None
    terminal_rows = [r for r in play.get('runners', [])
                     if r.get('details', {}).get('playIndex') == terminal.get('index')]
    supported = (play.get('about', {}).get('hasReview') is True
        and play['about'].get('isComplete') is True
        and isinstance(review, dict) and review.get('inProgress') is False
        and type(review.get('isOverturned')) is bool and label in field_type
        and review.get('reviewType') == field_type[label] and disposition is not None
        and (REVIEW_STATUS_BY_NARRATIVE[disposition.lower()] == 'overturned') == review['isOverturned']
        and terminal.get('isPitch') is True and details.get('isInPlay') is True
        and SAFE_IRI_SEGMENT.fullmatch(str(terminal.get('playId') or ''))
        and not terminal.get('reviewDetails') and details.get('hasReview') is False
        and bool(terminal_rows)
        and all(type(r.get('movement', {}).get('isOut')) is bool
                and type(r.get('details', {}).get('isScoringEvent')) is bool for r in terminal_rows))
    if not supported:
        return accounted_runner_count_reviews(play)
    # Only the positively accounted terminal field review leaves the count
    # review scope. Earlier event reviews are still examined independently.
    count_scope = {**play, 'about': {**play['about'], 'hasReview': False}}
    count_scope.pop('reviewDetails', None)
    result = accounted_runner_count_reviews(count_scope)
    result['accountedFieldReview'] = dict(eventIndex=terminal['index'], playId=terminal['playId'],
        reviewType=review['reviewType'], overturned=review['isOverturned'])
    return result


def personal_runner_histories(raw: bytes) -> dict:
    """E1/C1 source reconciliation, independent of mapped-row counts.

    Only fully reconciled half innings enter this first source selection.
    Unknown review/substitution effects withhold the whole half, not just the
    inconvenient row. No location, adjudication or strict precedence is minted.
    Temporal values below are event bounds, not claimed exact runner timestamps.
    """
    checker = Path(__file__).resolve().parents[2] / 'sources/mlb-game/pipeline/reconcile-metric-source.py'
    canonical = checker.read_text(encoding='utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').encode()
    if hashlib.sha256(canonical).hexdigest() != '4b4bd708b1f0a8c9936d2e5c9f42c298840dd65d1a2995892810ddcb9b11dc90':
        raise ValueError('Runner-history source reconciler differs from its reviewed dependency pin')
    spec = importlib.util.spec_from_file_location('runner_source_reconciler', checker)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    document = json.loads(raw)
    source = module.reconcile(raw, str(document['gamePk']))
    result = dict(inputSha256=source['inputSha256'], sourceRevision=source['sourceRevision'],
                  sourceAuthorityDecision='archive/design-records/metric-source-c1-operation-2026-09-14/review.json',
                  sourceConsistency=source['status'], histories=[], episodeMembership=[], halves=[], boundaryIssues=[],
                  graphCoverageVerified=False, metricPopulationAdmitted=False)
    if source['status'] != 'consistent':
        result['sourceIssues'] = source['issues']
        return result
    groups = defaultdict(list)
    for play in document['liveData']['plays']['allPlays']:
        groups[(play['about']['inning'], play['about']['halfInning'])].append(play)

    def instant(value):
        try:
            t = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return t if t.tzinfo is not None else None
        except (AttributeError, ValueError):
            return None

    neutral = {'batter_timeout', 'mound_visit', 'pitching_substitution',
               'defensive_substitution', 'defensive_switch'}
    advisories = {'Status Change - Pre-Game', 'Status Change - Warmup',
                  'Status Change - In Progress', 'Mound Visit.', 'Injury Delay.'}
    independent = {'balk', 'wild_pitch', 'passed_ball', 'stolen_base_2b', 'stolen_base_3b',
                   'stolen_base_home', 'caught_stealing_2b', 'caught_stealing_3b',
                   'caught_stealing_home', 'pickoff_1b', 'pickoff_2b', 'pickoff_3b',
                   'defensive_indiff', 'pickoff_error_1b', 'pickoff_error_2b', 'pickoff_error_3b'}
    for (inning, half), plays in groups.items():
        active, histories, memberships, problems = {}, [], [], []
        outs = 0
        previous_pa_end = None
        last_event_end = None

        def block(code, pa=None):
            problems.append(dict(code=code, atBatIndex=pa))

        def finish(item, anchor, terminal, bound):
            # Stable serialization of the reviewed lifetime anchors, not a
            # source revision, PA index or row-position identity for the whole.
            identity = [str(document['gamePk']), item['runnerId'], item['entryAnchor'], anchor]
            key = hashlib.sha256(json.dumps(identity, separators=(',', ':')).encode()).hexdigest()
            completed = dict(item, lifetimeKey=key, terminationAnchor=anchor,
                             terminal=terminal, latestEndBound=bound)
            if terminal == 'game-ended':
                completed['gameEndInstantIri'] = f"https://baseballontology.org/data/game/{document['gamePk']}/temporal-instant/end"
            histories.append(completed)
            memberships.extend(dict(lifetimeKey=key, **episode) for episode in item['episodes'])

        for play in plays:
            pa = play['atBatIndex']; about = play['about']; rows = play['runners']
            pa_start, pa_end = instant(about['startTime']), instant(about['endTime'])
            if previous_pa_end and pa_start < previous_pa_end:
                # Overlapping PA header bounds defeat a PA-start projection.
                # C1 uses independently bounded movement events; their order
                # is checked across PAs below, not inferred from array order.
                result['boundaryIssues'].append(dict(code='AMBIGUOUS_PA_TIME_ORDER', atBatIndex=pa,
                    previousEndBound=previous_pa_end.isoformat(), startBound=about['startTime']))
            previous_pa_end = pa_end
            reviews = accounted_runner_history_reviews(play)
            if reviews['issues']:
                block('UNRESOLVED_REVIEW_EFFECT', pa)
            # Q4 validates actual batter changes independently of runner
            # replacement. A known PH with no movement and no active outgoing
            # runner is administrative for this personal-history census.
            try:
                batter_participation_context(play, str(document['gamePk']), source_consistent=True)
                batting_changes_supported = True
            except (ValueError, KeyError):
                batting_changes_supported = False
            events = play['playEvents']
            if not events:
                block('MISSING_BOUNDARY_EVENT', pa); continue
            event_by_index = {event['index']: event for event in events}
            event_rows = defaultdict(list)
            for row_index, row in enumerate(rows):
                event_rows[row['details']['playIndex']].append((row_index, row))
            admitted_pairs = {int(item['runnerIndex']): item for item in runner_episode_evidence(play, str(pa))['runnerEpisodes']}
            if len(admitted_pairs) != len(rows):
                block('UNSUPPORTED_RUNNER_EPISODE', pa)
            for event_position, event in enumerate(events):
                index = event['index']; details = event.get('details', {})
                kind, event_type = event.get('type'), details.get('eventType')
                selected = event_rows[index]
                if (event.get('reviewDetails') or details.get('hasReview') is True) and index not in reviews['events']:
                    block('UNRESOLVED_REVIEW_EFFECT', pa)
                batting_only = (batting_changes_supported and event_type == 'offensive_substitution'
                    and event.get('position', {}).get('abbreviation') == 'PH'
                    and not selected and str(event.get('replacedPlayer', {}).get('id')) not in active
                    and str(event.get('player', {}).get('id')) not in active)
                prior_count = events[event_position - 1].get('count', {}) if event_position else dict(balls=0, strikes=0, outs=outs)
                delay_only = (event_type == 'game_advisory' and details.get('description') == 'On-field Delay.'
                    and kind == 'action' and event.get('isPitch') is False and not selected
                    and details.get('isScoringPlay') is False and details.get('isOut') is False
                    and details.get('hasReview') is False and not event.get('reviewDetails')
                    and not event.get('isSubstitution') and not event.get('isBaseRunningPlay')
                    and not any(details.get(k) is True for k in ('isBall', 'isStrike', 'isInPlay'))
                    and all(type(prior_count.get(k)) is int and event.get('count', {}).get(k) == prior_count[k]
                            for k in ('balls', 'strikes', 'outs')) and prior_count['outs'] == outs)
                supported = (event.get('isPitch') is True or kind in {'pickoff', 'stepoff', 'no_pitch'}
                             or event_type in neutral or event_type in independent
                             or batting_only or delay_only
                             or (event_type == 'game_advisory' and details.get('description') in advisories))
                if not supported:
                    block('UNSUPPORTED_EVENT_EFFECT:' + str(event_type or kind), pa)
                if event_type in independent and not selected:
                    block('MISSING_INDEPENDENT_MOVEMENT', pa)
                start, end = instant(event.get('startTime')), instant(event.get('endTime'))
                # Neutral administrative observations need no invented instant.
                # All pitch/movement boundary events require usable time bounds.
                if event.get('isPitch') is True or selected:
                    if (not start or not end or start > end or start < pa_start or end > pa_end
                            or (last_event_end and start < last_event_end)):
                        block('UNSUPPORTED_EVENT_TIME_ORDER', pa)
                    if end:
                        last_event_end = end
                    if event.get('count', {}).get('outs') != outs:
                        block('PRE_EVENT_OUT_COUNT_MISMATCH', pa)
                event_anchor = str(event.get('playId') or '')
                stable_anchor = bool(SAFE_IRI_SEGMENT.fullmatch(event_anchor))
                by_runner = defaultdict(list)
                for row_index, row in selected:
                    by_runner[str(row['details']['runner']['id'])].append((row_index, row))
                out_numbers = []
                for runner, pending_rows in by_runner.items():
                    batter = runner == str(play['matchup']['batter']['id'])
                    if runner not in active:
                        if not batter or sum(r['movement'].get('start') is None for _, r in pending_rows) != 1:
                            block('UNSUPPORTED_RUNNER_ENTRY', pa); continue
                        # An ordinary batter out contributes an out, not a
                        # fabricated personal baserunning lifetime.
                        if len(pending_rows) == 1 and pending_rows[0][1]['movement'].get('isOut') is True:
                            out_numbers.append(pending_rows[0][1]['movement'].get('outNumber'))
                            continue
                        if not stable_anchor:
                            block('MISSING_STABLE_MOVEMENT_ANCHOR', pa)
                        active[runner] = dict(runnerId=runner, inning=str(inning), half=half,
                            entryAnchor=event_anchor, earliestStartBound=event.get('startTime'), episodes=[], base=None)
                    item = active[runner]
                    remaining = list(pending_rows)
                    while remaining:
                        matching = [(i, row) for i, row in remaining if row['movement'].get('start') == item['base']]
                        if len(matching) != 1:
                            block('AMBIGUOUS_RUNNER_SEGMENT_CHAIN', pa); break
                        i, row = matching[0]; remaining.remove((i, row))
                        m, d = row['movement'], row['details']
                        if i not in admitted_pairs:
                            block('UNSUPPORTED_RUNNER_EPISODE', pa); break
                        item['episodes'].append(admitted_pairs[i])
                        out, end_base, score = m.get('isOut'), m.get('end'), d.get('isScoringEvent')
                        if type(out) is not bool or (score is True) != (end_base == 'score') or (out and score):
                            block('CONFLICTING_RUNNER_OUTCOME', pa); break
                        if out or score:
                            if remaining:
                                block('MOVEMENT_AFTER_TERMINATION', pa)
                            if out:
                                out_numbers.append(m.get('outNumber'))
                            if not stable_anchor:
                                block('MISSING_STABLE_MOVEMENT_ANCHOR', pa)
                            finish(item, event_anchor, 'out' if out else 'score', event.get('endTime'))
                            del active[runner]
                            break
                        if end_base not in {'1B', '2B', '3B'}:
                            block('UNKNOWN_SAFE_DESTINATION', pa); break
                        item['base'] = end_base
                if any(type(n) is not int for n in out_numbers) or sorted(out_numbers) != list(range(outs + 1, outs + len(out_numbers) + 1)):
                    block('DISTINCT_OUT_RECONCILIATION_FAILED', pa)
                outs += len(out_numbers)
                if outs > 3:
                    block('TOO_MANY_OUTS', pa)
                occupied = [item['base'] for item in active.values() if item['base'] is not None]
                if len(set(occupied)) != len(occupied):
                    block('CONFLICTING_BASE_OCCUPANCY', pa)
            if play.get('count', {}).get('outs') != outs:
                block('POST_PA_OUT_COUNT_MISMATCH', pa)
            for code, field in [('1B', 'postOnFirst'), ('2B', 'postOnSecond'), ('3B', 'postOnThird')]:
                reported = play.get('matchup', {}).get(field)
                if reported is not None and active.get(str(reported.get('id')), {}).get('base') != code:
                    block('POST_BASE_RECONCILIATION_FAILED', pa)
            if outs == 3 and play is not plays[-1]:
                block('EVENT_AFTER_HALF_END', pa)
        last_play = plays[-1]
        boundary = supported_walkoff_boundary(document, last_play) if outs != 3 else None
        if boundary:
            if not problems:
                for item in active.values():
                    finish(item, boundary['eventId'], 'game-ended', boundary['endTime'])
        else:
            if outs != 3:
                block('UNSUPPORTED_HALF_TERMINATION')
            terminal_events = [event_by_index[r['details']['playIndex']] for r in last_play['runners']
                               if r['movement'].get('isOut') is True and r['movement'].get('outNumber') == 3]
            if len(terminal_events) != 1 or not terminal_events[0].get('playId'):
                block('UNSUPPORTED_THIRD_OUT_ANCHOR')
            elif not problems:
                for item in active.values():
                    finish(item, terminal_events[0]['playId'], 'stranded', last_play['about']['endTime'])
        result['halves'].append(dict(inning=inning, half=half, status='withheld' if problems else 'reconciled',
                                    issues=problems, personalHistories=0 if problems else len(histories)))
        if boundary and not problems:
            result['halves'][-1]['gameEndingBoundary'] = boundary
        if not problems:
            result['histories'].extend({k: v for k, v in h.items() if k != 'base'} for h in histories)
            result['episodeMembership'].extend(memberships)
    return result


def runner_metric_evidence(play: dict, at_bat_index: str, season: str) -> dict[str, list[dict]]:
    """Select source rows for the user's final award/origin graph contracts.

    Start is a source designation, never persistence evidence. The force flag
    is positive evidence, not a conclusion reconstructed from occupied bases.
    Unresolved reviews and unverified rule editions withhold award assertions.
    """
    products = {"segmentOrigins": [], "awardAdvances": []}
    if not str(at_bat_index).isdigit() or isinstance(at_bat_index, bool):
        return products
    rows = play.get("runners", [])
    known = {int(r["runnerIndex"]): r for r in runner_episode_evidence(play, at_bat_index)["runnerEpisodes"]}

    def identity(row):
        d, m = row.get("details", {}), row.get("movement", {})
        return (str(d.get("runner", {}).get("id")), d.get("playIndex"),
                m.get("start"), m.get("end"), m.get("isOut"), d.get("eventType"))

    unambiguous = {i: item for i, item in known.items()
                   if sum(identity(r) == identity(rows[i]) for r in rows) == 1}
    for i, item in unambiguous.items():
        start = rows[i].get("movement", {}).get("start")
        if start in {"1B", "2B", "3B"}:
            products["segmentOrigins"].append({**item, "baseCode": start})

    result = play.get("result", {}).get("eventType")
    events = play.get("playEvents", [])
    if (str(season) not in {"2019", "2026"}
            or play.get("about", {}).get("isComplete") is not True
            or result not in {"walk", "intent_walk", "hit_by_pitch"}):
        return products
    has_review = (play.get('about', {}).get('hasReview') is True or play.get('reviewDetails')
                  or any(e.get('reviewDetails') or e.get('details', {}).get('hasReview') is True for e in events))
    if has_review and accounted_runner_count_reviews(play)['issues']:
        return products
    batter = str(play.get("matchup", {}).get("batter", {}).get("id"))
    award_types = {"walk", "intent_walk"} if result in {"walk", "intent_walk"} else {"hit_by_pitch"}
    batter_rows = [(i, r) for i, r in enumerate(rows)
                   if str(r.get("details", {}).get("runner", {}).get("id")) == batter
                   and r.get("details", {}).get("eventType") in award_types]
    if len(batter_rows) != 1:
        return products
    bi, br = batter_rows[0]
    bd, bm = br.get("details", {}), br.get("movement", {})
    index = bd.get("playIndex")
    matches = [e for e in events if type(e.get("index")) is int and e["index"] == index]
    if (type(index) is not int or index < 0 or len(matches) != 1
            or bi not in unambiguous or bm.get("start") is not None
            or bm.get("isOut") is not False or bm.get("end") != "1B"
            or bd.get("movementReason") is not None
            or str(play.get("matchup", {}).get("postOnFirst", {}).get("id")) != batter):
        return products
    event = matches[0]
    pitches = [e for e in events if e.get("isPitch") is True]
    if result == "intent_walk":
        if event.get("details", {}).get("eventType") != "intent_walk":
            return products
    elif (not pitches or pitches[-1].get("index") != index
          or (result == "walk" and event.get("count", {}).get("balls") != 4)
          or (result == "hit_by_pitch" and event.get("details", {}).get("call", {}).get("code") != "H")):
        return products
    event_rows = [(i, r) for i, r in enumerate(rows)
                  if type(r.get("details", {}).get("playIndex")) is int and r["details"]["playIndex"] == index]
    edition = f"https://baseballontology.org/data/rule/official-baseball/{season}"
    for i, row in event_rows:
        if i not in unambiguous:
            continue
        d, m = row.get("details", {}), row.get("movement", {})
        runner = str(d.get("runner", {}).get("id"))
        if (d.get("eventType") not in award_types or m.get("isOut") is not False
                or sum(str(r.get("details", {}).get("runner", {}).get("id")) == runner for _, r in event_rows) != 1):
            continue
        if i == bi:
            code = "5.05(b)(2)" if result == "hit_by_pitch" else "5.05(b)(1)"
            rule_key = "batter-hbp" if result == "hit_by_pitch" else "batter-walk"
        else:
            expected = {"1B": "2B", "2B": "3B", "3B": "score"}.get(m.get("start"))
            if d.get("movementReason") != "r_adv_force" or expected is None or m.get("end") != expected:
                continue
            if expected == "score":
                if d.get("isScoringEvent") is not True:
                    continue
            elif str(play.get("matchup", {}).get({"2B": "postOnSecond", "3B": "postOnThird"}[expected], {}).get("id")) != runner:
                continue
            code, rule_key = "5.06(b)(3)(B)", "forced-advance"
        products["awardAdvances"].append({**unambiguous[i], "ruleIri": edition + "/" + rule_key,
            "ruleCode": code, "ruleEditionIri": edition,
            "ruleIdentifierIri": edition + "/" + rule_key + "/identifier",
            "ruleEditionIdentifierIri": edition + "/identifier",
            "ruleEditionIdentifier": f"Official Baseball Rules {season}"})
    return products


def require_numeric(value: object, label: str) -> str:
    rendered = str(value if value is not None else "")
    if not rendered.isdigit():
        raise ValueError(f"{label} must be a numeric identifier, got {value!r}")
    return rendered


def require_segment(value: object, label: str) -> str:
    rendered = str(value if value is not None else "")
    if not SAFE_IRI_SEGMENT.fullmatch(rendered):
        raise ValueError(f"{label} is not a safe IRI segment: {value!r}")
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--schedule-evidence", type=Path)
    return parser.parse_args()


def schedule_postponement_context(
    path: Path | None, game_pk: str
) -> list[dict[str, object]]:
    if path is None:
        return []
    evidence = json.loads(path.read_text(encoding="utf-8-sig"))
    if evidence.get("artifactType") != "baseballo-mlb-game-schedule-evidence":
        raise ValueError("Schedule evidence has an unexpected artifactType")
    if evidence.get("contractVersion") != 1:
        raise ValueError("Schedule evidence has an unsupported contractVersion")
    if str(evidence.get("gamePk")) != game_pk:
        raise ValueError("Schedule evidence gamePk does not match the game payload")
    schedule_sha256 = str(evidence.get("scheduleSha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", schedule_sha256):
        raise ValueError("Schedule evidence lacks a valid scheduleSha256")
    records = evidence.get("postponements")
    if not isinstance(records, list) or not records:
        raise ValueError("Schedule evidence has no postponement records")

    context: list[dict[str, object]] = []
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Schedule postponement {position} must be an object")
        act_key = require_segment(record.get("actKey"), f"postponement {position} actKey")
        original_key = require_segment(
            record.get("originalPlanKey"), f"postponement {position} originalPlanKey"
        )
        revised_key = require_segment(
            record.get("revisedPlanKey"), f"postponement {position} revisedPlanKey"
        )
        original_date = str(record.get("originalDate") or "")
        revised_date = str(record.get("revisedDate") or "")
        try:
            if date.fromisoformat(original_date) >= date.fromisoformat(revised_date):
                raise ValueError
        except ValueError as error:
            raise ValueError(
                f"Schedule postponement {position} must identify ordered calendar dates"
            ) from error
        game_iri = f"https://baseballontology.org/data/game/{game_pk}"
        act_iri = f"{game_iri}/schedule/postponement/{act_key}"
        original_plan_iri = f"{game_iri}/schedule-plan/{original_key}"
        revised_plan_iri = f"{game_iri}/schedule-plan/{revised_key}"
        reason = str(record.get("reason") or "")
        item: dict[str, object] = {
            "gameIri": game_iri,
            "actIri": act_iri,
            "originalPlanIri": original_plan_iri,
            "revisedPlanIri": revised_plan_iri,
            "originalDateIdentifierIri": f"{original_plan_iri}/calendar-date",
            "revisedDateIdentifierIri": f"{revised_plan_iri}/calendar-date",
            "originalDayIri": f"https://baseballontology.org/data/day/{original_date}",
            "revisedDayIri": f"https://baseballontology.org/data/day/{revised_date}",
            "originalDate": original_date,
            "revisedDate": revised_date,
            "mlbOrganizationIri": (
                "https://baseballontology.org/data/organization/major-league-baseball"
            ),
            "scheduleResponseIri": (
                "https://baseballontology.org/data/source/mlb-game/schedule/response/"
                f"sha256/{schedule_sha256}"
            ),
            "hasReason": bool(reason),
        }
        if reason:
            reason_key = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:20]
            item.update(
                {
                    "reason": reason,
                    "reasonMeasurementIri": f"{act_iri}/reason/{reason_key}",
                    "reasonReferenceSystemIri": (
                        "https://baseballontology.org/data/reference-system/"
                        "mlb-game/schedule-postponement-reasons"
                    ),
                }
            )
        context.append(item)
    return context


def unique_player_ids_by_name(document: dict[str, object]) -> dict[str, str]:
    candidates: dict[str, set[str]] = {}
    players = document.get("gameData", {}).get("players", {})
    for player in players.values():
        player_id = player.get("id")
        full_name = player.get("fullName")
        if player_id is None or not isinstance(full_name, str) or not full_name.strip():
            continue
        candidates.setdefault(full_name.strip().casefold(), set()).add(str(player_id))
    return {
        name: next(iter(player_ids))
        for name, player_ids in candidates.items()
        if len(player_ids) == 1
    }


def final_review_decision(
    review_type: str,
    play: dict[str, object],
    pitch_events: list[dict[str, object]],
) -> str | None:
    if review_type == "pitch_result":
        if not pitch_events:
            return None
        call_code = pitch_events[-1].get("details", {}).get("call", {}).get("code")
        return PITCH_DECISION_BY_CALL_CODE.get(str(call_code))

    if review_type not in OUT_SAFE_REVIEW_TYPES:
        return None

    runners = play.get("runners", [])
    if len(runners) != 1:
        return None
    is_out = runners[0].get("movement", {}).get("isOut")
    if is_out is True:
        return "out"
    if is_out is False:
        return "safe"
    return None


def reviewed_play_context(
    play: dict[str, object],
    pitch_events: list[dict[str, object]],
    player_ids_by_name: dict[str, str],
    at_bat_index: str,
) -> dict[str, object]:
    """Return only the review claims supported by one reviewed MLB play.

    MLB's pitch-result challenge wording can omit confirmed/overturned status.
    That absence does not suppress the evidenced challenge, review, or final
    decision, and it never licenses an invented original decision or outcome.
    """
    description = play.get("result", {}).get("description")
    if not isinstance(description, str):
        raise ValueError(f"Reviewed play {at_bat_index} has no description")
    review_match = REVIEW_DESCRIPTION.search(description)
    if review_match is None:
        raise ValueError(
            f"Reviewed play {at_bat_index} has an unrecognized review description"
        )

    review_type = require_segment(
        re.sub(
            r"[^a-z0-9]+",
            "_",
            review_match.group("review_type").lower(),
        ).strip("_"),
        f"Play {at_bat_index} review type",
    )
    review_initiation = (
        "challenge"
        if review_match.group("action").lower() == "challenged"
        else "umpire_review"
    )
    context: dict[str, object] = {
        "hasReview": True,
        "hasReviewStatus": False,
        "hasReviewChallengerId": False,
        "reviewType": review_type,
        "reviewInitiation": review_initiation,
    }

    status_text = review_match.group("status")
    review_status = (
        REVIEW_STATUS_BY_NARRATIVE[status_text.lower()]
        if status_text is not None
        else None
    )
    # A plate appearance can contain more than one review. The play-level
    # reviewDetails describes the review summarized by the play-level result
    # narrative; a reviewed pitch earlier in the same plate appearance can be
    # a separate review with a different outcome. Prefer the matching
    # play-level evidence and consult pitch-level evidence only when it is
    # absent, so distinct review acts are never conflated.
    play_review_details = play.get("reviewDetails")
    if (
        isinstance(play_review_details, dict)
        and isinstance(play_review_details.get("isOverturned"), bool)
    ):
        structured_overturns = {play_review_details["isOverturned"]}
    elif review_type == "pitch_result":
        # A pitch-result narrative refers to the terminal pitch. Earlier
        # explicit pitch reviews are distinct M2 events, not votes on its result.
        terminal_details = pitch_events[-1].get("reviewDetails", {}) if pitch_events else {}
        structured_overturns = ({terminal_details["isOverturned"]}
                               if isinstance(terminal_details, dict)
                               and type(terminal_details.get("isOverturned")) is bool else set())
    else:
        structured_overturns = {
            event.get("reviewDetails", {}).get("isOverturned")
            for event in pitch_events
            if isinstance(event.get("reviewDetails"), dict)
            and isinstance(event.get("reviewDetails", {}).get("isOverturned"), bool)
        }
    if len(structured_overturns) > 1:
        raise ValueError(
            f"Reviewed play {at_bat_index} has conflicting structured review outcomes"
        )
    if structured_overturns:
        structured_status = "overturned" if next(iter(structured_overturns)) else "confirmed"
        if review_status is not None and review_status != structured_status:
            raise ValueError(
                f"Reviewed play {at_bat_index} has conflicting narrative and structured review outcomes"
            )
        review_status = structured_status

    if review_status is not None:
        context.update(
            {
                "hasReviewStatus": True,
                "reviewStatus": review_status,
                "reviewOutcome": (
                    "overturning" if review_status == "overturned" else "affirming"
                ),
            }
        )

    if review_initiation == "challenge":
        challenger_name = review_match.group("initiator").strip()
        challenger_id = player_ids_by_name.get(challenger_name.casefold())
        if challenger_id is not None:
            context["hasReviewChallengerId"] = True
            context["reviewChallengerId"] = require_numeric(
                challenger_id,
                f"Play {at_bat_index} review challenger id",
            )

    final_decision = final_review_decision(review_type, play, pitch_events)
    if final_decision is not None:
        context["reviewFinalDecision"] = final_decision
    if review_status == "overturned":
        context["hasUnresolvedOriginalDecision"] = True
    elif review_status is not None and final_decision is not None:
        context.update(
            {
                "reviewOriginalDecision": final_decision,
                "reviewPattern": f"{final_decision}_to_{final_decision}",
            }
        )
    return context


def play_has_plate_appearance_structure(play: dict[str, object]) -> bool:
    """Whether a provider play contains evidence of a plate appearance.

    A pure administrative advisory is not a plate appearance. An advisory can,
    however, be appended to an incomplete plate appearance that already
    contains a real pitch or runner event; those baseball processes retain
    their plate-appearance context even though no completed result is mapped.
    """
    about = play.get("about", {})
    matchup = play.get("matchup", {})
    play_events = play.get("playEvents", [])
    runners = play.get("runners", [])
    result_event_type = play.get("result", {}).get("eventType")
    has_baseball_event = bool(
        runners or any(event.get("isPitch") is True for event in play_events)
    )
    return bool(
        isinstance(about.get("atBatIndex"), int)
        and matchup.get("batter", {}).get("id") is not None
        and matchup.get("pitcher", {}).get("id") is not None
        and (play_events or runners)
        and (
            result_event_type not in ADMINISTRATIVE_EVENT_TYPES
            or has_baseball_event
        )
    )


def annotate_officials(document: dict[str, object]) -> int:
    """Add mapping guards without fabricating absent official names."""
    officials = (
        document.get("liveData", {}).get("boxscore", {}).get("officials", [])
    )
    for position, assignment in enumerate(officials):
        if CONTEXT_KEY in assignment:
            raise ValueError(
                f"Official {position} already contains reserved key {CONTEXT_KEY!r}"
            )
        official = assignment.get("official", {})
        require_numeric(official.get("id"), f"Official {position} official.id")
        full_name = official.get("fullName")
        assignment[CONTEXT_KEY] = {
            "hasOfficialName": isinstance(full_name, str) and bool(full_name.strip())
        }
    return len(officials)


def batter_participation_context(play: dict, game_pk: str, *, source_consistent: bool) -> dict:
    """Q4 actual per-person participation; official PA credit is independent.

    Explicit PH replacement chains assign delivered pitches to their actual
    batters. No lineup replacement by itself proves earlier participation.
    Ambiguous attribution fails preparation rather than promoting false agents.
    """
    pa = require_numeric(play['about']['atBatIndex'], 'batting participation PA')
    final = require_numeric(play['matchup']['batter']['id'], 'final batter')
    base = f'https://baseballontology.org/data/game/{game_pk}/plate-appearance/{pa}'
    events = play.get('playEvents', [])
    changes = []
    for event in events:
        if event.get('details', {}).get('eventType') != 'offensive_substitution':
            continue
        position = event.get('position', {}).get('abbreviation')
        if position == 'PR':
            continue  # A pinch runner does not change the person batting.
        if position != 'PH' or event.get('isSubstitution') is not True or event.get('isPitch') is not False:
            raise ValueError(f'PA {pa}: ambiguous offensive substitution')
        changes.append(event)
    current = require_numeric(changes[0]['replacedPlayer']['id'], 'replaced batter') if changes else final
    assignments, observed, replaced = {}, [], set()

    def instant(value):
        try:
            t = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return t if t.tzinfo is not None else None
        except (AttributeError, ValueError):
            return None

    if changes:
        indexes = [e.get('index') for e in events]
        if any(type(i) is not int for i in indexes) or indexes != list(range(len(events))):
            raise ValueError(f'PA {pa}: incomplete substitution event membership')
    for event in events:
        if event in changes:
            outgoing = require_numeric(event.get('replacedPlayer', {}).get('id'), 'replaced batter')
            incoming = require_numeric(event.get('player', {}).get('id'), 'replacement batter')
            if outgoing != current or incoming == current or incoming in replaced:
                raise ValueError(f'PA {pa}: conflicting or repeated batter stint')
            if event.get('reviewDetails') or event.get('details', {}).get('hasReview') is not False:
                raise ValueError(f'PA {pa}: unresolved substitution review')
            replaced.add(current)
            current = incoming
        elif event.get('isPitch') is True or (event.get('type') == 'no_pitch' and
                (event.get('details', {}).get('isBall') is True or event.get('details', {}).get('isStrike') is True)):
            if current not in observed:
                observed.append(current)
            if event.get('isPitch') is True:
                pid = require_segment(event.get('playId'), 'assigned pitch')
                if pid in assignments:
                    raise ValueError(f'PA {pa}: duplicate assigned pitch')
                assignments[pid] = current
    if current != final:
        raise ValueError(f'PA {pa}: substitution chain disagrees with final matchup')
    if final not in observed:
        if observed:
            raise ValueError(f'PA {pa}: replacement has no supported batting participation')
        observed.append(final)  # Preserve the existing no-pitch PA pattern.
    if len(observed) > 1:
        if not source_consistent:
            raise ValueError(f'PA {pa}: substituted participation needs reconciled source membership')
        # Corroborate the side of every substitution on which actual pitches
        # occurred. These source bounds are not exact Batter Act intervals.
        for change in changes:
            start, end = instant(change.get('startTime')), instant(change.get('endTime'))
            if not start or not end or start > end:
                raise ValueError(f'PA {pa}: unsupported substitution boundary')
            for event in events:
                if not (event.get('isPitch') is True or (event.get('type') == 'no_pitch' and
                        (event.get('details', {}).get('isBall') is True or event.get('details', {}).get('isStrike') is True))):
                    continue
                a, b = instant(event.get('startTime')), instant(event.get('endTime'))
                if not a or not b or a > b or (event['index'] < change['index'] and b > start) or (event['index'] > change['index'] and a < end):
                    raise ValueError(f'PA {pa}: pitch overlaps substitution boundary')
    rows = [dict(atBatIndex=pa, playerId=person,
                 actIri=base+'/batter-act'+('/'+person if len(observed) > 1 else ''),
                 pitchIds=[pid for pid, actor in assignments.items() if actor == person])
            for person in observed]
    by_person = {row['playerId']: row for row in rows}
    return dict(participations=rows, pitches={pid: dict(batterId=person, batterActIri=by_person[person]['actIri'])
                for pid, person in assignments.items()})


def automatic_count_awards(document: dict) -> dict:
    """Select Q5's explicit count awards; never convert provider rows to pitches.

    Individual award evidence is separate from a complete ordered PA census.
    Times support conservative precedence only, not exact judgment duration.
    """
    base = 'https://baseballontology.org/'
    data = base + f"data/game/{document['gamePk']}/"
    plays = document['liveData']['plays']['allPlays']
    ids = [e.get('playId') for p in plays for e in p.get('playEvents', []) if e.get('playId')]
    source = document[CONTEXT_KEY]['runnerHistoryReconciliation']
    admitted, withheld = [], []

    def count(event):
        c = event.get('count', {})
        return (c['balls'], c['strikes']) if all(type(c.get(k)) is int and 0 <= c[k] <= n
            for k, n in [('balls', 4), ('strikes', 3), ('outs', 3)]) else None

    def instant(value):
        try:
            t = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return t if t.tzinfo is not None else None
        except (ValueError, AttributeError):
            return None

    for play in plays:
        events = play.get('playEvents', [])
        indexes = [e.get('index') for e in events]
        reviews = accounted_runner_count_reviews(play)
        bounds = [(instant(e.get('startTime')), instant(e.get('endTime'))) for e in events]
        ordered = (all(a is not None and b is not None and a <= b for a, b in bounds)
                   and all(a[1] <= b[0] for a, b in zip(bounds, bounds[1:])))
        pa = str(play['about']['atBatIndex'])
        for index, event in enumerate(events):
            details = event.get('details', {})
            code = details.get('call', {}).get('code')
            if not (code in {'VP', 'AC', 'VB'} or (event.get('isPitch') is False and
                    (details.get('isBall') is True or details.get('isStrike') is True))):
                continue
            item = dict(atBatIndex=pa, playId=event.get('playId'), eventIndex=event.get('index'))
            kind = {'VP': 'ball', 'AC': 'strike'}.get(code)
            before = count(events[index - 1]) if index else (0, 0)
            after = count(event)
            pid = event.get('playId')
            reason = None
            if source['sourceConsistency'] != 'consistent': reason = 'SOURCE_RECONCILIATION_FAILED'
            elif play['about'].get('isComplete') is not True: reason = 'INCOMPLETE_PA'
            elif any(type(i) is not int for i in indexes) or indexes != list(range(len(events))): reason = 'EVENT_MEMBERSHIP_OR_ORDER'
            elif not kind: reason = 'AUTOMATIC_AWARD_KIND_NOT_ADMITTED'
            elif event.get('isPitch') is not False or event.get('type') != 'no_pitch': reason = 'CONTRADICTORY_PITCH_FLAG'
            elif not isinstance(pid, str) or not SAFE_IRI_SEGMENT.fullmatch(pid) or ids.count(pid) != 1: reason = 'AMBIGUOUS_EVENT_ID'
            elif (details.get('violation', {}).get('type') != ('pitcher_pitch_timer' if kind == 'ball' else 'batter_pitch_timer')
                  or details.get('isBall') is not (kind == 'ball') or details.get('isStrike') is not (kind == 'strike')
                  or details.get('isInPlay') is not False): reason = 'CONFLICTING_AUTOMATIC_AWARD'
            elif (reviews['issues'] or any(r['overturned'] for r in reviews['events'].values())
                  or event.get('reviewDetails') or details.get('hasReview') is not False): reason = 'UNRESOLVED_COUNT_REVIEW'
            elif event.get('isSubstitution') is True: reason = 'CONFLICTING_SUBSTITUTION_EVENT'
            elif not ordered: reason = 'UNSUPPORTED_EVENT_TIME_ORDER'
            elif before is None or after is None: reason = 'INVALID_COUNTER'
            elif before[0] >= 4 or before[1] >= 3: reason = 'COUNTER_RESET_AFTER_TERMINATION'
            elif after != (before[0] + (kind == 'ball'), before[1] + (kind == 'strike')): reason = 'UNEXPLAINED_COUNTER_TRANSITION'
            if reason:
                withheld.append(dict(item, reason=reason))
                continue
            row = dict(item, kind=kind, processIri=data+f'process/{kind}/{pid}',
                judgmentIri=data+f'judgment/{kind}/{pid}', decisionIri=data+f'decision/{kind}/{pid}',
                processClassIri=base+kind.title()+'Process', judgmentClassIri=base+kind.title()+'JudgmentAct',
                decisionClassIri=base+kind.title()+'DecisionICE', ruleIri=base+'data/rule/'+kind,
                ruleClassIri=base+kind.title()+'Rule',
                plateAppearanceIri=data+'plate-appearance/'+pa,
                recordIri=data+'event-record/count-award/'+pid,
                recordIdentifierIri=data+'event-record/count-award/'+pid+'/identifier/mlb-play-id',
                description=details.get('description', ''),
                ballsBefore=before[0], strikesBefore=before[1], ballsAfter=after[0], strikesAfter=after[1])
            for name, neighbors in [('previousPitchIri', reversed(events[:index])), ('nextPitchIri', events[index+1:])]:
                neighbor = next((e for e in neighbors if e.get('isPitch') is True), None)
                if neighbor and isinstance(neighbor.get('playId'), str) and SAFE_IRI_SEGMENT.fullmatch(neighbor['playId']) and ids.count(neighbor['playId']) == 1:
                    row[name] = data+'pitch/'+neighbor['playId']
            admitted.append(row)
    document[CONTEXT_KEY]['metricAutomaticAwards'] = admitted
    return dict(automaticAwards=admitted, withheldAutomaticAwards=withheld,
                automaticAwardDecision='archive/design-records/automatic-count-awards/review.json')


def metric_pitch_context(document: dict) -> dict:
    """Accepted M1/M2 source selection; graph semantics belong to RML/SHACL.

    Inspect unfiltered event prefixes. Counters are mapping evidence, not new
    RDF count states. The retained inventory also checks exact serialization.
    """
    game = str(document['gamePk'])
    data = f'https://baseballontology.org/data/game/{game}/'
    base = 'https://baseballontology.org/'
    evidence = dict(decision='archive/design-records/mlb-game-metric-mapping-completion/review.json',
                    countedFouls=[], withheldFouls=[], pitchReviews=[], withheldReviews=[])
    root = document[CONTEXT_KEY]
    evidence.update(automatic_count_awards(document))
    automatic_ids = {(r['atBatIndex'], r['playId']) for r in evidence['automaticAwards']}
    source = root['runnerHistoryReconciliation']
    evidence.update(inputSha256=source['inputSha256'], sourceRevision=source['sourceRevision'])
    rows = []

    def instant(value):
        try:
            t = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return t if t.tzinfo is not None else None
        except (ValueError, AttributeError):
            return None

    def counts(event):
        c = event.get('count', {})
        if all(type(c.get(k)) is int and 0 <= c[k] <= n
               for k, n in [('balls', 4), ('strikes', 3), ('outs', 3)]):
            return c['balls'], c['strikes']
        return None

    plays = document['liveData']['plays']['allPlays']
    all_ids = [e.get('playId') for p in plays for e in p.get('playEvents', []) if e.get('isPitch') is True]
    for play in plays:
        pa = str(play['about']['atBatIndex'])
        events = play.get('playEvents', [])
        pitches = [e for e in events if e.get('isPitch') is True]
        pc = play[CONTEXT_KEY]
        indexes = [e.get('index') for e in events]
        prefix_problem = None
        if source['sourceConsistency'] != 'consistent':
            prefix_problem = 'SOURCE_RECONCILIATION_FAILED'
        elif play['about'].get('isComplete') is not True:
            prefix_problem = 'INCOMPLETE_PA'
        elif any(type(i) is not int for i in indexes) or indexes != list(range(len(events))):
            prefix_problem = 'EVENT_MEMBERSHIP_OR_ORDER'
        elif play.get('reviewDetails') or play['about'].get('hasReview') is not False:
            prefix_problem = 'UNRESOLVED_PA_REVIEW'
        previous = None
        prior = (0, 0)
        has_batting_substitution = any(e.get('details', {}).get('eventType') == 'offensive_substitution' for e in events)
        for event in events:
            details = event.get('details', {})
            code = details.get('call', {}).get('code')
            after = counts(event)
            start, end = instant(event.get('startTime')), instant(event.get('endTime'))
            if not start or not end or end < start or (previous and (not instant(previous.get('endTime')) or instant(previous['endTime']) > start)):
                prefix_problem = prefix_problem or 'UNSUPPORTED_EVENT_TIME_ORDER'
            if event.get('reviewDetails') or details.get('hasReview') is True:
                prefix_problem = prefix_problem or 'UNRESOLVED_PREFIX_REVIEW'
            if event.get('isSubstitution') is True or 'substitution' in str(details.get('eventType', '')):
                prefix_problem = prefix_problem or 'SUBSTITUTION_IN_PREFIX'
            if after is None:
                prefix_problem = prefix_problem or 'INVALID_COUNTER'
            elif prior is not None:
                balls, strikes = prior
                if balls >= 4 or strikes >= 3:
                    prefix_problem = prefix_problem or 'COUNTER_RESET_AFTER_TERMINATION'
                if event.get('isPitch') is True:
                    if code in {'B', '*B'}: expected = (balls + 1, strikes)
                    elif code in {'C', 'S', 'W', 'M', 'T', 'O', 'L'}: expected = (balls, strikes + 1)
                    elif code == 'F': expected = (balls, min(2, strikes + 1))
                    elif code in {'X', 'D', 'E', 'H'}: expected = prior
                    else: expected = None
                else:
                    neutral = details.get('eventType') in {'batter_timeout', 'mound_visit', 'defensive_switch'} or event.get('type') in {'pickoff', 'stepoff', 'no_pitch'}
                    if (pa, event.get('playId')) in automatic_ids:
                        expected = (balls + (code == 'VP'), strikes + (code == 'AC'))
                    else:
                        expected = prior if neutral else None
                if expected is None or expected != after:
                    prefix_problem = prefix_problem or 'UNEXPLAINED_COUNTER_TRANSITION'
            if event.get('isPitch') is not True:
                previous, prior = event, after
                continue
            pid = event.get('playId')
            ec = event[CONTEXT_KEY]
            unique_id = isinstance(pid, str) and SAFE_IRI_SEGMENT.fullmatch(pid) and all_ids.count(pid) == 1
            if not unique_id:
                prefix_problem = prefix_problem or 'AMBIGUOUS_PITCH_ID'
            for kind in ('ball', 'strike'):
                ec[f'{kind}JudgmentIri'] = data + f'judgment/{kind}/{pid}'
                ec[f'{kind}DecisionIri'] = data + f'decision/{kind}/{pid}'
                ec[f'{kind}OnFieldJudgmentIri'] = ec[f'{kind}JudgmentIri']
            ec['isSecondCountedFoul'] = False
            if code == 'F' and after and after[1] == 2:
                item = dict(atBatIndex=pa, playId=pid, eventIndex=event.get('index'))
                if prefix_problem is None and previous is not None and prior == (after[0], 1) and ec['isBuntAttempt'] is False:
                    ec['isSecondCountedFoul'] = True
                    evidence['countedFouls'].append(item)
                else:
                    evidence['withheldFouls'].append(dict(item, reason=prefix_problem or 'NO_SECOND_STRIKE_INCREMENT'))

            review = event.get('reviewDetails')
            if review is not None:
                item = dict(atBatIndex=pa, playId=pid, eventIndex=event.get('index'))
                kind = PITCH_DECISION_BY_CALL_CODE.get(code)
                reason = None
                if not unique_id: reason = 'AMBIGUOUS_PITCH_ID'
                elif not isinstance(review, dict) or review.get('inProgress') is not False or review.get('isOverturned') is not False:
                    reason = 'NOT_EXPLICIT_COMPLETED_AFFIRMATION'
                elif not kind or details.get('isBall') is not (kind == 'ball') or details.get('isStrike') is not (kind == 'strike') or details.get('hasReview') is False:
                    reason = 'CONFLICTING_OR_UNSUPPORTED_CALL'
                legacy = pc.get('reviewType') == 'pitch_result' and bool(pitches) and event is pitches[-1]
                if legacy and (pc.get('reviewOutcome') != 'affirming' or pc.get('reviewFinalDecision') != kind or pc.get('reviewOriginalDecision') != kind):
                    reason = 'CONFLICTING_PA_REVIEW'
                if reason:
                    evidence['withheldReviews'].append(dict(item, reason=reason))
                    if legacy:
                        # The same explicit contradictory/incomplete review
                        # cannot survive through the older PA-narrative route.
                        for context in (pc, ec):
                            for key in list(context):
                                if key.startswith('review') or key.startswith('hasReview') or key == 'hasUnresolvedOriginalDecision':
                                    context.pop(key)
                            context.update(hasReview=False, hasReviewStatus=False, hasReviewChallengerId=False)
                else:
                    review_root = data + (f'review/{pa}/' if legacy else f'review/pitch/{pid}/')
                    if legacy:
                        ec[f'{kind}JudgmentIri'] = review_root + 'act'
                        ec[f'{kind}DecisionIri'] = review_root + 'decision/replay'
                    ec[f'{kind}OnFieldJudgmentIri'] = review_root + 'judgment/on-field'
                    row = dict(item, reviewIri=ec[f'{kind}JudgmentIri'],
                               operativeDecisionIri=ec[f'{kind}DecisionIri'],
                               originalJudgmentIri=review_root+'judgment/on-field',
                               originalDecisionIri=review_root+'decision/on-field',
                               originalProcessIri=review_root+'process/on-field',
                               dispositionIri=review_root+'result',
                               recordIri=data+(f'event-record/review/{pa}' if legacy else f'event-record/review/pitch/{pid}'),
                               pitchIri=data+f'pitch/{pid}', motionIri=data+f'process/pitch-ball-motion/{pid}',
                               processIri=data+f'process/{kind}/{pid}',
                               judgmentClassIri=base+kind.title()+'JudgmentAct',
                               decisionClassIri=base+kind.title()+'DecisionICE',
                               reviewClassIri=base+kind.title()+'AffirmingBaseballReplayReviewAct',
                               ruleIri='https://baseballontology.org/data/rule/'+kind,
                               affectedBatterSupported=not has_batting_substitution,
                               reusesPlayReview=legacy)
                    rows.append(row)
                    evidence['pitchReviews'].append(row.copy())
            previous, prior = event, after
    root['metricPitchReviews'] = rows
    root['metricMappingEvidence'] = evidence
    return evidence


def main() -> None:
    args = parse_args()
    document = json.loads(args.source.read_text(encoding="utf-8"))
    if CONTEXT_KEY in document:
        raise ValueError(f"Source root already contains reserved key {CONTEXT_KEY!r}")

    plays = document.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if not plays:
        raise ValueError("Source has no liveData.plays.allPlays records")

    status = document.get("gameData", {}).get("status", {})
    metadata = document.get("metaData", {})
    final_corroborated = (
        status.get("abstractGameState") == "Final"
        or status.get("codedGameState") == "F"
        or "game_finished" in metadata.get("gameEvents", [])
        or any(
            item in {"gameStateChangeToFinal", "gameStateChangeToGameOver"}
            for item in metadata.get("logicalEvents", [])
        )
    )
    if not final_corroborated:
        raise ValueError("Game end is not corroborated by final/game-over source state")
    terminal_baseball_plays = [
        play
        for play in plays
        if play.get("result", {}).get("eventType") not in ADMINISTRATIVE_EVENT_TYPES
        and (
            play.get("playEvents")
            or play.get("runners")
            or play.get("about", {}).get("isComplete") is True
        )
        and isinstance(play.get("about", {}).get("endTime"), str)
    ]
    if not terminal_baseball_plays:
        raise ValueError("Final game has no terminal baseball event with an endTime")
    final_end_time = terminal_baseball_plays[-1].get("about", {}).get("endTime")
    if not isinstance(final_end_time, str) or not final_end_time.strip():
        raise ValueError("Final play has no about.endTime")
    game_pk = require_numeric(document.get("gamePk"), "Root gamePk")
    game_data = document.get("gameData", {})
    game_description = game_data.get("game", {})
    season = require_numeric(game_description.get("season"), "gameData.game.season")
    provider_version = require_segment(
        metadata.get("timeStamp"), "metaData.timeStamp"
    )
    provider_reference_root = (
        "https://baseballontology.org/data/reference-system/mlb-game/"
        f"{provider_version}"
    )
    root_context: dict[str, object] = {
        "runnerHistoryReconciliation": personal_runner_histories(args.source.read_bytes()),
        "gameEndTime": final_end_time,
        "pitchTypeReferenceSystemIri": f"{provider_reference_root}/pitch-types",
        "pitchTypeReferenceSystemLabel": (
            f"MLB pitch-type reference system observed {provider_version}"
        ),
        "battedTrajectoryReferenceSystemIri": (
            f"{provider_reference_root}/batted-ball-trajectories"
        ),
        "battedTrajectoryReferenceSystemLabel": (
            f"MLB batted-ball trajectory reference system observed {provider_version}"
        ),
    }
    postponement_context = schedule_postponement_context(
        args.schedule_evidence, game_pk
    )
    if postponement_context:
        root_context["schedulePostponements"] = postponement_context
    game_type = str(game_description.get("type") or "")
    phase_definition = SEASON_PHASE_BY_GAME_TYPE.get(game_type)
    if phase_definition is not None:
        phase_key, phase_class, category = phase_definition
        root_context["seasonPhase"] = {
            "iri": f"https://baseballontology.org/data/season/{season}/phase/{phase_key}",
            "classIri": f"https://baseballontology.org/{phase_class}",
            "categoryIri": f"https://baseballontology.org/{category}",
            "referenceSystemIri": f"{provider_reference_root}/season-segments",
            "referenceSystemLabel": (
                f"MLB season-segment reference system observed {provider_version}"
            ),
            "seasonIri": f"https://baseballontology.org/data/season/{season}",
            "gameIri": f"https://baseballontology.org/data/game/{game_pk}",
            "gameTypeCode": game_type,
        }
    document[CONTEXT_KEY] = root_context
    player_ids_by_name = unique_player_ids_by_name(document)
    official_count = annotate_officials(document)

    roster_player_count = 0
    boxscore_teams = (
        document.get("liveData", {}).get("boxscore", {}).get("teams", {})
    )
    for side in ("away", "home"):
        team_boxscore = boxscore_teams.get(side, {})
        team_id = require_numeric(
            team_boxscore.get("team", {}).get("id"),
            f"Boxscore {side} team.id",
        )
        for roster_key, roster_player in team_boxscore.get("players", {}).items():
            if CONTEXT_KEY in roster_player:
                raise ValueError(
                    f"Roster player {roster_key} already contains reserved key {CONTEXT_KEY!r}"
                )
            require_numeric(
                roster_player.get("person", {}).get("id"),
                f"Boxscore {side} roster player {roster_key} person.id",
            )
            roster_player[CONTEXT_KEY] = {"teamId": team_id}
            roster_player_count += 1

    pitch_count = 0
    runner_count = 0
    terminal_pitch_count = 0
    review_count = 0
    institutional_pitch_classification_count = 0
    uncaught_third_strike_count = 0
    occupied_base_count = 0
    seen_pitch_ids: set[str] = set()
    current_half_inning: tuple[str, str] | None = None
    outs_after_previous_play = 0
    runners_after_previous_play: dict[str, str] = {}
    for play_position, play in enumerate(plays):
        if CONTEXT_KEY in play:
            raise ValueError(
                f"Play {play_position} already contains reserved key {CONTEXT_KEY!r}"
            )
        about = play.get("about", {})
        matchup = play.get("matchup", {})
        result_event_type = play.get("result", {}).get("eventType")
        play_events = play.get("playEvents", [])
        pitch_events = [
            event for event in play_events if event.get("isPitch") is True
        ]
        runners = play.get("runners", [])
        has_plate_appearance_structure = play_has_plate_appearance_structure(play)
        has_completed_plate_appearance_result = bool(
            has_plate_appearance_structure
            and about.get("isComplete") is True
            and isinstance(result_event_type, str)
            and result_event_type not in ADMINISTRATIVE_EVENT_TYPES
        )
        at_bat_index = require_numeric(
            about.get("atBatIndex"), f"Play {play_position} about.atBatIndex"
        )
        batter_id = require_numeric(
            matchup.get("batter", {}).get("id"),
            f"Play {at_bat_index} matchup.batter.id",
        )
        pitcher_id = require_numeric(
            matchup.get("pitcher", {}).get("id"),
            f"Play {at_bat_index} matchup.pitcher.id",
        )

        half_inning = (
            require_numeric(about.get("inning"), f"Play {at_bat_index} about.inning"),
            require_segment(
                str(about.get("halfInning", "")).lower(),
                f"Play {at_bat_index} about.halfInning",
            ),
        )
        if half_inning != current_half_inning:
            current_half_inning = half_inning
            outs_after_previous_play = 0
            runners_after_previous_play = {}
            for event in play.get("playEvents", []):
                if event.get("details", {}).get("eventType") != "runner_placed":
                    continue
                base_number = require_numeric(
                    event.get("base"),
                    f"Play {at_bat_index} runner_placed base",
                )
                if base_number not in {"1", "2", "3"}:
                    raise ValueError(
                        f"Play {at_bat_index} runner_placed has unsupported base {base_number}"
                    )
                runner_id = require_numeric(
                    event.get("player", {}).get("id"),
                    f"Play {at_bat_index} runner_placed player.id",
                )
                if base_number in runners_after_previous_play:
                    raise ValueError(
                        f"Play {at_bat_index} places multiple runners on base {base_number}"
                    )
                runners_after_previous_play[base_number] = runner_id

        start_base_occupancies = [
            {
                "atBatIndex": at_bat_index,
                "runnerId": runner_id,
                "baseNumber": base_number,
                "baseCode": f"{base_number}B",
                "baseLabel": {"1": "First base", "2": "Second base", "3": "Third base"}[base_number],
                "baseSiteLabel": {"1": "First base site", "2": "Second base site", "3": "Third base site"}[base_number],
            }
            for base_number, runner_id in sorted(runners_after_previous_play.items())
        ]

        play_context: dict[str, object] = {
            "outsBefore": outs_after_previous_play,
            "startBaseOccupancies": start_base_occupancies,
            "battedRunnerResolutions": batted_runner_resolution_links(play, at_bat_index, root_context['runnerHistoryReconciliation']),
            **runner_episode_evidence(play, at_bat_index),
            **runner_metric_evidence(play, at_bat_index, season),
            "hasPlateAppearanceStructure": has_plate_appearance_structure,
            "hasCompletedPlateAppearanceResult": has_completed_plate_appearance_result,
            "hasReview": False,
            "hasReviewStatus": False,
            "hasReviewChallengerId": False,
        }
        batting_context = batter_participation_context(play, game_pk,
            source_consistent=root_context['runnerHistoryReconciliation']['sourceConsistency'] == 'consistent')
        play_context['batterParticipations'] = batting_context['participations'] if has_plate_appearance_structure else []
        occupied_base_count += len(start_base_occupancies)
        review_type: str | None = None
        review_context: dict[str, object] = {}
        if about.get("hasReview") is True:
            review_context = reviewed_play_context(
                play, pitch_events, player_ids_by_name, at_bat_index
            )
            review_type = str(review_context["reviewType"])
            play_context.update(review_context)
            review_count += 1

        events_by_index = {
            event.get("index", event_position): event
            for event_position, event in enumerate(play_events)
        }
        classification_event_ids_by_runner: dict[int, str] = {}
        classification_event_ids: set[str] = set()
        for runner_position, runner in enumerate(runners):
            event_type = runner.get("details", {}).get("eventType")
            if event_type not in {"passed_ball", "wild_pitch"}:
                continue
            play_index = runner.get("details", {}).get("playIndex")
            event = events_by_index.get(play_index)
            if event is None:
                raise ValueError(
                    f"Play {at_bat_index} {event_type} runner row references missing "
                    f"play event index {play_index!r}"
                )
            source_pitch_event = event
            if event.get("isPitch") is not True or not event.get("playId"):
                preceding_pitch_events = [
                    candidate
                    for candidate in play_events
                    if candidate.get("isPitch") is True
                    and candidate.get("playId")
                    and candidate.get("index", -1) <= play_index
                ]
                if not preceding_pitch_events:
                    raise ValueError(
                        f"Play {at_bat_index} {event_type} event at index "
                        f"{play_index!r} has no preceding source pitch"
                    )
                source_pitch_event = preceding_pitch_events[-1]
            event_play_id = require_segment(
                source_pitch_event.get("playId"),
                f"Play {at_bat_index} {event_type} event playId",
            )
            classification_event_ids_by_runner[runner_position] = event_play_id
            classification_event_ids.add(event_play_id)

        has_null_strikeout_placeholder = any(
            runner.get("details", {}).get("eventType") == "strikeout"
            and runner.get("details", {}).get("runner", {}).get("id")
            == matchup.get("batter", {}).get("id")
            and runner.get("movement", {}).get("isOut") is None
            for runner in runners
        )
        safe_batter_classifications = {
            runner.get("details", {}).get("eventType")
            for runner in runners
            if runner.get("details", {}).get("runner", {}).get("id")
            == matchup.get("batter", {}).get("id")
            and runner.get("movement", {}).get("isOut") is False
            and runner.get("movement", {}).get("end") == "1B"
            and runner.get("details", {}).get("eventType")
            in {"passed_ball", "wild_pitch"}
        }
        uncaught_classification = next(iter(safe_batter_classifications), None)
        is_uncaught_third_strike = (
            play.get("result", {}).get("eventType") == "strikeout"
            and has_null_strikeout_placeholder
            and len(safe_batter_classifications) == 1
        )
        uncaught_event_id = next(
            (
                classification_event_ids_by_runner[runner_position]
                for runner_position, runner in enumerate(runners)
                if runner.get("details", {}).get("runner", {}).get("id")
                == matchup.get("batter", {}).get("id")
                and runner.get("movement", {}).get("isOut") is False
                and runner.get("movement", {}).get("end") == "1B"
                and runner.get("details", {}).get("eventType")
                == uncaught_classification
            ),
            None,
        )

        for runner_position, runner in enumerate(runners):
            if CONTEXT_KEY in runner:
                raise ValueError(
                    f"Runner {runner_position} in play {at_bat_index} already contains "
                    f"reserved key {CONTEXT_KEY!r}"
                )
            require_numeric(
                runner.get("details", {}).get("runner", {}).get("id"),
                f"Runner {runner_position} in play {at_bat_index} details.runner.id",
            )
            movement = runner.get("movement", {})
            event_type = runner.get("details", {}).get("eventType")
            runner_context: dict[str, object] = {
                "atBatIndex": at_bat_index,
                "runnerIndex": str(runner_position),
                "hasRunnerResolution": isinstance(movement.get("isOut"), bool),
                "hasSupportedStartBase": movement.get("start") in {"1B", "2B", "3B"},
                "endsAtScore": movement.get("end") == "score",
            }
            if runner_position in classification_event_ids_by_runner:
                runner_context["eventPlayId"] = classification_event_ids_by_runner[
                    runner_position
                ]
            if (
                is_uncaught_third_strike
                and event_type == "strikeout"
                and movement.get("isOut") is None
            ):
                runner_context["isUncaughtThirdStrikePlaceholder"] = True
                runner_context["eventPlayId"] = uncaught_event_id
            runner[CONTEXT_KEY] = runner_context
            runner_count += 1

        if pitch_events:
            terminal_pitch = pitch_events[-1]
            terminal_pitch_id = require_segment(
                terminal_pitch.get("playId"),
                f"Play {at_bat_index} terminal pitch playId",
            )
            play_context["terminalPitchPlayId"] = terminal_pitch_id
            play_context["terminalPitchIsInPlay"] = (
                terminal_pitch.get("details", {}).get("isInPlay") is True
                and terminal_pitch.get("details", {}).get("call", {}).get("code")
                in {"X", "D", "E"}
            )
            terminal_pitch_count += 1

        institutional_pitch_classification_count += len(classification_event_ids)

        if is_uncaught_third_strike:
            if not pitch_events:
                raise ValueError(
                    f"Uncaught third strike play {at_bat_index} has no pitch event"
                )
            if uncaught_event_id is None:
                raise ValueError(
                    f"Uncaught third strike play {at_bat_index} has no classified source pitch"
                )
            terminal_event_id = require_segment(
                pitch_events[-1].get("playId"),
                f"Uncaught third strike play {at_bat_index} terminal pitch playId",
            )
            if uncaught_event_id != terminal_event_id:
                raise ValueError(
                    f"Uncaught third strike play {at_bat_index} classification event "
                    f"{uncaught_event_id} does not match terminal pitch {terminal_event_id}"
                )
            play_context.update(
                {
                    "isUncaughtThirdStrike": True,
                    "uncaughtThirdStrikeEventType": uncaught_classification,
                    "uncaughtThirdStrikePlayId": uncaught_event_id,
                }
            )
            uncaught_third_strike_count += 1

        play[CONTEXT_KEY] = play_context

        ending_outs = play.get("count", {}).get("outs")
        if not isinstance(ending_outs, int) or ending_outs < outs_after_previous_play or ending_outs > 3:
            raise ValueError(
                f"Play {at_bat_index} has invalid ending out count {ending_outs!r} "
                f"after {outs_after_previous_play} outs"
            )
        outs_after_previous_play = ending_outs
        runners_after_previous_play = {}
        for base_number, source_key in (("1", "postOnFirst"), ("2", "postOnSecond"), ("3", "postOnThird")):
            runner = matchup.get(source_key)
            if runner is None:
                continue
            runner_id = require_numeric(
                runner.get("id") if isinstance(runner, dict) else None,
                f"Play {at_bat_index} matchup.{source_key}.id",
            )
            if runner_id in runners_after_previous_play.values():
                raise ValueError(f"Play {at_bat_index} places runner {runner_id} on multiple bases")
            runners_after_previous_play[base_number] = runner_id

        for event_position, event in enumerate(pitch_events):
            if CONTEXT_KEY in event:
                raise ValueError(
                    f"Pitch {event_position} in play {at_bat_index} already contains "
                    f"reserved key {CONTEXT_KEY!r}"
                )
            play_id = require_segment(
                event.get("playId"),
                f"Pitch {event_position} in play {at_bat_index} playId",
            )
            if play_id in seen_pitch_ids:
                raise ValueError(f"Duplicate pitch playId in context source: {play_id}")
            seen_pitch_ids.add(play_id)
            trajectory = event.get("hitData", {}).get("trajectory")
            is_bunt_attempt = (
                event.get("details", {}).get("call", {}).get("code") in BUNT_CALL_CODES
                or trajectory in BUNT_TRAJECTORIES
            )
            event_context: dict[str, object] = {
                "atBatIndex": at_bat_index,
                **batting_context['pitches'][play_id],
                "pitcherId": pitcher_id,
                "isBuntAttempt": is_bunt_attempt,
                "matchesBuntContactSource": (
                    is_bunt_attempt
                    and event.get("details", {}).get("call", {}).get("code") != "M"
                ),
                "hasPitchTypeCategory": False,
                "hasBattedTrajectoryCategory": False,
            }
            pitch_type_code = str(
                event.get("details", {}).get("type", {}).get("code") or ""
            )
            pitch_type_category = PITCH_TYPE_CATEGORY_BY_CODE.get(pitch_type_code)
            if pitch_type_category is not None:
                event_context.update(
                    {
                        "hasPitchTypeCategory": True,
                        "pitchTypeCategoryIri": (
                            f"https://baseballontology.org/{pitch_type_category}"
                        ),
                        "pitchTypeReferenceSystemIri": root_context[
                            "pitchTypeReferenceSystemIri"
                        ],
                    }
                )
            trajectory_category = BATTED_TRAJECTORY_CATEGORY_BY_TOKEN.get(
                str(trajectory or "")
            )
            if trajectory_category is not None:
                event_context.update(
                    {
                        "hasBattedTrajectoryCategory": True,
                        "battedTrajectoryCategoryIri": (
                            f"https://baseballontology.org/{trajectory_category}"
                        ),
                        "battedTrajectoryReferenceSystemIri": root_context[
                            "battedTrajectoryReferenceSystemIri"
                        ],
                    }
                )
            event[CONTEXT_KEY] = event_context
            if (
                event_position == len(pitch_events) - 1
                and review_type == "pitch_result"
            ):
                event[CONTEXT_KEY].update(review_context)
            pitch_count += 1

    metric_pitch_context(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Context pitches: {pitch_count}")
    print(f"Context roster players: {roster_player_count}")
    print(f"Context officials: {official_count}")
    print(f"Context runners: {runner_count}")
    print(f"Context occupied bases at plate-appearance start: {occupied_base_count}")
    print(f"Context terminal pitches: {terminal_pitch_count}")
    print(f"Context reviewed plays: {review_count}")
    print(
        "Context passed-ball/wild-pitch classifications: "
        f"{institutional_pitch_classification_count}"
    )
    print(f"Context uncaught third strikes: {uncaught_third_strike_count}")
    print(f"Context game end: {final_end_time}")
    print(f"Context schedule postponements: {len(postponement_context)}")


if __name__ == "__main__":
    main()
