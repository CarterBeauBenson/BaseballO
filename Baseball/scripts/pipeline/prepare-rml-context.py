#!/usr/bin/env python3
"""Create an isolated ancestor-aware JSON context for RMLMapper execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import unicodedata
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
    "fielders_choice", "fielders_choice_out", "field_error",
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


def clock_pair(record: dict) -> tuple:
    """T1: select neither member of a contradictory pair; never repair clocks.

    The original source fields remain untouched. Missing/invalid individual
    values retain their prior validation behavior; T1 isolates reversed pairs.
    """
    start, end = record.get('startTime'), record.get('endTime')
    try:
        a = datetime.fromisoformat(start.replace('Z', '+00:00'))
        b = datetime.fromisoformat(end.replace('Z', '+00:00'))
        if a.tzinfo and b.tzinfo and b < a:
            return None, None
    except (ValueError, AttributeError):
        pass
    return start, end


def clock_pair_conflicted(record: dict) -> bool:
    return clock_pair(record) == (None, None) and any(record.get(k) is not None for k in ('startTime', 'endTime'))


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
    review = accounted_runner_history_reviews(play)
    if review['issues']:return False
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
        reviewed=event['index'] in review['events'] or review.get('accountedFieldReview',{}).get('eventIndex')==event['index']
        replacement=False
        if before_contact and event.get('isSubstitution') is True:
            prefix=events[:event['index']]
            neutral=(event.get('isPitch') is False and details.get('eventType')=='offensive_substitution'
                and event.get('count',{}).get('balls')==0 and event.get('count',{}).get('strikes')==0
                and not selected and not any(e.get('isPitch') is True for e in prefix)
                and not any(r.get('details',{}).get('playIndex',terminal_index)<event['index'] for r in rows))
            if neutral and event.get('position',{}).get('abbreviation')=='PH':
                try:actual=batter_participation_context(play,'1',source_consistent=True)['participations']
                except (ValueError,KeyError):actual=[]
                replacement=len(actual)==1 and actual[0]['playerId']==str(event.get('player',{}).get('id'))
            elif neutral and event.get('position',{}).get('abbreviation')=='PR':
                incoming=str(event.get('player',{}).get('id'));outgoing=str(event.get('replacedPlayer',{}).get('id'))
                def witness(h,field):
                    w=h.get(field,{})
                    return str(w.get('atBatIndex'))==at_bat_index and w.get('eventIndex')==event['index']
                begun=[h for h in histories.get('histories',[]) if h.get('runnerId')==incoming and witness(h,'entryWitness')]
                ended=[h for h in histories.get('histories',[]) if h.get('runnerId')==outgoing and witness(h,'terminationWitness')]
                replacement=(len(begun)==len(ended)==1 and begun[0].get('entryAnchor')==ended[0].get('terminationAnchor'))
        if (((event.get('reviewDetails') or details.get('hasReview') is True) and not reviewed)
                or event.get('isSubstitution') is True and not replacement
                or (event.get('isPitch') is not True and details.get('eventType') not in {'batter_timeout', 'mound_visit'}
                    and not independent and not empty_attempt and not replacement and not reviewed)):
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


def compound_double_play_parts(play: dict) -> list[dict]:
    """K1: reconcile the compound whole with two existing counted outs.

    This selects existing result/out identities, never a Strikeout constituent
    or a strategy. The explicit joined narrative and terminal event corroborate
    one continuous play; matching array indexes alone are insufficient.
    """
    about, result = play.get('about', {}), play.get('result', {})
    events, runners = play.get('playEvents', []), play.get('runners', [])
    if (result.get('eventType') != 'strikeout_double_play' or about.get('isComplete') is not True
            or not events):
        return []
    reviews=accounted_runner_count_reviews(play)
    if reviews['issues']:return []
    terminal = events[-1]
    before, after = terminal.get('count', {}).get('outs'), play.get('count', {}).get('outs')
    if (terminal.get('isPitch') is not True or terminal.get('type') != 'pitch'
            or not SAFE_IRI_SEGMENT.fullmatch(str(terminal.get('playId') or ''))
            or terminal.get('count', {}).get('strikes') != 3
            or play.get('count', {}).get('strikes') != 3
            or terminal.get('details', {}).get('isInPlay') is not False
            or terminal.get('details', {}).get('isStrike') is not True
            or type(before) is not int or before not in (0, 1) or after != before + 2
            or ((terminal.get('reviewDetails') or terminal.get('details', {}).get('hasReview') is not False)
                and terminal.get('index') not in reviews['events'])):
        return []
    outs = [(i, row) for i, row in enumerate(runners) if row.get('movement', {}).get('isOut') is True]
    batter = play.get('matchup', {}).get('batter', {})
    if len(outs) != 2 or len({r.get('details', {}).get('runner', {}).get('id') for _, r in outs}) != 2:
        return []
    if any(r.get('details', {}).get('playIndex') != terminal.get('index')
           or r.get('details', {}).get('isScoringEvent') is not False
           or r.get('movement', {}).get('end') is not None for _, r in outs):
        return []
    numbers = [r['movement'].get('outNumber') for _, r in outs]
    if any(type(n) is not int for n in numbers) or sorted(numbers) != [before + 1, before + 2]:
        return []
    batting = [r for _, r in outs if r.get('details', {}).get('runner', {}).get('id') == batter.get('id')]
    running = [r for _, r in outs if r.get('details', {}).get('runner', {}).get('id') != batter.get('id')]
    if (len(batting) != 1 or batting[0]['movement'].get('start') is not None
            or running[0]['movement'].get('start') not in {'1B', '2B', '3B'}):
        return []
    other = running[0]['details']['runner']
    names = [batter.get('fullName'), other.get('fullName')]
    if not all(isinstance(n, str) and n.strip() for n in names):
        return []
    # Bound the accepted selector to explicit K-and-caught-stealing wording.
    narrative = (re.escape(names[0]) + r' (?:strikes out (?:swinging|looking)|called out on strikes) and '
                 + re.escape(names[1]) + r' caught stealing (?:2nd|3rd|home)(?:[, .]|$)')
    description=result.get('description','')
    if reviews['events']:description=REVIEW_DESCRIPTION.sub('',description,count=1).strip()
    if not re.match(narrative, description, flags=re.I):
        return []
    if running[0]['details'].get('eventType') not in {'caught_stealing_2b', 'caught_stealing_3b', 'caught_stealing_home'}:
        return []
    return [dict(atBatIndex=str(play['atBatIndex']), runnerIndex=str(i),
                 runnerId=str(r['details']['runner']['id'])) for i, r in outs]


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
            or clock_pair_conflicted(terminal) or clock_pair_conflicted(about)
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


def linked_pitch_tag_review_tail(play, position):
    """Reconcile separate pitch/tag reviews joined by the actual pitch ID."""
    events=play.get('playEvents',[])
    if not 0 < position < len(events):return None
    event=events[position];review=event.get('reviewDetails',{})
    if review.get('additionalReviews'):return None
    linked=[e for e in events[:position] if e.get('isPitch') is True
        and e.get('playId')==event.get('actionPlayId') and e.get('reviewDetails')]
    if len(linked)!=1:return None
    pitch=linked[0];pitch_review=pitch['reviewDetails']
    if pitch_review.get('reviewType')!='MJ' or pitch_review.get('additionalReviews'):return None
    scope=dict(play,playEvents=events[:position],about=dict(play.get('about',{}),hasReview=False))
    scope.pop('reviewDetails',None)
    counted=accounted_runner_count_reviews(scope)
    if counted['issues'] or pitch['index'] not in counted['events']:return None
    description=event.get('details',{}).get('description','')
    if not completed_field_review_dispositions(dict(review,additionalReviews=[pitch_review]),description):return None
    for _ in range(2):
        match=REVIEW_DESCRIPTION.search(description)
        if match is None:return None
        description=description[match.end():].lstrip()
    return description


def unchanged_runner_tag_review(play: dict, position: int) -> dict | None:
    """E1 final movement effects only; no original decision or review RDF.

    An explicit completed affirmation of the named runner's steal/tag outcome
    leaves that final source movement operative. C1/C3 still reconcile its
    time, active runner, episode and (for an out) stable boundary separately.
    """
    events = play.get('playEvents', [])
    if position == 0 or position >= len(events)-1:
        return None
    event = events[position]; details = event.get('details', {})
    review = event.get('reviewDetails'); description = details.get('description', '')
    match = REVIEW_DESCRIPTION.search(description)
    event_type = details.get('eventType')
    linked_tail = linked_pitch_tag_review_tail(play,position)
    kinds = {'stolen_base_2b': ('1B', '2B', False, '2nd'),
             'stolen_base_3b': ('2B', '3B', False, '3rd'),
             'caught_stealing_2b': ('1B', '2B', True, '2nd'),
             'caught_stealing_3b': ('2B', '3B', True, '3rd')}
    if (play.get('about', {}).get('isComplete') is not True or event_type not in kinds
            or event.get('type') != 'action' or event.get('isPitch') is not False
            or event.get('isSubstitution') is True or details.get('hasReview') is not True
            or not isinstance(review, dict) or review.get('inProgress') is not False
            or type(review.get('isOverturned')) is not bool or review.get('reviewType') not in {'MA','NA'}
            or not match or match.group('review_type').lower() != 'tag play'
            or (not completed_field_review_dispositions(review, description) and linked_tail is None)
            or details.get('isScoringPlay') is not False
            or any(details.get(k) is True for k in ('isBall', 'isStrike', 'isInPlay'))):
        return None
    rows = [r for r in play.get('runners', []) if r.get('details', {}).get('playIndex') == event.get('index')]
    if len(rows) != 1:
        return None
    row = rows[0]; movement = row.get('movement', {}); runner = row.get('details', {}).get('runner', {})
    origin, destination, out, ordinal = kinds[event_type]
    name = runner.get('fullName')
    before = events[position-1].get('count', {}); after = event.get('count', {})
    if (type(runner.get('id')) is not int or runner['id'] <= 0 or not isinstance(name, str) or not name
            or row['details'].get('eventType') != event_type or row['details'].get('isScoringEvent') is not False
            or movement.get('originBase') != origin or movement.get('start') != origin
            or movement.get('isOut') is not out or details.get('isOut') is not out
            or movement.get('end') != (None if out else destination)
            or movement.get('outBase') != (destination if out else None)
            or any(type(c.get(k)) is not int or not 0 <= c[k] <= limit
                   for c in (before, after) for k, limit in (('balls', 3), ('strikes', 2), ('outs', 3)))
            or before['outs'] >= 3 or after['outs'] != before['outs'] + int(out)
            or any(before[k] != after[k] for k in ('balls', 'strikes'))
            or movement.get('outNumber') != (after['outs'] if out else None)):
        return None
    outcome_text = (r' caught stealing ' if out else r' steals(?: \(\d+\))? ') + ordinal + r' base[.,]'
    if not re.match(re.escape(name) + outcome_text, linked_tail if linked_tail is not None else description[match.end():].strip()):
        return None
    return dict(kind='unchanged-runner-tag-review', runnerId=str(runner['id']), overturned=review['isOverturned'],
                scope='final runner-history effects only; no original decision or mechanism assigned')


def completed_field_review_dispositions(review, description):
    """Match every completed provider disposition to its explicit narrative.

    Provider codes select final source records only. They mint no review kind,
    original call, affected player or eligible challenge opportunity in RDF.
    """
    codes = {
        'tag play': {'MA', 'NA'}, 'pitch result': {'MJ', 'NJ'}, 'play at 1st': {'MF', 'NF'},
        'force play': {'MC', 'NC'}, 'catch or drop': {'MD', 'ND'},
        'trap play': {'MT', 'NT'}, 'home run': {'MH', 'NH'},
        'hit by pitch': {'MI', 'NI'}, 'shift violation': {'MW', 'NW'},
        'rules check': {'MQ', 'NQ'}, 'tag-up play': {'MU', 'NU'},
        'touching a base': {'MB', 'NB'}, 'catcher interference': {'MV', 'NV'},
        'fair or foul in outfield': {'MO', 'NO'}, 'timing play': {'MM', 'NM'},
        'home-plate collision': {'MP', 'NP'}, 'stadium boundary call': {'MS', 'NS'},
        'slide interference': {'ME', 'NE'}, 'fan interference': {'MN', 'NN'},
        'passing runners': {'MR','NR'}, 'runner placement': {'MY','NY'},
        'grounds rule': {'MG','NG'}, 'record keeping': {'MK','NK'},
    }
    pending = [review]
    while pending:
        item = pending.pop(0)
        match = REVIEW_DESCRIPTION.search(description)
        if (not isinstance(item, dict) or item.get('inProgress') is not False
                or type(item.get('isOverturned')) is not bool or not match
                or item.get('reviewType') not in codes.get(match.group('review_type').lower(), set())
                or not match.group('status')
                or (match.group('status').lower() == 'overturned') != item['isOverturned']):
            return False
        extra = item.get('additionalReviews', [])
        if not isinstance(extra, list): return False
        pending[0:0] = extra
        description = description[match.end():].lstrip()
    return not REVIEW_DESCRIPTION.search(description)


def completed_nonterminal_field_review(play, position):
    """A final ordinary counter transition does not imply an original call."""
    events = play.get('playEvents', [])
    if not 0 <= position < len(events)-1: return None
    event = events[position]; detail = event.get('details', {})
    review = event.get('reviewDetails')
    allowed = {'MO': {'F'}, 'NO': {'F'}, 'NH': {'F'}, 'MH': {'F'},
               'MN': {'F'}, 'NN': {'F'}, 'MI': {'B','*B','F','L','T','O'},
               'NI': {'B','*B','F','L','T','O'}, 'MV': {'B','*B','F','T'}, 'NV': {'B','*B','F','T'}}
    code = detail.get('call',{}).get('code')
    before = events[position-1].get('count', {}) if position else dict(balls=0,strikes=0,outs=event.get('count',{}).get('outs'))
    after = event.get('count',{})
    if (play.get('about',{}).get('isComplete') is True and event.get('type') == 'pickoff'
            and event.get('isPitch') is False and detail.get('isOut') is False
            and detail.get('hasReview') is True and isinstance(review,dict)
            and review.get('reviewType') in {'MA','NA'} and review.get('inProgress') is False
            and type(review.get('isOverturned')) is bool and not review.get('additionalReviews')
            and not any(r.get('details',{}).get('playIndex') == event.get('index') for r in play.get('runners',[]))
            and SAFE_IRI_SEGMENT.fullmatch(str(event.get('playId') or ''))
            and sum(e.get('playId') == event.get('playId') for e in events) == 1
            and all(type(before.get(k)) is int and 0 <= before[k] <= n and before[k] == after.get(k)
                    for k,n in (('balls',3),('strikes',2),('outs',2)))):
        return dict(kind='completed-no-movement-pickoff-review',overturned=review['isOverturned'],
                    scope='no final runner/count effect; no original call or Safe judgment inferred')
    if (play.get('about',{}).get('isComplete') is not True or not isinstance(review,dict)
            or review.get('inProgress') is not False or type(review.get('isOverturned')) is not bool
            or not isinstance(review.get('additionalReviews',[]),list)
            or any(not isinstance(v,dict) or v.get('reviewType') not in {'MK','NK'}
                   or v.get('inProgress') is not False or type(v.get('isOverturned')) is not bool
                   or v.get('additionalReviews') for v in review.get('additionalReviews',[]))
            or code not in allowed.get(review.get('reviewType'),set())
            or detail.get('hasReview') is not True or event.get('isPitch') is not True
            or detail.get('isInPlay') is not False or detail.get('isOut') is not False
            or not SAFE_IRI_SEGMENT.fullmatch(str(event.get('playId') or ''))
            or sum(e.get('playId') == event.get('playId') for e in events) != 1
            or any(r.get('details',{}).get('playIndex') == event.get('index') for r in play.get('runners',[]))
            or any(type(c.get(k)) is not int or not 0 <= c[k] <= limit
                   for c in (before,after) for k,limit in (('balls',3),('strikes',2),('outs',2)))):
        return None
    ball = code in {'B','*B'}
    expected = (before['balls'] + int(ball),
                before['strikes'] if ball else min(2,before['strikes']+1) if code == 'F' else before['strikes']+1)
    if (expected != (after['balls'],after['strikes']) or before['outs'] != after['outs']
            or detail.get('isBall') is not ball or detail.get('isStrike') is not (not ball)):
        return None
    return dict(kind='completed-field-count',playId=event['playId'],overturned=review['isOverturned'],
                scope='final operative count only; original call and review RDF not inferred')


def completed_independent_review(play, position):
    """Reconcile reviewed multi-runner effects without assigning review subjects."""
    events = play.get('playEvents',[])
    if not 0 < position < len(events)-1 or play.get('about',{}).get('isComplete') is not True:return None
    event = events[position]; detail = event.get('details',{})
    review = event.get('reviewDetails'); before = events[position-1].get('count',{})
    if detail.get('hasReview') is not True or not completed_field_review_dispositions(review,detail.get('description','')):
        return None
    rows = [r for r in play.get('runners',[]) if r.get('details',{}).get('playIndex') == event.get('index')]
    # Preserve the stricter existing single-steal/tag witness and its negative cases.
    if (len(rows) == 1 and detail.get('eventType') in {'stolen_base_2b','stolen_base_3b','caught_stealing_2b','caught_stealing_3b'}
            and review.get('reviewType') in {'MA','NA'} and not review.get('additionalReviews')):return None
    if not counted_foul_running_prefix(None,play,event,(before.get('balls'),before.get('strikes')),check_review=False):
        return None
    description = detail['description']
    while (match := REVIEW_DESCRIPTION.search(description)):
        description = description[match.end():].lstrip()
    for row in rows:
        movement = row['movement']; name = row['details'].get('runner',{}).get('fullName')
        base = movement.get('outBase') if movement['isOut'] else movement.get('end')
        ordinal = {'1B':'1st','2B':'2nd','3B':'3rd','4B':'home','score':'home'}.get(base)
        if not name or not ordinal or movement.get('start') != movement.get('originBase'):return None
        if movement['isOut']:
            pattern = (re.escape(name) + r' (?:caught stealing |out at |picked off and caught stealing )' + ordinal
                       + r'\b|picks off ' + re.escape(name) + r' at ' + ordinal + r'\b')
        elif base == 'score':pattern = re.escape(name) + r' scores\b'
        else:pattern = re.escape(name) + r' (?:to |steals(?: \(\d+\))? )' + ordinal + r'\b'
        if not re.search(pattern,description):return None
    if len(rows)==1 and detail.get('isOut') is not rows[0]['movement']['isOut']:return None
    return dict(kind='completed-independent-review',overturned=review['isOverturned'],
                scope='final runner effects only; original call and affected player not inferred')


def catcher_pickoff_boundary_kind(play, event):
    """Reuse C3's association/type/runner token for an evidenced catcher pickoff."""
    events=play.get('playEvents',[]);detail=event.get('details',{})
    kind=play.get('result',{}).get('eventType');base={
        'pickoff_1b':'1B','pickoff_2b':'2B','pickoff_3b':'3B'}.get(kind)
    if (not events or event is not events[-1] or base is None
            or play.get('about',{}).get('isComplete') is not True
            or event.get('type')!='pickoff' or event.get('isPitch') is not False
            or event.get('playId') or not SAFE_IRI_SEGMENT.fullmatch(str(event.get('actionPlayId') or ''))
            or detail.get('code')!=base[0] or detail.get('fromCatcher') is not True
            or detail.get('isOut') is not True or detail.get('hasReview') is not False
            or event.get('reviewDetails') or play.get('result',{}).get('isOut') is not True):return None
    prior=[e for e in events[:-1] if e.get('playId')==event['actionPlayId'] and e.get('isPitch') is True]
    rows=[r for r in play.get('runners',[]) if r.get('details',{}).get('playIndex')==event.get('index')]
    before=event.get('count',{});after=play.get('count',{})
    if (len(prior)!=1 or prior[0].get('count')!=before or len(rows)!=1
            or any(type(before.get(k)) is not int or not 0<=before[k]<=limit
                   for k,limit in (('balls',3),('strikes',2),('outs',2)))
            or any(after.get(k)!=before[k] for k in ('balls','strikes'))
            or after.get('outs')!=before['outs']+1):return None
    row=rows[0];movement=row.get('movement',{});details=row.get('details',{})
    if (any(movement.get(k)!=base for k in ('originBase','start','outBase'))
            or movement.get('isOut') is not True or movement.get('end') is not None
            or movement.get('outNumber')!=after['outs'] or details.get('eventType')!=kind
            or details.get('isScoringEvent') is not False
            or not str(details.get('runner',{}).get('id','')).isdigit()):return None
    return kind


def accounted_runner_history_reviews(play: dict) -> dict:
    """Select the reconciled final effect; review identity remains independent."""
    review = play.get('reviewDetails')
    events = play.get('playEvents', [])
    terminal = events[-1] if events else {}
    details = terminal.get('details', {})
    nonmovements = nonmovement_strikeout_records(play, check_review=False)
    terminal_rows = [r for i, r in enumerate(play.get('runners', []))
                     if r.get('details', {}).get('playIndex') == terminal.get('index') and i not in nonmovements]
    # A completed field review can finish as an ordinary hit/out, HBP,
    # interference or pickoff. Its final label need not name the reviewed call.
    final_effect = ((terminal.get('isPitch') is True
        and details.get('call', {}).get('code') in {'X','D','E','H','B','*B','C','S','W','T','F','L','M','O'})
        or (terminal.get('isPitch') is False and terminal.get('type') == 'pickoff'))
    supported = (play.get('about', {}).get('hasReview') is True
        and play['about'].get('isComplete') is True
        and completed_field_review_dispositions(review, play.get('result', {}).get('description', ''))
        and final_effect and (SAFE_IRI_SEGMENT.fullmatch(str(terminal.get('playId') or ''))
            or catcher_pickoff_boundary_kind(play,terminal))
        and not terminal.get('reviewDetails') and details.get('hasReview') is False
        and bool(terminal_rows)
        and all(type(r.get('movement', {}).get('isOut')) is bool
                and type(r.get('details', {}).get('isScoringEvent')) is bool for r in terminal_rows))
    count_scope = {**play}
    if supported:
        # Only the positively accounted terminal field review leaves the
        # count scope. Earlier reviews are examined independently below.
        count_scope['about'] = {**play['about'], 'hasReview': False}
        count_scope.pop('reviewDetails', None)
    accounted, count_events = {}, []
    for position, event in enumerate(events):
        detail = event.get('details', {})
        candidate = event.get('reviewDetails')
        before = events[position-1].get('count', {}) if position else dict(balls=0, strikes=0)
        after = event.get('count', {})
        # E1 final-state reconciliation only: an affirmed ordinary foul with
        # no movement/out cannot change runner occupancy. This does not admit
        # M3/M4 count/review RDF, original calls, or challenge eligibility.
        unchanged_foul = (play.get('about', {}).get('isComplete') is True
            and position < len(events)-1 and isinstance(candidate, dict)
            and candidate.get('inProgress') is False and candidate.get('isOverturned') is False
            and candidate.get('reviewType') == 'MO' and detail.get('hasReview') is True
            and event.get('isPitch') is True and detail.get('call', {}).get('code') == 'F'
            and detail.get('isInPlay') is False and detail.get('isOut') is False
            and detail.get('isStrike') is True and detail.get('isBall') is False
            and SAFE_IRI_SEGMENT.fullmatch(str(event.get('playId') or ''))
            and not any(r.get('details', {}).get('playIndex') == event.get('index')
                        for r in play.get('runners', []))
            and all(type(c.get(k)) is int and 0 <= c[k] <= limit
                    for c in (before, after) for k, limit in (('balls', 3), ('strikes', 2)))
            and after['balls'] == before['balls'] and after['strikes'] == min(2, before['strikes']+1)
            and type(before.get('outs')) is int and 0 <= before['outs'] < 3
            and after.get('outs') == before['outs'])
        runner_tag = (unchanged_runner_tag_review(play, position) or completed_pickoff_review(play, position)
                      or completed_nonterminal_field_review(play, position)
                      or completed_independent_review(play, position))
        if unchanged_foul or runner_tag:
            accounted[event['index']] = runner_tag or dict(playId=event['playId'], kind='unchanged-foul',
                overturned=False, scope='final runner-history effects only')
            clean = {**event, 'details': {**detail, 'hasReview': False}}
            clean.pop('reviewDetails', None)
            count_events.append(clean)
        else:
            count_events.append(event)
    count_scope['playEvents'] = count_events
    result = accounted_runner_count_reviews(count_scope)
    result['events'].update(accounted)
    if supported:
        result['accountedFieldReview'] = dict(eventIndex=terminal['index'],
            reviewType=review['reviewType'], overturned=review['isOverturned'])
        if terminal.get('playId'):result['accountedFieldReview']['playId']=terminal['playId']
        else:result['accountedFieldReview']['boundaryAssociationId']=terminal['actionPlayId']
    return result


def completed_pickoff_review(play, position):
    """Account for an explicit final pickoff out without inferring its old call."""
    events = play.get('playEvents', [])
    if position == 0 or position >= len(events)-1:
        return None
    event = events[position]; detail = event.get('details', {})
    review = event.get('reviewDetails', {})
    match = REVIEW_DESCRIPTION.search(detail.get('description', ''))
    base = {'pickoff_1b': '1B', 'pickoff_2b': '2B', 'pickoff_3b': '3B'}.get(detail.get('eventType'))
    rows = [r for r in play.get('runners', []) if r.get('details', {}).get('playIndex') == event.get('index')]
    if (not base or len(rows) != 1 or not match or match.group('review_type').lower() != 'tag play'
            or not match.group('status') or review.get('inProgress') is not False
            or type(review.get('isOverturned')) is not bool or review.get('reviewType') != 'MA'
            or (match.group('status').lower() == 'overturned') != review['isOverturned']
            or play.get('about', {}).get('isComplete') is not True
            or event.get('type') != 'action' or event.get('isPitch') is not False
            or detail.get('hasReview') is not True or detail.get('isOut') is not True
            or detail.get('isScoringPlay') is not False or event.get('isSubstitution') is True):
        return None
    row = rows[0]; move = row.get('movement', {}); person = row.get('details', {}).get('runner', {})
    before = events[position-1].get('count', {}); after = event.get('count', {})
    attempts = [e for e in events[:position] if e.get('playId') == event.get('actionPlayId')
                and e.get('type') == 'pickoff' and e.get('isPitch') is False]
    if (len(attempts) != 1 or not SAFE_IRI_SEGMENT.fullmatch(str(event.get('actionPlayId') or ''))
            or type(person.get('id')) is not int or person['id'] <= 0 or not person.get('fullName')
            or event.get('player', {}).get('id') != person['id']
            or row.get('details', {}).get('eventType') != detail.get('eventType')
            or row['details'].get('isScoringEvent') is not False
            or move != dict(originBase=base, start=base, end=None, outBase=base,
                           isOut=True, outNumber=after.get('outs'))
            or any(type(before.get(k)) is not int or not 0 <= before[k] <= limit
                   or type(after.get(k)) is not int for k, limit in (('balls', 3), ('strikes', 2), ('outs', 2)))
            or any(before[k] != after[k] for k in ('balls', 'strikes'))
            or after['outs'] != before['outs'] + 1
            or not re.search(r' picks off ' + re.escape(person['fullName']) + r' at '
                             + {'1B': '1st', '2B': '2nd', '3B': '3rd'}[base] + r'\b',
                             detail['description'][match.end():])):
        return None
    return dict(kind='completed-pickoff-review', runnerId=str(person['id']),
                overturned=review['isOverturned'], scope='final runner-history effects only')


def nonmovement_strikeout_records(play, *, check_review=True):
    """Recognize an empty K record beside an explicit safe WP/PB movement.

    The complete positive companion and post-state establish the boundary;
    the null fields alone establish neither an out nor a safe advancement.
    Preserve the distinct source records without inventing a second running act.
    """
    if (play.get('result', {}).get('eventType') != 'strikeout'
            or play['result'].get('isOut') is not False or play.get('count', {}).get('strikes') != 3
            or (check_review and (play.get('about', {}).get('hasReview') is not False
                                  or play.get('reviewDetails'))
                and accounted_runner_history_reviews(play)['issues'])):
        return {}
    batter = play.get('matchup', {}).get('batter', {}).get('id')
    if type(batter) is not int or batter <= 0:
        return {}
    records = [(i,r) for i,r in enumerate(play.get('runners', [])) if r.get('details', {}).get('runner', {}).get('id') == batter]
    if len(records) not in (2,3):
        return {}
    empty = [(i,r) for i,r in records if r.get('details', {}).get('eventType') == 'strikeout'
             and set(r.get('movement', {})) == {'originBase','start','end','outBase','isOut','outNumber'}
             and all(v is None for v in r['movement'].values())
             and r['details'].get('isScoringEvent') is False and not r.get('credits')]
    safe = [(i,r) for i,r in records if r.get('details', {}).get('eventType') in {'wild_pitch','passed_ball'}
            and r.get('movement') == dict(originBase=None,start=None,end='1B',outBase=None,isOut=False,outNumber=None)
            and r['details'].get('isScoringEvent') is False]
    if len(empty) != 1 or len(safe) != 1:
        return {}
    index = empty[0][1]['details'].get('playIndex')
    continuation=[r for i,r in records if i not in {empty[0][0],safe[0][0]}]
    if continuation:
        row,=continuation
        if (row.get('movement')!=dict(originBase=row.get('movement',{}).get('originBase'),start='1B',end='2B',outBase=None,isOut=False,outNumber=None)
                or row['movement'].get('originBase') not in (None,'1B')
                or row.get('details',{}).get('playIndex')!=index or row['details'].get('isScoringEvent') is not False):return {}
    final='postOnSecond' if continuation else 'postOnFirst'
    if play['matchup'].get(final,{}).get('id')!=batter:return {}
    events = [e for e in play.get('playEvents', []) if e.get('index') == index]
    if (safe[0][1]['details'].get('playIndex') != index or len(events) != 1
            or events[0].get('isPitch') is not True or events[0].get('count', {}).get('strikes') != 3
            or events[0].get('details', {}).get('isInPlay') is not False):
        return {}
    return {empty[0][0]: safe[0][0]}


def runner_boundary_anchors(document):
    """C3 source witnesses and collision census; tokens are not RDF entities."""
    anchors, candidates = {}, defaultdict(list)
    for p, play in enumerate(document['liveData']['plays']['allPlays']):
        about = play['about']; pa = play['atBatIndex']
        for e, event in enumerate(play['playEvents']):
            kind = event.get('details', {}).get('eventType')
            person = str(event.get('player', {}).get('id', ''))
            outgoing = str(event.get('replacedPlayer', {}).get('id', ''))
            prefix = f"/liveData/plays/allPlays/{p}/playEvents/{e}"
            common = dict(atBatIndex=pa, eventIndex=event['index'], sourcePointer=prefix,
                earliestStartBound=event.get('startTime'), latestEndBound=event.get('endTime'))
            token = None
            if kind == 'offensive_substitution' and event.get('position', {}).get('abbreviation') == 'PR':
                if person.isdigit() and outgoing.isdigit():
                    token = f"replacement/{about['inning']}/{about['halfInning']}/{outgoing}/{person}"
                    candidates[token].append(dict(common, form='replacement', runnerId=person,
                        outgoingRunnerId=outgoing, base=event.get('base')))
            elif kind == 'runner_placed':
                if person.isdigit():
                    token = f"placement/{about['inning']}/{about['halfInning']}/{person}"
                    candidates[token].append(dict(common, form='placement', runnerId=person, base=event.get('base')))
            if token:
                anchors[(pa, event['index'], None)] = token
            # A stable pitch ID retains the existing serialization. C3 is a
            # fallback only for a positively identified non-pitch action.
            association = str(event.get('actionPlayId') or '')
            catcher_kind = catcher_pickoff_boundary_kind(play,event)
            if catcher_kind:kind=catcher_kind
            if (event.get('playId') or event.get('isPitch') is not False
                    or (event.get('type') != 'action' and not catcher_kind)
                    or not SAFE_IRI_SEGMENT.fullmatch(association)
                    or not isinstance(kind, str) or not SAFE_IRI_SEGMENT.fullmatch(kind)):
                continue
            terminal = defaultdict(list)
            for i, row in enumerate(play['runners']):
                if row['details']['playIndex'] == event['index'] and (
                        row['movement'].get('isOut') is True or row['details'].get('isScoringEvent') is True):
                    terminal[str(row['details']['runner']['id'])].append(i)
            for runner, rows in terminal.items():
                token = f'action/{association}/{kind}/{runner}'
                anchors[(pa, event['index'], runner)] = token
                candidates[token].append(dict(common, form='action', runnerId=runner,
                    associationId=association, eventType=kind,
                    runnerPointers=[f'/liveData/plays/allPlays/{p}/runners/{i}' for i in rows],
                    terminalRecords=len(rows)))
    witnesses = {token:dict(rows[0], anchor=token) for token, rows in candidates.items()
                 if len(rows) == 1 and rows[0].get('terminalRecords', 1) == 1}
    return anchors, witnesses, [dict(anchor=token, observations=rows) for token, rows in candidates.items()
                               if token not in witnesses]


def verify_runner_history_correction(current, previous):
    """Quarantine uncertain identity/membership changes before another RML run."""
    if previous is None:
        return
    old = {h['lifetimeKey']:h for h in previous.get('histories', [])}
    new = {h['lifetimeKey']:h for h in current['histories']}
    fields = ('runnerId', 'inning', 'half', 'entryAnchor', 'terminationAnchor', 'terminal')
    if any(key not in new or any(row.get(f) != new[key].get(f) for f in fields) for key, row in old.items()):
        raise ValueError('C3 prior runner history identity no longer aligns; correction requires review')
    owners = {(r['atBatIndex'], r['runnerIndex']):r['lifetimeKey'] for r in current['episodeMembership']}
    if any(owners.get((r['atBatIndex'], r['runnerIndex'])) != r['lifetimeKey']
           for r in previous.get('episodeMembership', [])):
        raise ValueError('C3 prior runner episode allocation no longer aligns; correction requires review')


def isolate_zero_episode_histories(result):
    """Accepted Q7: isolate empty histories without admitting the whole half.

    This also accepts the exact retained reconciliation inventory for the two
    authorized additions. Existing lifetime identities and bounds are reused.
    The empty history and all original issues remain in the withheld evidence.
    """
    known={h['lifetimeKey'] for h in result['histories']}
    for half in result['withheldHistories']:
        if not half['issues'] or {i['code'] for i in half['issues']}!={'ZERO_EPISODE_PERSONAL_HISTORY'}:
            continue
        selected=[h for h in half['completedCandidates'] if h['episodes']]
        for history in selected:
            if history['lifetimeKey'] in known:continue
            result['histories'].append(history)
            result['episodeMembership'].extend(dict(lifetimeKey=history['lifetimeKey'],**episode) for episode in history['episodes'])
            if history.get('placement'):
                result['placementAdjudications'].append(dict(lifetimeKey=history['lifetimeKey'],runnerId=history['runnerId'],
                    inning=history['inning'],half=history['half'],**history['placement']))
            known.add(history['lifetimeKey'])
        half['isolatedHistoryKeys']=sorted(h['lifetimeKey'] for h in selected)
        for census in result['halves']:
            if (census['inning'],census['half'])==(half['inning'],half['half']):
                census['personalHistories']=len(selected)
        result['historyIsolationDecision']='archive/design-records/mlb-game-zero-episode-history-isolation/review.json'
    return result


def reconciled_action_pitch_overlap(play, earlier, following):
    """A PB/WP effect and the next counted pitch can have overlapping bounds.

    Their source association and changed counter establish distinct events;
    the caller independently reconciles all runner, out and post-base effects.
    This does not assert precedence or adjust either observed interval.
    """
    events = play.get('playEvents', [])
    if earlier is None or not any(e is earlier for e in events):
        return False
    detail = earlier.get('details', {}); after_detail = following.get('details', {})
    before = earlier.get('count', {}); after = following.get('count', {})
    association = earlier.get('actionPlayId')
    anchors = [e for e in events if e.get('playId') == association and e.get('isPitch') is True]
    call = after_detail.get('call', {}).get('code')
    ball = call in {'B', '*B'}; strike = call in {'C', 'S', 'W'}
    return (earlier.get('type') == 'action' and earlier.get('isPitch') is False
        and detail.get('eventType') in {'passed_ball', 'wild_pitch'}
        and detail.get('hasReview') is False and not earlier.get('reviewDetails')
        and len(anchors) == 1 and SAFE_IRI_SEGMENT.fullmatch(str(association or '')) is not None
        and anchors[0].get('count') == before
        and any(r.get('details', {}).get('playIndex') == earlier.get('index') for r in play.get('runners', []))
        and following.get('isPitch') is True and (ball or strike)
        and SAFE_IRI_SEGMENT.fullmatch(str(following.get('playId') or '')) is not None
        and following['playId'] != association
        and after_detail.get('isBall') is ball and after_detail.get('isStrike') is strike
        and after_detail.get('isInPlay') is False and after_detail.get('isOut') is False
        and not any(r.get('details', {}).get('playIndex') == following.get('index') for r in play.get('runners', []))
        and all(type(before.get(k)) is int and 0 <= before[k] <= limit
                and type(after.get(k)) is int for k, limit in (('balls', 2), ('strikes', 1), ('outs', 2)))
        and after['balls'] == before['balls'] + int(ball)
        and after['strikes'] == before['strikes'] + int(strike)
        and after['outs'] == before['outs'])


def reconciled_pitch_counter_order(play, earlier, following):
    """Source pitch ordinals and counters, never array position or clock repair."""
    events = play.get('playEvents', [])
    if (earlier is None or not any(e is earlier for e in events) or not any(e is following for e in events)
            or following.get('isPitch') is not True):return False
    before = earlier.get('count',{}); after = following.get('count',{})
    if earlier.get('isPitch') is True:
        prior_pitch = earlier
    else:
        if not counted_foul_running_prefix(None,play,earlier,(before.get('balls'),before.get('strikes'))):return False
        candidates = [e for e in events if e.get('isPitch') is True and e.get('index',-1) < earlier.get('index',-1)]
        prior_pitch = candidates[-1] if candidates else None
    ordinal = prior_pitch.get('pitchNumber') if prior_pitch else 0
    if (type(ordinal) is not int or following.get('pitchNumber') != ordinal+1
            or type(following.get('pitchNumber')) is not int
            or any(not SAFE_IRI_SEGMENT.fullmatch(str(e.get('playId') or '')) for e in [following]+([prior_pitch] if prior_pitch else []))
            or (prior_pitch and prior_pitch['playId']==following['playId'])
            or any(type(before.get(k)) is not int or not 0 <= before[k] <= n
                   or type(after.get(k)) is not int for k,n in (('balls',3),('strikes',2),('outs',2)))):
        return False
    code = following.get('details',{}).get('call',{}).get('code')
    if code in {'B','*B'}:expected = before['balls']+1,before['strikes']
    elif code in {'C','S','W','M','T','O','L'}:expected = before['balls'],before['strikes']+1
    elif code=='F':expected = before['balls'],min(2,before['strikes']+1)
    elif code in {'X','D','E'}:expected = before['balls'],before['strikes']
    else:return False
    return expected == (after['balls'],after['strikes']) and before['outs'] == after['outs']


def reconciled_pa_boundary_order(previous, current, earlier, following):
    """Completed outcome and the next batter/count can reconcile overlapping PAs."""
    if previous is None or earlier is None:return False
    prior_events = previous.get('playEvents',[]); events = current.get('playEvents',[])
    pitches = [e for e in events if e.get('isPitch') is True]
    rows = [r for r in previous.get('runners',[]) if r.get('details',{}).get('playIndex') == earlier.get('index')]
    if (not prior_events or earlier is not prior_events[-1] or not pitches or following is not pitches[0]
            or following.get('pitchNumber') != 1 or previous.get('about',{}).get('isComplete') is not True
            or current.get('about',{}).get('isComplete') is not True
            or previous.get('about',{}).get('inning') != current.get('about',{}).get('inning')
            or previous.get('about',{}).get('halfInning') != current.get('about',{}).get('halfInning')
            or not rows or any(type(r.get('movement',{}).get('isOut')) is not bool for r in rows)
            or any(not SAFE_IRI_SEGMENT.fullmatch(str(e.get('playId') or '')) for e in (earlier,following))
            or earlier['playId'] == following['playId']
            or type(previous.get('count',{}).get('outs')) is not int
            or previous['count']['outs'] >= 3 or following.get('count',{}).get('outs') != previous['count']['outs']):
        return False
    # A real terminal runner out can leave the same batter at the plate.
    terminal_runner_out = (earlier.get('type') == 'pickoff' and any(r['movement']['isOut'] for r in rows))
    if not terminal_runner_out and previous.get('matchup',{}).get('batter',{}).get('id') == current.get('matchup',{}).get('batter',{}).get('id'):
        return False
    code = following.get('details',{}).get('call',{}).get('code')
    expected = (1,0) if code in {'B','*B'} else (0,1) if code in {'C','S','W','M','T','O','L','F'} else (0,0) if code in {'X','D','E'} else None
    return expected is not None and expected == (following.get('count',{}).get('balls'),following.get('count',{}).get('strikes'))


def runner_state_neutral_event(play, event, before):
    """Ignore count/movement-free administration, never its potential semantics."""
    detail = event.get('details', {})
    kind = detail.get('eventType')
    if (kind not in {'game_advisory', 'ejection', 'injury', 'umpire_substitution', 'pitcher_switch', 'error', 'mound_visit', 'batter_timeout'}
            or event.get('type') != 'action' or event.get('isPitch') is not False
            or event.get('isSubstitution') is True or event.get('reviewDetails')
            or any(detail.get(k) is not False for k in ('isOut','isScoringPlay','hasReview'))
            or any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))
            or any(type(before.get(k)) is not int or event.get('count',{}).get(k) != before[k]
                   for k in ('balls','strikes','outs'))
            or any(r.get('details',{}).get('playIndex') == event.get('index') for r in play.get('runners',[]))):
        return False
    if kind == 'error':
        related = [e for e in play.get('playEvents',[]) if e.get('playId') == event.get('actionPlayId')]
        return (len(related) == 1 and related[0].get('isPitch') is True
            and related[0].get('details',{}).get('call',{}).get('code') == 'F'
            and detail.get('description','').startswith('Dropped foul pop error by '))
    return event.get('isBaseRunningPlay') is not True


def personal_runner_histories(raw: bytes, previous=None) -> dict:
    """E1/C1 source reconciliation, independent of mapped-row counts.

    Reconciled half innings and Q7's independently complete histories enter.
    Unknown review/substitution effects withhold the whole half, not just the
    inconvenient row. Placement adjudications use the explicit September 16
    decision; no physical location or strict precedence is minted.
    Temporal values below are event bounds, not claimed exact runner timestamps.
    """
    checker = Path(__file__).resolve().parents[2] / 'sources/mlb-game/pipeline/reconcile-metric-source.py'
    canonical = checker.read_text(encoding='utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').encode()
    if hashlib.sha256(canonical).hexdigest() != '20ccdcb154db8d3f72625dffc4c88b5fad63756c894ca5c1758923300ae80034':
        raise ValueError('Runner-history source reconciler differs from its reviewed dependency pin')
    spec = importlib.util.spec_from_file_location('runner_source_reconciler', checker)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    document = json.loads(raw)
    source = module.reconcile(raw, str(document['gamePk']))
    result = dict(inputSha256=source['inputSha256'], sourceRevision=source['sourceRevision'],
                  sourceAuthorityDecision='archive/design-records/metric-source-c1-operation-2026-09-14/review.json',
                  sourceConsistency=source['status'], clockConflicts=source['clockConflicts'],
                  clockDecision=source['clockDecision'], histories=[], withheldHistories=[], episodeMembership=[], placementAdjudications=[], halves=[], boundaryIssues=[],
                  graphCoverageVerified=False, metricPopulationAdmitted=False)
    if source['status'] != 'consistent':
        result['sourceIssues'] = source['issues']
        verify_runner_history_correction(result, previous)
        return result
    groups = defaultdict(list)
    for play in document['liveData']['plays']['allPlays']:
        groups[(play['about']['inning'], play['about']['halfInning'])].append(play)
    anchor_keys, anchor_witnesses, anchor_collisions = runner_boundary_anchors(document)
    result.update(boundaryIdentityDecision='archive/design-records/mlb-game-runner-boundary-anchors/review.json',
                  boundaryAnchorCensus=list(anchor_witnesses.values()), boundaryAnchorCollisions=anchor_collisions)
    known_people = {str(p['id']) for p in document['gameData']['players'].values()}

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
                   'defensive_indiff', 'pickoff_error_1b', 'pickoff_error_2b', 'pickoff_error_3b',
                   'pickoff_caught_stealing_2b', 'pickoff_caught_stealing_3b', 'pickoff_caught_stealing_home',
                   'forced_balk', 'other_out', 'other_advance'}
    for (inning, half), plays in groups.items():
        active, histories, memberships, problems = {}, [], [], []
        outs = 0
        previous_pa_end = None
        previous_play = None
        last_event_end = None
        last_timed_event = None
        last_boundary_end = None
        boundary_overlap_event = None

        def block(code, pa=None):
            problems.append(dict(code=code, atBatIndex=pa))

        def finish(item, anchor, terminal, bound):
            if not item['episodes'] and not item.get('placement'):
                block('ZERO_EPISODE_PERSONAL_HISTORY', item.get('entryAtBatIndex'))
            # Stable serialization of the reviewed lifetime anchors, not a
            # source revision, PA index or row-position identity for the whole.
            identity = [str(document['gamePk']), item['runnerId'], item['entryAnchor'], anchor]
            key = hashlib.sha256(json.dumps(identity, separators=(',', ':')).encode()).hexdigest()
            completed = dict(item, lifetimeKey=key, terminationAnchor=anchor,
                             terminal=terminal, latestEndBound=bound)
            if anchor in anchor_witnesses:
                completed['terminationWitness'] = anchor_witnesses[anchor]
            if terminal == 'game-ended':
                completed['gameEndInstantIri'] = f"https://baseballontology.org/data/game/{document['gamePk']}/temporal-instant/end"
            histories.append(completed)
            memberships.extend(dict(lifetimeKey=key, **episode) for episode in item['episodes'])

        for play in plays:
            pa = play['atBatIndex']; about = play['about']; rows = play['runners']
            pa_start, pa_end = map(instant, clock_pair(about))
            if pa_start is None or pa_end is None:
                block('UNSUPPORTED_PA_CLOCK_PAIR', pa)
                result['boundaryIssues'].append(dict(code='UNSUPPORTED_PA_CLOCK_PAIR', atBatIndex=pa))
            if previous_pa_end and pa_start and pa_start < previous_pa_end:
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
            nonmovements = nonmovement_strikeout_records(play)
            for row_index, row in enumerate(rows):
                if row_index not in nonmovements:
                    event_rows[row['details']['playIndex']].append((row_index, row))
            admitted_pairs = {int(item['runnerIndex']): item for item in runner_episode_evidence(play, str(pa))['runnerEpisodes']}
            # Account for every source record without turning the all-null K
            # bookkeeping companion into a second movement or lifetime entry.
            if set(admitted_pairs) != set(range(len(rows))) - set(nonmovements):
                block('UNSUPPORTED_RUNNER_EPISODE', pa)
            for event_position, event in enumerate(events):
                index = event['index']; details = event.get('details', {})
                kind, event_type = event.get('type'), details.get('eventType')
                selected = event_rows[index]
                if outs == 3 and (event.get('isPitch') is True or selected or event_type == 'runner_placed'):
                    block('EVENT_AFTER_HALF_END', pa)
                if (event.get('reviewDetails') or details.get('hasReview') is True) and index not in reviews['events']:
                    block('UNRESOLVED_REVIEW_EFFECT', pa)
                batting_only = (batting_changes_supported and event_type == 'offensive_substitution'
                    and event.get('position', {}).get('abbreviation') == 'PH'
                    and not selected and str(event.get('replacedPlayer', {}).get('id')) not in active
                    and str(event.get('player', {}).get('id')) not in active)
                prior_count = events[event_position - 1].get('count', {}) if event_position else dict(balls=0, strikes=0, outs=outs)
                administrative_anchor = anchor_keys.get((pa, index, None))
                administrative = anchor_witnesses.get(administrative_anchor)
                administrative_supported = False
                if administrative_anchor:
                    incoming = str(event.get('player', {}).get('id', ''))
                    outgoing = str(event.get('replacedPlayer', {}).get('id', ''))
                    base = str(event.get('base')) + 'B'
                    start, end = map(instant, clock_pair(event))
                    following = next((x for x in events[event_position + 1:]
                        if x.get('isPitch') is True or event_rows[x['index']]), None)
                    next_start = instant(clock_pair(following or {})[0])
                    # The accepted September 30 overlap policy uses the named
                    # replacement and subsequent movement, not array position
                    # or separated clock endpoints, to reconcile this boundary.
                    placed = active.get(outgoing, {})
                    placement_replacement_overlap = (
                        administrative is not None and administrative['form'] == 'replacement'
                        and placed.get('entryWitness', {}).get('form') == 'placement'
                        and placed.get('base') == base and last_event_end is None
                        and start is not None and last_boundary_end is not None
                        and instant(placed.get('earliestStartBound')) is not None
                        and instant(placed['earliestStartBound']) <= start < last_boundary_end
                        and any(str(r.get('details', {}).get('runner', {}).get('id')) == incoming
                            and r.get('movement', {}).get('start') == base
                            and r.get('details', {}).get('playIndex', -1) > index for r in rows))
                    common = (administrative is not None and event.get('type') == 'action'
                        and event.get('isPitch') is False and not selected and incoming in known_people
                        and incoming not in active and base in {'1B', '2B', '3B'}
                        and details.get('isScoringPlay') is False and details.get('isOut') is False
                        and details.get('hasReview') is False and not event.get('reviewDetails')
                        and all(type(prior_count.get(k)) is int and event.get('count', {}).get(k) == prior_count[k]
                                for k in ('balls', 'strikes', 'outs')) and prior_count['outs'] == outs
                        and start is not None and end is not None and next_start is not None
                        and pa_end is not None and start <= end and end <= pa_end
                        and (end <= next_start or (start <= next_start and following.get('isPitch') is True
                             and following.get('pitchNumber') == 1 and not any(e.get('isPitch') is True for e in events[:event_position])
                             and SAFE_IRI_SEGMENT.fullmatch(str(following.get('playId') or ''))))
                        and (last_event_end is None or last_event_end <= start)
                        and (last_boundary_end is None or last_boundary_end <= start
                             or placement_replacement_overlap))
                    replacement = (common and administrative['form'] == 'replacement'
                        and event.get('isSubstitution') is True and outgoing != incoming
                        and outgoing in known_people and outgoing in active and active[outgoing]['base'] == base)
                    placement = (common and administrative['form'] == 'placement'
                        and document['gameData']['game'].get('type') == 'R' and inning > 9
                        and play is plays[0] and outs == 0 and last_event_end is None and not active
                        and base == '2B' and prior_count['balls'] == prior_count['strikes'] == 0)
                    if replacement or placement:
                        if replacement:
                            if placement_replacement_overlap:
                                result.setdefault('reconciledAdministrativeOverlaps', []).append(dict(
                                    atBatIndex=pa, placementAnchor=placed['entryAnchor'],
                                    replacementAnchor=administrative_anchor,
                                    placementEndBound=last_boundary_end.isoformat(),
                                    replacementStartBound=event['startTime']))
                                result['temporalOverlapDecision'] = 'archive/design-records/metric-repair-scope-2026-09-30/answers.md'
                            finish(active.pop(outgoing), administrative_anchor, 'replaced', event.get('endTime'))
                        active[incoming] = dict(runnerId=incoming, inning=str(inning), half=half,
                            entryAnchor=administrative_anchor, entryWitness=administrative,
                            entryAtBatIndex=pa, earliestStartBound=event.get('startTime'), episodes=[], base=base)
                        if placement and str(document['gameData']['game'].get('season')) == '2026':
                            root = f"https://baseballontology.org/data/game/{document['gamePk']}/{administrative_anchor}"
                            active[incoming]['placement'] = dict(
                                judgmentIri=root + '/judgment', decisionIri=root + '/decision',
                                recordIri=root + '/record',
                                ruleIri='https://baseballontology.org/data/rule/2026/extra-inning-placement',
                                baseIri=f"https://baseballontology.org/data/venue/{document['gameData']['venue']['id']}/artifact/base/2B")
                        last_boundary_end = end
                        boundary_overlap_event = following if next_start < end else None
                        administrative_supported = True
                        # C3 does not license physical start stases or a reverse
                        # metric projection from an administrative base field.
                        result['boundaryIssues'].append(dict(code='C3_ADMINISTRATIVE_BASE_BOUNDARY', atBatIndex=pa,
                            anchor=administrative_anchor, sourcePointer=administrative['sourcePointer']))
                    else:
                        block('UNSUPPORTED_C3_ADMINISTRATIVE_BOUNDARY', pa)
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
                             or batting_only or delay_only or administrative_supported
                             or runner_state_neutral_event(play, event, prior_count)
                             or (event_type == 'game_advisory' and details.get('description') in advisories))
                if not supported:
                    block('UNSUPPORTED_EVENT_EFFECT:' + str(event_type or kind), pa)
                if event_type in independent and not selected:
                    block('MISSING_INDEPENDENT_MOVEMENT', pa)
                start, end = map(instant, clock_pair(event))
                # Neutral administrative observations need no invented instant.
                # All pitch/movement boundary events require usable time bounds.
                if event.get('isPitch') is True or selected:
                    if (not start or not end or not pa_start or not pa_end or start > end or (event.get('isPitch') is True and (start < pa_start or end > pa_end))
                            or (last_event_end and start < last_event_end
                                and not (reconciled_action_pitch_overlap(play, last_timed_event, event)
                                         or reconciled_pitch_counter_order(play, last_timed_event, event)
                                         or reconciled_pa_boundary_order(previous_play, play, last_timed_event, event)))
                            or (last_boundary_end and start < last_boundary_end and event is not boundary_overlap_event)):
                        block('UNSUPPORTED_EVENT_TIME_ORDER', pa)
                    if end:
                        last_event_end = end
                    last_timed_event = event
                    if kind != 'action' and event.get('count', {}).get('outs') != outs:
                        block('PRE_EVENT_OUT_COUNT_MISMATCH', pa)
                event_anchor = str(event.get('playId') or '')
                stable_anchor = bool(SAFE_IRI_SEGMENT.fullmatch(event_anchor))
                by_runner = defaultdict(list)
                for row_index, row in selected:
                    by_runner[str(row['details']['runner']['id'])].append((row_index, row))
                out_numbers = []
                for runner, pending_rows in by_runner.items():
                    runner_anchor = event_anchor if stable_anchor else anchor_keys.get((pa, index, runner))
                    runner_anchor_valid = stable_anchor or runner_anchor in anchor_witnesses
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
                            if not runner_anchor_valid:
                                block('MISSING_STABLE_MOVEMENT_ANCHOR', pa)
                            finish(item, runner_anchor or '', 'out' if out else 'score', event.get('endTime'))
                            del active[runner]
                            break
                        if end_base not in {'1B', '2B', '3B'}:
                            block('UNKNOWN_SAFE_DESTINATION', pa); break
                        item['base'] = end_base
                if any(type(n) is not int for n in out_numbers) or sorted(out_numbers) != list(range(outs + 1, outs + len(out_numbers) + 1)):
                    block('DISTINCT_OUT_RECONCILIATION_FAILED', pa)
                outs += len(out_numbers)
                if selected and kind == 'action' and event.get('count', {}).get('outs') != outs:
                    block('POST_ACTION_OUT_COUNT_MISMATCH', pa)
                if outs > 3:
                    block('TOO_MANY_OUTS', pa)
                occupied = [item['base'] for item in active.values() if item['base'] is not None]
                # At three reconciled outs these are last observations, not a
                # live occupancy snapshot. Do not infer missing forced advances.
                if outs < 3 and len(set(occupied)) != len(occupied):
                    block('CONFLICTING_BASE_OCCUPANCY', pa)
            if play.get('count', {}).get('outs') != outs:
                block('POST_PA_OUT_COUNT_MISMATCH', pa)
            for code, field in [('1B', 'postOnFirst'), ('2B', 'postOnSecond'), ('3B', 'postOnThird')]:
                reported = play.get('matchup', {}).get(field)
                if reported is not None and active.get(str(reported.get('id')), {}).get('base') != code:
                    block('POST_BASE_RECONCILIATION_FAILED', pa)
            if outs == 3 and play is not plays[-1]:
                block('EVENT_AFTER_HALF_END', pa)
            previous_play = play
        last_play = plays[-1]
        boundary = supported_walkoff_boundary(document, last_play) if outs != 3 else None
        if boundary:
            if not problems:
                for item in active.values():
                    finish(item, boundary['eventId'], 'game-ended', boundary['endTime'])
        else:
            if outs != 3:
                block('UNSUPPORTED_HALF_TERMINATION')
            terminal_rows = [r for r in last_play['runners'] if r['movement'].get('isOut') is True
                             and r['movement'].get('outNumber') == 3]
            terminal_event = event_by_index[terminal_rows[0]['details']['playIndex']] if len(terminal_rows) == 1 else {}
            terminal_anchor = terminal_event.get('playId') or (anchor_keys.get((last_play['atBatIndex'],
                terminal_event['index'], str(terminal_rows[0]['details']['runner']['id']))) if terminal_event else None)
            if not terminal_anchor or (not terminal_event.get('playId') and terminal_anchor not in anchor_witnesses):
                block('UNSUPPORTED_THIRD_OUT_ANCHOR')
            elif not problems:
                for item in active.values():
                    finish(item, terminal_anchor, 'stranded', last_play['about']['endTime'])
        result['halves'].append(dict(inning=inning, half=half, status='withheld' if problems else 'reconciled',
                                    issues=problems, personalHistories=0 if problems else len(histories)))
        if boundary and not problems:
            result['halves'][-1]['gameEndingBoundary'] = boundary
        if not problems:
            pa_ids = {p['atBatIndex'] for p in plays}
            reconciled = [i for i in result['boundaryIssues']
                          if i.get('code') == 'AMBIGUOUS_PA_TIME_ORDER' and i.get('atBatIndex') in pa_ids]
            if reconciled:
                result.setdefault('reconciledPaHeaderOverlaps',[]).extend(reconciled)
                result['boundaryIssues'] = [i for i in result['boundaryIssues'] if i not in reconciled]
                result['temporalOverlapDecision'] = 'archive/design-records/metric-repair-scope-2026-09-30/answers.md'
            result['histories'].extend({k: v for k, v in h.items() if k != 'base'} for h in histories)
            result['episodeMembership'].extend(memberships)
            result['placementAdjudications'].extend(dict(lifetimeKey=h['lifetimeKey'],
                runnerId=h['runnerId'], inning=h['inning'], half=h['half'], **h['placement'])
                for h in histories if h.get('placement'))
        else:
            result['withheldHistories'].append(dict(inning=inning, half=half,
                completedCandidates=[{k:v for k,v in h.items() if k!='base'} for h in histories],
                activeCandidates=list(active.values()), issues=problems))
    isolate_zero_episode_histories(result)
    verify_runner_history_correction(result, previous)
    return result


def zero_episode_replacement_witness(document: dict, play: dict, event: dict) -> bool:
    """Read a reconciled C3 replacement even when the incoming runner never moves.

    Q7 retains these witnesses while withholding the zero-episode Process.
    W1 uses only the witnessed replacement; it admits no personal history.
    """
    history = document.get(CONTEXT_KEY, {}).get('runnerHistoryReconciliation', {})
    about = play.get('about', {})
    incoming = str(event.get('player', {}).get('id', ''))
    outgoing = str(event.get('replacedPlayer', {}).get('id', ''))
    if (history.get('sourceConsistency') != 'consistent' or event.get('isSubstitution') is not True
            or event.get('position', {}).get('abbreviation') != 'PR'
            or not incoming.isdigit() or not outgoing.isdigit() or incoming == outgoing
            or str(play.get('matchup', {}).get('batter', {}).get('id')) in {incoming, outgoing}):
        return False
    anchor = f"replacement/{about.get('inning')}/{about.get('halfInning')}/{outgoing}/{incoming}"
    expected = dict(anchor=anchor, form='replacement', runnerId=incoming, outgoingRunnerId=outgoing,
        base=event.get('base'), atBatIndex=about.get('atBatIndex'), eventIndex=event.get('index'),
        earliestStartBound=event.get('startTime'), latestEndBound=event.get('endTime'))
    matches = lambda row: all(row.get(k) == v for k, v in expected.items())
    ended = [h for h in history.get('histories', []) if h.get('runnerId') == outgoing
             and h.get('terminal') == 'replaced' and h.get('terminationAnchor') == anchor
             and matches(h.get('terminationWitness', {}))]
    started = [h for half in history.get('withheldHistories', [])
               if half.get('inning') == about.get('inning') and half.get('half') == about.get('halfInning')
               and half.get('issues') and all(i.get('code') == 'ZERO_EPISODE_PERSONAL_HISTORY' for i in half['issues'])
               for h in half.get('completedCandidates', [])
               if h.get('runnerId') == incoming and h.get('entryAnchor') == anchor
               and h.get('episodes') == [] and matches(h.get('entryWitness', {}))]
    anchors = [w for w in history.get('boundaryAnchorCensus', []) if w.get('anchor') == anchor]
    return len(ended) == len(started) == len(anchors) == 1 and matches(anchors[0])


def zero_pitch_walk_terminal(play: dict, document: dict | None = None) -> int | None:
    """W1's four VB counters, with only the reviewed count-neutral prefix.

    Return the terminal source index, never a Pitch or judgment identity.
    C3 remains the owner of pinch-runner replacement reconciliation.
    """
    events = play.get('playEvents', [])
    if (play.get('result', {}).get('eventType') != 'intent_walk' or len(events) < 4
            or any(type(e.get('index')) is not int for e in events)
            or [e['index'] for e in events] != list(range(len(events)))):
        return None
    if not all(e.get('isPitch') is False and e.get('type') == 'no_pitch'
            and e.get('details', {}).get('call', {}).get('code') == 'VB'
            and e.get('details', {}).get('isBall') is True
            and e.get('details', {}).get('isStrike') is False
            and e.get('count', {}).get('balls') == n
            and e.get('count', {}).get('strikes') == 0
            and e.get('count', {}).get('outs') == play.get('count', {}).get('outs')
            for n, e in enumerate(events[-4:], 1)):
        return None
    for event in events[:-4]:
        detail = event.get('details', {})
        if (event.get('type') != 'action' or event.get('isPitch') is not False
                or event.get('count', {}).get('balls') != 0
                or event.get('count', {}).get('strikes') != 0
                or event.get('count', {}).get('outs') != play.get('count', {}).get('outs')
                or detail.get('isOut') is not False or detail.get('isScoringPlay') is not False
                or detail.get('hasReview') is not False or event.get('reviewDetails')
                or any(detail.get(k) is True for k in ('isBall', 'isStrike', 'isInPlay'))
                or any(r.get('details', {}).get('playIndex') == event['index'] for r in play.get('runners', []))):
            return None
        if detail.get('eventType') == 'mound_visit' and event.get('isSubstitution') is not True:
            continue
        if (detail.get('eventType') != 'offensive_substitution' or document is None
                or (counted_foul_neutral_event(document, play, event, (0, 0)) != 'reconciled-pinch-runner'
                    and not zero_episode_replacement_witness(document, play, event))):
            return None
    return events[-1]['index']


def intentional_walk_award_terminal(play: dict) -> int | None:
    """W3 final award counters; this does not classify the PA as zero-pitch.

    Earlier events retain their own admission and causal attribution. Only
    the final award's counter suffix and boundary are selected here.
    """
    events = play.get('playEvents', [])
    if (play.get('result', {}).get('eventType') != 'intent_walk'
            or play.get('about', {}).get('isComplete') is not True or not events
            or any(type(e.get('index')) is not int for e in events)
            or [e['index'] for e in events] != list(range(len(events)))):
        return None
    first = len(events)
    while first and events[first-1].get('details', {}).get('call', {}).get('code') == 'VB':
        first -= 1
    if not 1 <= len(events)-first <= 4:
        return None
    final = play.get('count', {})
    before = events[first-1].get('count', {}) if first else dict(balls=0, strikes=0, outs=final.get('outs'))
    if (any(type(before.get(k)) is not int or not 0 <= before[k] <= n
            for k, n in (('balls', 3), ('strikes', 2), ('outs', 2)))
            or any(type(final.get(k)) is not int for k in ('balls', 'strikes', 'outs'))
            or final != dict(balls=4, strikes=before['strikes'], outs=before['outs'])
            or len(events)-first != 4-before['balls']):
        return None
    for offset, event in enumerate(events[first:], 1):
        detail = event.get('details', {})
        count = event.get('count', {})
        if (event.get('isPitch') is not False or event.get('type') != 'no_pitch'
                or event.get('isSubstitution') is True or event.get('reviewDetails')
                or detail.get('isBall') is not True or detail.get('isStrike') is not False
                or detail.get('isInPlay') is not False or detail.get('isOut') is not False
                or detail.get('hasReview') is not False or detail.get('isScoringPlay') is True
                or any(type(count.get(k)) is not int for k in ('balls', 'strikes', 'outs'))
                or count != dict(balls=before['balls']+offset, strikes=before['strikes'], outs=before['outs'])
                or (event is not events[-1] and any(r.get('details', {}).get('playIndex') == event['index']
                        for r in play.get('runners', [])))):
            return None
    return events[-1]['index']


def defensive_indifference_evidence(play):
    """D2: reconciled independent advancement, without a stolen-base award."""
    if play.get('about',{}).get('isComplete') is not True:return []
    if accounted_runner_history_reviews(play)['issues']:return []
    index=play.get('atBatIndex');events=play.get('playEvents',[])
    if type(index) is not int:return []
    known={r['runnerIndex'] for r in runner_episode_evidence(play,str(index))['runnerEpisodes']}
    selected=[];positions={'1B':1,'2B':2,'3B':3,'score':4}
    for i,row in enumerate(play.get('runners',[])):
        d=row.get('details',{});m=row.get('movement',{});runner=d.get('runner',{}).get('id')
        if (d.get('eventType')!='defensive_indiff' or d.get('movementReason')!='r_defensive_indiff'
                or str(i) not in known or type(runner) is not int or type(d.get('playIndex')) is not int
                or m.get('isOut') is not False or m.get('start') not in {'1B','2B','3B'}
                or positions.get(m.get('end'),0)<=positions[m['start']]
                or d.get('rbi') is not False or type(d.get('isScoringEvent')) is not bool
                or d['isScoringEvent']!=(m.get('end')=='score')):continue
        matches=[e for e in events if e.get('index')==d['playIndex']]
        if len(matches)!=1:continue
        event=matches[0];detail=event.get('details',{})
        if (event.get('type')!='action' or event.get('isPitch') is not False
                or event.get('isBaseRunningPlay') is not True or event.get('isSubstitution') is True
                or event.get('player',{}).get('id')!=runner or detail.get('eventType')!='defensive_indiff'
                or detail.get('isInPlay') is True or detail.get('isOut') is True):continue
        duplicates=[r for r in play['runners'] if r.get('details',{}).get('playIndex')==d['playIndex']
                    and r.get('details',{}).get('runner',{}).get('id')==runner]
        if len(duplicates)!=1:continue
        selected.append(dict(atBatIndex=str(index),runnerIndex=str(i),runnerId=str(runner)))
    return selected


def balk_runner_evidence(play: dict, at_bat_index: str) -> list[dict]:
    """BK1: one operative nonpitch balk, joined to its explicit awarded moves.

    The event's source identity is shared by its runners. Neither the eventual
    batting result nor a descriptive label supplies the running attribution.
    """
    if not str(at_bat_index).isdigit() or play.get('about',{}).get('isComplete') is not True:
        return []
    events=play.get('playEvents',[])
    if (play.get('about',{}).get('hasReview') or play.get('reviewDetails')
            or any(e.get('reviewDetails') or e.get('details',{}).get('hasReview') for e in events)):
        if accounted_runner_history_reviews(play)['issues']:return []
    known={int(r['runnerIndex']):r for r in runner_episode_evidence(play,str(at_bat_index))['runnerEpisodes']}
    output=[]
    for event in events:
        detail=event.get('details',{});index=event.get('index');identity=event.get('actionPlayId')
        kind=detail.get('eventType')
        supported=(kind=='balk' or kind=='forced_balk' and detail.get('violation',{}).get('type')=='pitcher_disengagement')
        if (event.get('isPitch') is not False or event.get('type')!='action'
                or not supported or type(index) is not int
                or not isinstance(identity,str) or not SAFE_IRI_SEGMENT.fullmatch(identity)
                or sum(e.get('index')==index for e in events)!=1
                or sum(e.get('actionPlayId')==identity and e.get('details',{}).get('eventType')==kind
                       for e in events)!=1):continue
        rows=[(i,r) for i,r in enumerate(play.get('runners',[])) if r.get('details',{}).get('playIndex')==index]
        for i,row in rows:
            d=row.get('details',{});m=row.get('movement',{});runner=d.get('runner',{}).get('id')
            destination={'1B':'2B','2B':'3B','3B':'score'}.get(m.get('start'))
            if (i not in known or type(runner) is not int or runner<=0
                    or type(d.get('playIndex')) is not int
                    or d.get('eventType')!=kind or m.get('isOut') is not False
                    or destination is None or m.get('end')!=destination
                    or d.get('isScoringEvent') is not (destination=='score')
                    or sum(r.get('details',{}).get('runner',{}).get('id')==runner for _,r in rows)!=1):continue
            output.append(dict(known[i],actionId=identity,eventIndex=str(index)))
    return output


def runner_metric_evidence(play: dict, at_bat_index: str, season: str, *, document: dict | None = None) -> dict[str, list[dict]]:
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
    if has_review:
        reviews = accounted_runner_count_reviews(play)
        if reviews['issues']:
            final_review = accounted_runner_history_reviews(play)
            if not final_review['issues'] and (final_review.get('accountedFieldReview')
                    or result in {'walk','intent_walk','hit_by_pitch'} and final_review.get('events')):
                reviews = final_review
        if reviews['issues']:
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
        # The accepted non-pitch Ball awards can encode an intentional walk
        # as four VB records rather than one eventType=intent_walk record.
        # Require the complete counted sequence and its exact terminal join.
        automatic = (zero_pitch_walk_terminal(play, document) == index
                     or intentional_walk_award_terminal(play) == index)
        if event.get("details", {}).get("eventType") != "intent_walk" and not automatic:
            return products
    elif result == "walk" and event.get("isPitch") is False:
        # W4: the accepted Ball Judgment/Decision can complete a walk without
        # a delivered pitch. Reuse Q5's reconciled selection and exact event
        # identity; the result label alone never establishes the award.
        if document is None or event is not events[-1] or not any(
                row['atBatIndex'] == str(at_bat_index) and row['eventIndex'] == index
                and row['playId'] == event.get('playId') and row['kind'] == 'ball'
                and row['ballsBefore'] == 3 and row['ballsAfter'] == 4
                for row in automatic_count_awards(document)['automaticAwards']):
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
    parser.add_argument("--previous-defensive-evidence", type=Path)
    parser.add_argument("--previous-runner-history", type=Path)
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


def terminal_baseball_play(document: dict) -> dict:
    """Last evidenced baseball play, including a PA carrying an advisory.

    A pure administrative record cannot supply the game's physical end.
    Preserve the existing recorded boundary; do not manufacture a timestamp.
    """
    candidates = [p for p in document['liveData']['plays']['allPlays']
        if (p.get('result', {}).get('eventType') not in ADMINISTRATIVE_EVENT_TYPES
            or play_has_plate_appearance_structure(p))
        and (p.get('playEvents') or p.get('runners') or p.get('about', {}).get('isComplete') is True)]
    if not candidates or not isinstance(candidates[-1].get('about', {}).get('endTime'), str):
        raise ValueError('Last baseball play has no recorded endTime')
    return candidates[-1]


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


def pitcher_participation_context(document: dict, play: dict) -> dict:
    """P1: preserve actual pitching segments, independently of statistical assignment."""
    events=play.get('playEvents',[])
    pitches=[e for e in events if e.get('isPitch') is True]
    final=play.get('matchup',{}).get('pitcher',{}).get('id')
    changes=[(i,e) for i,e in enumerate(events) if
        e.get('details',{}).get('eventType')=='pitching_substitution'
        or (e.get('isSubstitution') is True and e.get('position',{}).get('abbreviation')=='P')]
    result=dict(pitches={},participants=[],issues=[])
    if not changes:
        result['pitches']={e['playId']:str(final) for e in pitches}
    else:
        indexes=[e.get('index') for e in events]
        if any(type(i) is not int for i in indexes) or indexes!=list(range(len(events))):
            result['issues'].append(dict(code='PITCHER_EVENT_MEMBERSHIP_OR_ORDER'))
            return result
        side='home' if play.get('about',{}).get('isTopInning') is True else 'away'
        team=document.get('liveData',{}).get('boxscore',{}).get('teams',{}).get(side,{})
        roster=team.get('players',{})
        ids=team.get('pitchers',[])
        names={pid:roster.get('ID'+str(pid),{}).get('person',{}).get('fullName') for pid in ids}
        current=final
        for i in range(len(events)-1,-1,-1):
            event=events[i]
            if event.get('isPitch') is True:result['pitches'][event['playId']]=str(current)
            if not any(position==i for position,_ in changes):continue
            incoming=event.get('player',{}).get('id')
            if (event.get('isPitch') is True or event.get('isSubstitution') is not True
                    or event.get('position',{}).get('abbreviation')!='P'
                    or incoming!=current or incoming not in ids):
                result['issues'].append(dict(code='CONFLICTING_PITCHER_REPLACEMENT',eventIndex=i))
                break
            # Before the first actual pitch, the outgoing pitcher's identity
            # is immaterial to this PA's physical pitching participation.
            if not any(e.get('isPitch') is True for e in events[:i]):break
            description=event.get('details',{}).get('description','')
            suffix=re.search(r', batting (?:1st|2nd|3rd|[4-9]th)(?:, replacing .+)?\.$',description)
            ordinary=(description[:suffix.start()] if suffix else description).rstrip('.')
            outgoing=[pid for pid in ids if pid!=incoming and names.get(pid) and names.get(incoming)
                and ordinary==f'Pitching Change: {names[incoming]} replaces {names[pid]}'.rstrip('.')]
            replaced=(event.get('replacedPlayer') or {}).get('id')
            if len(outgoing)!=1 or (not suffix and replaced is not None and replaced!=outgoing[0]):
                result['issues'].append(dict(code='UNRESOLVED_OUTGOING_PITCHER',eventIndex=i))
                break
            current=outgoing[0]
        if result['issues']:
            # A contradictory chain cannot silently fall back to the final
            # matchup. Owning SHACL refuses unsupported Pitch Act attribution.
            result['pitches']={}
    result['participants']=[dict(atBatIndex=str(play['atBatIndex']),playerId=pid)
        for pid in sorted(set(result['pitches'].values()))]
    return result


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
    # Q5: an explicitly identified initial pinch hitter can perform subsequent
    # batting acts even when the feed omits the outgoing lineup player's ID.
    # No outgoing identity or earlier act is inferred from that omission.
    initial = None
    if changes and changes[0].get('replacedPlayer', {}).get('id') is None:
        initial = changes[0]
        count = initial.get('count', {})
        if (initial is not events[0] or type(initial.get('index')) is not int or initial['index'] != 0
                or any(type(count.get(key)) is not int or count[key] != 0 for key in ('balls', 'strikes'))
                or require_numeric(initial.get('player', {}).get('id'), 'initial pinch hitter') != final
                or initial.get('reviewDetails') or initial.get('details', {}).get('hasReview') is not False):
            raise ValueError(f'PA {pa}: missing outgoing batter outside Q5 initial substitution')
    current = (final if initial is not None or not changes else
               require_numeric(changes[0]['replacedPlayer']['id'], 'replaced batter'))
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
        if event is initial:
            continue
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
        if observed or initial is not None:
            raise ValueError(f'PA {pa}: replacement has no supported batting participation')
        observed.append(final)  # Preserve the existing no-pitch PA pattern.
    if len(observed) > 1:
        if not source_consistent:
            raise ValueError(f'PA {pa}: substituted participation needs reconciled source membership')
        # Corroborate the side of every substitution on which actual pitches
        # occurred. These source bounds are not exact Batter Act intervals.
        for change in changes:
            start, end = map(instant, clock_pair(change))
            if not start or not end or start > end:
                raise ValueError(f'PA {pa}: unsupported substitution boundary')
            for event in events:
                if not (event.get('isPitch') is True or (event.get('type') == 'no_pitch' and
                        (event.get('details', {}).get('isBall') is True or event.get('details', {}).get('isStrike') is True))):
                    continue
                a, b = map(instant, clock_pair(event))
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
        bounds = [tuple(map(instant, clock_pair(e))) for e in events]
        ordered = (all(a is not None and b is not None and a <= b for a, b in bounds)
                   and all(a[1] <= b[0] for a, b in zip(bounds, bounds[1:])))
        undisputed = [bound for e, bound in zip(events, bounds) if not clock_pair_conflicted(e)]
        isolated_order = (any(clock_pair_conflicted(e) for e in events)
            and all(a is not None and b is not None and a <= b for a, b in undisputed)
            and all(a[1] <= b[0] for a, b in zip(undisputed, undisputed[1:])))
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
            elif not ordered and not isolated_order: reason = 'UNSUPPORTED_EVENT_TIME_ORDER'
            elif before is None or after is None: reason = 'INVALID_COUNTER'
            elif before[0] >= 4 or before[1] >= 3: reason = 'COUNTER_RESET_AFTER_TERMINATION'
            elif after != (before[0] + (kind == 'ball'), before[1] + (kind == 'strike')): reason = 'UNEXPLAINED_COUNTER_TRANSITION'
            if reason:
                withheld.append(dict(item, reason=reason))
                continue
            row = dict(item, kind=kind, clockOrderSupported=ordered, processIri=data+f'process/{kind}/{pid}',
                judgmentIri=data+f'judgment/{kind}/{pid}', decisionIri=data+f'decision/{kind}/{pid}',
                processClassIri=base+kind.title()+'Process', judgmentClassIri=base+kind.title()+'JudgmentAct',
                decisionClassIri=base+kind.title()+'DecisionICE', ruleIri=base+'data/rule/'+kind,
                ruleClassIri=base+kind.title()+'Rule',
                plateAppearanceIri=data+'plate-appearance/'+pa,
                recordIri=data+'event-record/count-award/'+pid,
                recordIdentifierIri=data+'event-record/count-award/'+pid+'/identifier/mlb-play-id',
                description=details.get('description', ''),
                ballsBefore=before[0], strikesBefore=before[1], ballsAfter=after[0], strikesAfter=after[1])
            for name, neighbors in ([('previousPitchIri', reversed(events[:index])), ('nextPitchIri', events[index+1:])] if ordered else []):
                neighbor = next((e for e in neighbors if e.get('isPitch') is True), None)
                if neighbor and isinstance(neighbor.get('playId'), str) and SAFE_IRI_SEGMENT.fullmatch(neighbor['playId']) and ids.count(neighbor['playId']) == 1:
                    row[name] = data+'pitch/'+neighbor['playId']
            admitted.append(row)
    document[CONTEXT_KEY]['metricAutomaticAwards'] = admitted
    return dict(automaticAwards=admitted, withheldAutomaticAwards=withheld,
                automaticAwardDecision='archive/design-records/automatic-count-awards/review.json')


def counted_foul_running_prefix(document, play, event, prior, *, check_review=True):
    """Reconcile an unchanged batting count independently of running credit."""
    detail = event.get('details',{}); events = play.get('playEvents',[])
    position = next((i for i,e in enumerate(events) if e is event), -1)
    kind = detail.get('eventType'); after = event.get('count',{})
    kinds = {'wild_pitch','passed_ball','balk','forced_balk','defensive_indiff',
             'stolen_base_2b','stolen_base_3b','stolen_base_home','caught_stealing_2b',
             'caught_stealing_3b','caught_stealing_home','pickoff_1b','pickoff_2b','pickoff_3b',
             'pickoff_error_1b','pickoff_error_2b','pickoff_error_3b',
             'pickoff_caught_stealing_2b','pickoff_caught_stealing_3b','pickoff_caught_stealing_home',
             'other_out','other_advance','error'}
    if (position <= 0 or kind not in kinds or event.get('type') != 'action'
            or event.get('isPitch') is not False or event.get('isBaseRunningPlay') is not True
            or event.get('isSubstitution') is True
            or prior != (after.get('balls'),after.get('strikes'))
            or any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))):
        return None
    before = events[position-1].get('count',{})
    rows = [(i,r) for i,r in enumerate(play.get('runners',[])) if r.get('details',{}).get('playIndex') == event.get('index')]
    if kind == 'error':
        # A supported independent error advance can leave the batting count
        # unchanged. It supplies no batting credit and no new running fact.
        if (len(rows) != 1 or type(event.get('player',{}).get('id')) is not int
                or rows[0][1].get('details',{}).get('eventType') != 'error'
                or rows[0][1]['details'].get('runner',{}).get('id') != event['player']['id']
                or rows[0][1].get('movement',{}).get('isOut') is not False
                or rows[0][1]['movement'].get('start') not in {'1B','2B','3B'}
                or rows[0][1]['movement'].get('end') not in {'1B','2B','3B'}
                or rows[0][1]['movement']['end'] <= rows[0][1]['movement']['start']):
            return None
    known = {int(r['runnerIndex']) for r in runner_episode_evidence(play,str(play['atBatIndex']))['runnerEpisodes']}
    if (not rows or any(i not in known or type(r['details'].get('isScoringEvent')) is not bool for i,r in rows)
            or any((r['details']['isScoringEvent'] is True) != (r['movement'].get('end') == 'score') for _,r in rows)
            or type(before.get('outs')) is not int or type(after.get('outs')) is not int
            or not 0 <= before['outs'] <= after['outs'] < 3
            or before.get('balls') != after['balls'] or before.get('strikes') != after['strikes']):
        return None
    movements = [(r['details']['runner']['id'],r['movement'].get('start'),r['movement'].get('end'),r['movement'].get('isOut')) for _,r in rows]
    if len(set(movements)) != len(movements): return None
    numbers = [r['movement'].get('outNumber') for _,r in rows if r['movement'].get('isOut') is True]
    if any(type(n) is not int for n in numbers) or sorted(numbers) != list(range(before['outs']+1,after['outs']+1)):
        return None
    if detail.get('isOut') is True and not numbers:return None
    if kind.startswith(('stolen_base_','caught_stealing_','pickoff_')):
        if event.get('player',{}).get('id') not in {r['details']['runner']['id'] for _,r in rows}:return None
    if check_review and (event.get('reviewDetails') or detail.get('hasReview') is True):
        if event.get('index') not in accounted_runner_history_reviews(play)['events']:return None
    if not SAFE_IRI_SEGMENT.fullmatch(str(event.get('actionPlayId') or '')):return None
    if sum(e.get('playId') == event['actionPlayId'] for e in events[:position]) != 1:return None
    return 'reconciled-running-count'


def counted_foul_initial_batter_chain(document, play):
    """Reconcile a rostered replacement chain completed before any pitch."""
    events=play.get('playEvents',[])
    pitches=[e for e in events if e.get('isPitch') is True]
    if not pitches:return set()
    first=next(i for i,e in enumerate(events) if e is pitches[0]);prefix=events[:first]
    ph=[e for e in prefix if e.get('details',{}).get('eventType')=='offensive_substitution'
        and e.get('position',{}).get('abbreviation')=='PH']
    all_ph=[e for e in events if e.get('details',{}).get('eventType')=='offensive_substitution'
        and e.get('position',{}).get('abbreviation')=='PH']
    if len(ph)<2 or len(ph)!=len(all_ph):return set()
    outs=prefix[0].get('count',{}).get('outs')
    allowed={'offensive_substitution','pitching_substitution','mound_visit'}
    if (type(outs) is not int or not 0<=outs<3
            or any(e.get('index')!=i or e.get('type')!='action' or e.get('isPitch') is not False
                or e.get('details',{}).get('eventType') not in allowed
                or e.get('count')!={'balls':0,'strikes':0,'outs':outs}
                or e.get('reviewDetails')
                or any(e.get('details',{}).get(k) is not False for k in ('hasReview','isScoringPlay','isOut'))
                or any(e.get('details',{}).get(k) is True for k in ('isBall','isStrike','isInPlay'))
                for i,e in enumerate(prefix))
            or any(r.get('details',{}).get('playIndex') in range(first) for r in play.get('runners',[]))):
        return set()
    if any(e.get('details',{}).get('eventType')=='offensive_substitution' and e not in ph for e in prefix):
        return set()
    side='away' if play.get('about',{}).get('isTopInning') is True else 'home'
    roster=document.get('liveData',{}).get('boxscore',{}).get('teams',{}).get(side,{}).get('players',{})
    previous=ph[0].get('replacedPlayer',{}).get('id');seen={previous}
    if type(previous) is not int or 'ID'+str(previous) not in roster:return set()
    for event in ph:
        incoming=event.get('player',{}).get('id')
        if (event.get('isSubstitution') is not True or event.get('replacedPlayer',{}).get('id')!=previous
                or type(incoming) is not int or incoming in seen or 'ID'+str(incoming) not in roster):
            return set()
        seen.add(incoming);previous=incoming
    if (previous!=play.get('matchup',{}).get('batter',{}).get('id')
            or any(str(e.get(CONTEXT_KEY,{}).get('batterId'))!=str(previous) for e in pitches)):
        return set()
    return {e['index'] for e in ph}


def counted_foul_neutral_event(document: dict, play: dict, event: dict, prior: tuple | None) -> str | None:
    """M3's bounded, positively reconciled non-pitch count-neutral records."""
    detail = event.get('details', {})
    count = event.get('count', {})
    events = play.get('playEvents', [])
    position = next((i for i,e in enumerate(events) if e is event), -1)
    before = events[position-1].get('count',{}) if position > 0 else dict(balls=0,strikes=0,outs=count.get('outs'))
    if prior == (before.get('balls'),before.get('strikes')) and runner_state_neutral_event(play,event,before):
        return 'reconciled-administration'
    running = counted_foul_running_prefix(document,play,event,prior)
    if running:return running
    if (event.get('isPitch') is not False or prior != (count.get('balls'), count.get('strikes'))
            or detail.get('hasReview') is not False
            or detail.get('isScoringPlay') is not False or event.get('reviewDetails')):
        return None
    kind = detail.get('eventType')
    events = play.get('playEvents', [])
    index = event.get('index')
    if kind in {'pickoff_1b','pickoff_2b','pickoff_3b'}:
        rows = [r for r in play.get('runners', []) if r.get('details', {}).get('playIndex') == index]
        attempt = [e for e in events[:index] if e.get('playId') == event.get('actionPlayId')
                   and e.get('type') == 'pickoff' and e.get('isPitch') is False]
        if len(rows) == len(attempt) == 1 and index:
            row = rows[0]; movement = row.get('movement', {}); rd = row.get('details', {})
            base = kind.rsplit('_',1)[1].upper(); previous_outs = events[index-1].get('count', {}).get('outs')
            if (detail.get('isOut') is True and event.get('isSubstitution') is not True
                    and event.get('isBaseRunningPlay') is True and rd.get('eventType') == kind
                    and type(event.get('player', {}).get('id')) is int
                    and rd.get('runner', {}).get('id') == event['player']['id']
                    and rd.get('isScoringEvent') is False and movement.get('start') == base
                    and movement.get('outBase') == base and movement.get('end') is None
                    and movement.get('isOut') is True and type(previous_outs) is int
                    and movement.get('outNumber') == count.get('outs') == previous_outs+1
                    and count['outs'] < 3):
                return 'reconciled-pickoff-out'
        return None
    if detail.get('isOut') is not False:return None
    if kind == 'runner_placed' and prior == (0,0):
        # Reuse C1's explicit adjudicative placement and exact boundary witness.
        # Placement changes occupancy, but leaves the batter's count unchanged.
        history = document.get(CONTEXT_KEY, {}).get('runnerHistoryReconciliation', {})
        about = play.get('about', {}); runner = str(event.get('player', {}).get('id', ''))
        anchor = f"placement/{about.get('inning')}/{about.get('halfInning')}/{runner}"
        expected = dict(anchor=anchor, form='placement', runnerId=runner, base=2,
            atBatIndex=about.get('atBatIndex'), eventIndex=index,
            earliestStartBound=event.get('startTime'), latestEndBound=event.get('endTime'))
        witnesses = [w for w in history.get('boundaryAnchorCensus', []) if w.get('anchor') == anchor]
        judgments = [j for j in history.get('placementAdjudications', []) if j.get('runnerId') == runner
            and str(j.get('inning')) == str(about.get('inning')) and j.get('half') == about.get('halfInning')]
        if (history.get('sourceConsistency') == 'consistent' and len(witnesses) == len(judgments) == 1
                and all(witnesses[0].get(k) == v for k,v in expected.items()) and event.get('base') == 2
                and count.get('outs') == 0 and event.get('isSubstitution') is not True
                and not any(e.get('isPitch') is True for e in events[:index])
                and not any(r.get('details', {}).get('playIndex') == index for r in play.get('runners', []))
                and not any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))):
            return 'reconciled-administration'
    if kind in {'offensive_substitution','defensive_switch','defensive_substitution'} and event.get('isSubstitution') is True:
        # Q4/Q5 already reconcile actual incoming participation. A fielding
        # switch or pre-pitch PH does not change an operative ball/strike count.
        prefix = events[:index]
        before_pitch = prior == (0,0) and not any(e.get('isPitch') is True
            or e.get('details', {}).get('call', {}).get('code') in {'VP','AC','VB'} for e in prefix)
        offense = 'away' if play.get('about', {}).get('isTopInning') is True else 'home'
        side = offense if kind == 'offensive_substitution' else ('home' if offense == 'away' else 'away')
        roster = document.get('liveData', {}).get('boxscore', {}).get('teams', {}).get(side, {}).get('players', {})
        incoming = event.get('player', {}).get('id'); outgoing = event.get('replacedPlayer', {}).get('id')
        position = event.get('position', {}).get('abbreviation')
        rostered = type(incoming) is int and 'ID'+str(incoming) in roster
        neutral = (not any(r.get('details', {}).get('playIndex') == index for r in play.get('runners', []))
            and not any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))
            and (not prefix or count.get('outs') == prefix[-1].get('count', {}).get('outs')))
        if rostered and neutral:
            if before_pitch and kind in {'defensive_switch','defensive_substitution'} and position in {'P','C','1B','2B','3B','SS','LF','CF','RF','DH'}:
                return 'initial-defensive-switch'
            if (before_pitch and kind == 'offensive_substitution' and position == 'PH'
                    and index in counted_foul_initial_batter_chain(document,play)):
                return 'initial-pinch-hitter'
            pitches = [e for e in events[index+1:] if e.get('isPitch') is True]
            if (position == 'PH' and outgoing != incoming and (outgoing is None or 'ID'+str(outgoing) in roster)
                    and incoming == play.get('matchup', {}).get('batter', {}).get('id') and pitches
                    and all(str(e.get(CONTEXT_KEY, {}).get('batterId')) == str(incoming) for e in pitches)
                    and sum(e.get('details', {}).get('eventType') == 'offensive_substitution'
                            and e.get('position', {}).get('abbreviation') == 'PH' for e in events) == 1):
                prior_pitches = [e for e in prefix if e.get('isPitch') is True]
                if before_pitch or (prior_pitches and outgoing is not None
                        and str(prior_pitches[-1].get(CONTEXT_KEY, {}).get('batterId')) == str(outgoing)):
                    return 'initial-pinch-hitter' if before_pitch else 'reconciled-pinch-hitter'
    if kind in {'stolen_base_2b', 'stolen_base_3b'} and event.get('isSubstitution') is not True:
        rows = [r for r in play.get('runners', []) if r.get('details', {}).get('playIndex') == index]
        if len(rows) != 1 or not index:
            return None
        row = rows[0]; movement = row.get('movement', {}); rd = row.get('details', {})
        before, after = ('1B', '2B') if kind == 'stolen_base_2b' else ('2B', '3B')
        if (rd.get('eventType') == kind and rd.get('runner', {}).get('id') == event.get('player', {}).get('id')
                and type(rd.get('runner', {}).get('id')) is int and rd.get('isScoringEvent') is False
                and movement.get('start') == before and movement.get('end') == after
                and movement.get('isOut') is False and movement.get('outNumber') is None
                and count.get('outs') == events[index-1].get('count', {}).get('outs')):
            return 'reconciled-steal'
    if (kind == 'offensive_substitution' and event.get('isSubstitution') is True
            and event.get('position', {}).get('abbreviation') == 'PR'):
        # C3 also retains the replacement witness when Q7 withholds the
        # incoming runner's zero-episode history. Reuse that witness, as W1
        # already does, without inventing a movement Process.
        if (zero_episode_replacement_witness(document, play, event)
                and not any(r.get('details', {}).get('playIndex') == index for r in play.get('runners', []))
                and not any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))
                and count.get('outs') == before.get('outs')):
            return 'reconciled-pinch-runner'
        # Otherwise require both accepted personal histories and their exact
        # shared replacement witness. Neither path changes the batter.
        history = document.get(CONTEXT_KEY, {}).get('runnerHistoryReconciliation', {})
        incoming = str(event.get('player', {}).get('id', ''))
        outgoing = str(event.get('replacedPlayer', {}).get('id', ''))
        about = play.get('about', {})
        anchor = f"replacement/{about.get('inning')}/{about.get('halfInning')}/{outgoing}/{incoming}"
        ended = [h for h in history.get('histories', [])
                 if h.get('terminationAnchor') == anchor and h.get('terminal') == 'replaced'
                 and h.get('runnerId') == outgoing]
        started = [h for h in history.get('histories', [])
                   if h.get('entryAnchor') == anchor and h.get('runnerId') == incoming]
        expected = dict(anchor=anchor, form='replacement', runnerId=incoming,
            outgoingRunnerId=outgoing, base=event.get('base'),
            atBatIndex=about.get('atBatIndex'), eventIndex=index,
            earliestStartBound=event.get('startTime'), latestEndBound=event.get('endTime'))
        if (history.get('sourceConsistency') == 'consistent' and len(ended) == len(started) == 1
                and all(ended[0].get('terminationWitness', {}).get(k) == v
                        and started[0].get('entryWitness', {}).get(k) == v for k,v in expected.items())
                and incoming != outgoing and incoming.isdigit() and outgoing.isdigit()
                and str(play.get('matchup', {}).get('batter', {}).get('id')) not in {incoming,outgoing}
                and not any(r.get('details', {}).get('playIndex') == index for r in play.get('runners', []))
                and not any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))):
            return 'reconciled-pinch-runner'
    if kind == 'pitching_substitution' and event.get('isSubstitution') is True:
        if (event.get('position', {}).get('abbreviation') != 'P'
                or any(e.get('details', {}).get('call', {}).get('code') in {'VP','AC','VB'} for e in events[:index])
                or sum(e.get('details', {}).get('eventType') == kind for e in events) != 1):
            return None
        team = 'home' if play.get('about', {}).get('isTopInning') is True else 'away'
        roster = document.get('liveData', {}).get('boxscore', {}).get('teams', {}).get(team, {})
        pitchers = roster.get('pitchers', [])
        people = document.get('gameData', {}).get('players', {})
        incoming = event.get('player', {}).get('id')
        names = {pid: people.get('ID'+str(pid), {}).get('fullName') for pid in pitchers}
        # Some feeds identify the outgoing pitcher only in the final narrative.
        # Require an exact unique pair of rostered people, never a fuzzy name.
        description = detail.get('description', '')
        # Suffix punctuation belongs to the person's name. A batting-order
        # suffix also leaves the pitch count unchanged.
        batting = re.search(r', batting (1st|2nd|3rd|[4-9]th)(?:, replacing '
            r'(?:pitcher|catcher|first baseman|second baseman|third baseman|shortstop|left fielder|center fielder|right fielder|designated hitter) (.+))?\.$',description)
        ordinary = (description[:batting.start()] if batting else description).rstrip('.')
        pairs = [(a,b) for a in pitchers for b in pitchers if a != b and names[a] and names[b]
                 and ordinary == f'Pitching Change: {names[a]} replaces {names[b]}'.rstrip('.')]
        leaving = event.get('replacedPlayer', {}).get('id')
        players = roster.get('players', {})
        outgoing_name = people.get('ID'+str(leaving), {}).get('fullName')
        lineup = bool(incoming in pitchers and names.get(incoming) and outgoing_name
            and 'ID'+str(leaving) in players and re.fullmatch(
                r'Pitcher '+re.escape(names[incoming])+r' enters the batting order, batting (?:1st|2nd|3rd|[4-9]th), '
                r'(?:pitcher|catcher|first baseman|second baseman|third baseman|shortstop|left fielder|center fielder|right fielder|designated hitter) '
                +re.escape(outgoing_name)+r' leaves the game\.', description))
        order=str(event.get('battingOrder') or '')
        batting_replacement=bool(batting and re.fullmatch(r'[1-9][0-9]{2}',order)
            and order[0]==batting.group(1)[0] and 'ID'+str(leaving) in players
            and (batting.group(2) is None or batting.group(2)==outgoing_name))
        # A batting-slot replacement and the outgoing pitcher are distinct joins.
        # Both must be evidenced; this selects later fouls, not new participants.
        prior_pitches=[e for e in events[:index] if e.get('isPitch') is True]
        supported_start=prior==(0,0) if not prior_pitches else bool(
            len(pairs)==1 and not lineup and not batting and prior is not None
            and 0<=prior[0]<4 and 0<=prior[1]<3)
        subsequent = [e for e in events[index+1:] if e.get('isPitch') is True]
        if (supported_start and ((len(pairs) == 1 and pairs[0][0] == incoming) or lineup) and subsequent
                and play.get('matchup', {}).get('pitcher', {}).get('id') == incoming
                and all(str(e.get(CONTEXT_KEY, {}).get('pitcherId')) == str(incoming) for e in subsequent)
                and not any(r.get('details', {}).get('playIndex') == index for r in play.get('runners', []))
                and not any(detail.get(k) is True for k in ('isBall','isStrike','isInPlay'))
                and count.get('outs') == before.get('outs')
                and (lineup or batting_replacement or event.get('replacedPlayer') is None or event['replacedPlayer'].get('id') == pairs[0][1])):
            return 'reconciled-pitching-change' if prior_pitches else 'initial-pitching-change'
    return None


def metric_pitch_context(document: dict) -> dict:
    """Accepted M1-M4 source selection; graph semantics belong to RML/SHACL.

    Inspect unfiltered event prefixes. Counters are mapping evidence, not new
    RDF count states. The retained inventory also checks exact serialization.
    """
    game = str(document['gamePk'])
    data = f'https://baseballontology.org/data/game/{game}/'
    base = 'https://baseballontology.org/'
    evidence = dict(decision='archive/design-records/mlb-game-metric-mapping-completion/review.json',
                    countedFouls=[], withheldFouls=[], pitchReviews=[], withheldReviews=[], prefixInventory=[],
                    countedFoulCompletionDecision='archive/design-records/mlb-game-counted-foul-completion/review.json')
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
        reviews = accounted_runner_history_reviews(play)
        field_review = reviews.get('accountedFieldReview')
        prefix_problem = None
        if source['sourceConsistency'] != 'consistent':
            prefix_problem = 'SOURCE_RECONCILIATION_FAILED'
        elif play['about'].get('isComplete') is not True:
            prefix_problem = 'INCOMPLETE_PA'
        elif any(type(i) is not int for i in indexes) or indexes != list(range(len(events))):
            prefix_problem = 'EVENT_MEMBERSHIP_OR_ORDER'
        elif reviews['issues']:
            prefix_problem = 'UNRESOLVED_PA_REVIEW'
        previous = None
        previous_extension = None
        previous_pitch_end = None
        prior = (0, 0)
        has_batting_substitution = any(e.get('details', {}).get('eventType') == 'offensive_substitution' for e in events)
        for event in events:
            details = event.get('details', {})
            code = details.get('call', {}).get('code')
            after = counts(event)
            neutral_extension = counted_foul_neutral_event(document, play, event, prior)
            start, end = map(instant, clock_pair(event))
            # Reconciled count-neutral records can overlap their surrounding
            # temporal regions (September 30). Actual pitches still need their
            # observed order; no clocks or BFO precedence assertions are changed.
            overlap = previous and instant(clock_pair(previous)[1]) and start and instant(clock_pair(previous)[1]) > start
            initial_changes = {'initial-pitching-change','reconciled-pitching-change','initial-pinch-hitter','initial-defensive-switch',
                               'reconciled-administration','reconciled-running-count','reconciled-pinch-runner','reconciled-pinch-hitter'}
            if (not start or not end or end < start or (overlap and not ({neutral_extension,previous_extension} & initial_changes))
                    or (event.get('isPitch') is True and previous_pitch_end and start and previous_pitch_end > start)):
                prefix_problem = prefix_problem or 'UNSUPPORTED_EVENT_TIME_ORDER'
            if event.get('isPitch') is True:previous_pitch_end = end
            if field_review and event.get('index') >= field_review['eventIndex']:
                prefix_problem = prefix_problem or 'FIELD_REVIEW_IN_PREFIX'
            if (event.get('reviewDetails') or details.get('hasReview') is True) and event.get('index') not in reviews['events']:
                prefix_problem = prefix_problem or 'UNRESOLVED_PREFIX_REVIEW'
            if (event.get('isSubstitution') is True or 'substitution' in str(details.get('eventType', ''))) and neutral_extension not in {'initial-pitching-change','reconciled-pitching-change','reconciled-pinch-runner','initial-pinch-hitter','reconciled-pinch-hitter','initial-defensive-switch','reconciled-administration'}:
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
                    neutral = bool(neutral_extension) or event.get('type') in {'pickoff', 'stepoff', 'no_pitch'}
                    if (pa, event.get('playId')) in automatic_ids:
                        expected = (balls + (code == 'VP'), strikes + (code == 'AC'))
                    else:
                        expected = prior if neutral else None
                if expected is None or expected != after:
                    prefix_problem = prefix_problem or 'UNEXPLAINED_COUNTER_TRANSITION'
            evidence['prefixInventory'].append(dict(atBatIndex=pa, eventIndex=event.get('index'),
                playId=event.get('playId'), call=code, before=prior, after=after,
                accountedExtension=neutral_extension or ('operative-pitch-review' if event.get('index') in reviews['events'] else None),
                problem=prefix_problem))
            if event.get('isPitch') is not True:
                previous, prior, previous_extension = event, after, neutral_extension
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
            ec['isCountedFoulBunt'] = False
            if code == 'F' and after and after[1] == 2:
                item = dict(atBatIndex=pa, playId=pid, eventIndex=event.get('index'))
                if (prefix_problem is None and previous is not None and prior == (after[0], 1) and ec['isBuntAttempt'] is False
                        and details.get('isStrike') is True and details.get('isBall') is False and details.get('isInPlay') is False):
                    ec['isSecondCountedFoul'] = True
                    evidence['countedFouls'].append(item)
                else:
                    evidence['withheldFouls'].append(dict(item, reason=('NO_SECOND_STRIKE_INCREMENT'
                        if prior is not None and prior[1] == after[1] else prefix_problem or 'NO_SECOND_STRIKE_INCREMENT')))
            if code == 'L':
                item = dict(atBatIndex=pa, playId=pid, eventIndex=event.get('index'), kind='foul-bunt')
                third = after is not None and after[1] == 3
                terminal = (event is pitches[-1] and play.get('result', {}).get('eventType') in {'strikeout','strikeout_double_play'}
                            and pc.get('terminalPitchPlayId') == pid)
                if (prefix_problem is None and prior is not None and after == (prior[0], prior[1]+1)
                        and ec.get('isBuntAttempt') is True and ec.get('matchesBuntContactSource') is True
                        and details.get('isStrike') is True and details.get('isBall') is False and details.get('isInPlay') is False
                        and ec.get('batterId') and ec.get('pitcherId') and (not third or terminal)):
                    ec['isCountedFoulBunt'] = True
                    evidence['countedFouls'].append(item)
                else:
                    evidence['withheldFouls'].append(dict(item, reason=prefix_problem or 'UNSUPPORTED_COUNTED_FOUL_BUNT'))

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
            previous, prior, previous_extension = event, after, neutral_extension
    root['metricPitchReviews'] = rows
    root['metricMappingEvidence'] = evidence
    return evidence


def defensive_act_context(document: dict, previous: dict | None = None) -> dict:
    """D1 particular performances, with witnesses and a separate play census.

    A credit is corroboration, never a stand-alone act. Sequence indices only
    serialize identity: these narrative patterns assert no strict precedence.
    """
    base = 'https://baseballontology.org/'
    game = base+f"data/game/{document['gamePk']}/"
    plays = document['liveData']['plays']['allPlays']
    ids = [e.get('playId') for p in plays for e in p.get('playEvents', []) if e.get('playId')]
    position = r'(?:pitcher|catcher|first baseman|second baseman|third baseman|shortstop|left fielder|center fielder|right fielder) '

    def normalized(text):
        return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).casefold().split()).rstrip('.')

    people = document.get('gameData', {}).get('players', {})
    rows, inventory = [], []
    source = document[CONTEXT_KEY]['runnerHistoryReconciliation']
    scope_path = Path(__file__).resolve().parents[2] / 'sources/mlb-game/pipeline/graph-source-scope.py'
    spec = importlib.util.spec_from_file_location('defensive_graph_scope', scope_path)
    scope = importlib.util.module_from_spec(spec); spec.loader.exec_module(scope)
    source_complete = source.get('sourceConsistency') == 'consistent'
    issues = source.get('sourceIssues', [])
    graph_source_reconciled = source_complete or (bool(issues) and not scope.graph_blocking_issues(issues))
    for play in plays:
        pa = str(play['about']['atBatIndex'])
        events = play.get('playEvents', [])
        contacts = [e for e in events if e.get('isPitch') is True and e.get('details', {}).get('call', {}).get('code') in {'F','T','L','O','X','D','E'}]
        terminal = events[-1] if events else None
        defending = 'home' if play.get('about', {}).get('isTopInning') is True else 'away'
        roster = document.get('liveData', {}).get('boxscore', {}).get('teams', {}).get(defending, {}).get('players', {})
        names = defaultdict(set); spellings = set()
        for key, person in roster.items():
            identity = person.get('person', {}).get('id')
            if type(identity) is int and key == 'ID'+str(identity):
                for name in (person.get('person', {}).get('fullName'), people.get(key, {}).get('fullName')):
                    if isinstance(name, str):
                        names[normalized(name)].add(str(identity))
                        spellings.update([name.rstrip('.'), ''.join(c for c in unicodedata.normalize('NFKD', name)
                            if not unicodedata.combining(c)).rstrip('.')])
        named_fielder = position + r'(?:' + '|'.join(re.escape(n) + r'\.?' for n in sorted(spellings,key=lambda n:(-len(n),n))) + ')'

        def resolve(mention):
            name = re.sub('^'+position, '', mention, flags=re.I)
            matches = names.get(normalized(name), set())
            return next(iter(matches)) if len(matches) == 1 else None

        description = play.get('result', {}).get('description', '')
        description_offset = 0
        reviewed_final = False
        if play.get('reviewDetails') or play['about'].get('hasReview') is True:
            reviewed = accounted_runner_history_reviews(play)
            reviewed_final = not reviewed['issues'] and bool(reviewed.get('accountedFieldReview'))
            if reviewed_final:
                while (review_match := REVIEW_DESCRIPTION.search(description)):
                    remaining = description[review_match.end():]
                    description_offset += review_match.end() + len(remaining) - len(remaining.lstrip())
                    description = remaining.lstrip()
        for event in contacts:
            pid = event.get('playId')
            item = dict(atBatIndex=pa, eventIndex=event.get('index'), playId=pid,
                resolution=game+'process/batted-ball-play/'+str(pid), acts=[],
                complete=False, orderComplete=False, gaps=[])
            inventory.append(item)
            if (not graph_source_reconciled or play['about'].get('isComplete') is not True
                    or not isinstance(pid, str) or not SAFE_IRI_SEGMENT.fullmatch(pid) or ids.count(pid) != 1
                    or [e.get('index') for e in events] != list(range(len(events)))):
                item['gaps'].append('UNRECONCILED_CONTACT_IDENTITY'); continue
            if (event is not terminal or ((play.get('reviewDetails') or play['about'].get('hasReview') is not False) and not reviewed_final)
                    or event.get('reviewDetails') or event.get('details', {}).get('hasReview') is not False):
                item['gaps'].append('UNRESOLVED_DEFENSIVE_DESCRIPTION'); continue
            associated = [(i,r) for i,r in enumerate(play.get('runners', [])) if r.get('details', {}).get('playIndex') == event['index']]
            credits = [(i,j,c) for i,r in associated for j,c in enumerate(r.get('credits', []))]

            def witnesses(player, kinds):
                return [f'/liveData/plays/allPlays/{pa}/runners/{i}/credits/{j}' for i,j,c in credits
                        if str(c.get('player', {}).get('id')) == player and c.get('credit') in kinds]

            selected = []
            def select(kind, agent, span, support):
                selected.append(dict(kind=kind, agent=agent, span=[n+description_offset for n in span], creditPointers=support))

            catch = re.match(r'.+? (?:flies|lines|pops) out(?: (?:sharply|softly))? to ('+named_fielder+r')(?: in foul territory)?\.', description, re.I)
            if catch and play.get('result', {}).get('eventType') == 'field_out':
                agent = resolve(catch.group(1)); support = witnesses(agent, {'f_putout'}) if agent else []
                outs = [r for _,r in associated if r.get('movement', {}).get('isOut') is True]
                conflicting = [c for _,_,c in credits if str(c.get('player', {}).get('id')) != agent or c.get('credit') != 'f_putout']
                if (agent and support and len(outs) == 1 and not conflicting
                        and outs[0].get('details', {}).get('runner', {}).get('id') == play.get('matchup', {}).get('batter', {}).get('id')):
                    select('CatchAttemptAct',agent,[catch.start(),catch.end()],support)
                    item['complete'] = len(associated) == 1 and catch.end() == len(description)
            # The explicit "on the throw" supplies a described relay. Credits
            # corroborate the participants; they do not create extra throws.
            relay = re.search(r'(?P<runner>[^.]+?) out at (?P<base>2nd|3rd|home) on the throw, (?P<chain>.+)\.$', description)
            if not selected and relay:
                mentions = relay.group('chain').split(' to ')
                agents = [resolve(m) if re.match('^'+position,m) else None for m in mentions]
                out_base = {'2nd':'2B','3rd':'3B','home':'4B'}[relay.group('base')]
                outs = [r for _,r in associated if r.get('movement', {}).get('isOut') is True
                        and r.get('movement', {}).get('outBase') in ({out_base,'HP'} if out_base=='4B' else {out_base})
                        and normalized(r.get('details', {}).get('runner', {}).get('fullName','')) == normalized(relay.group('runner'))]
                if (len(agents) >= 2 and all(agents) and len(outs) == 1
                        and witnesses(agents[0],{'f_fielded_ball'}) and witnesses(agents[-1],{'f_putout'})
                        and all(witnesses(a,{'f_assist','f_assist_of'}) for a in agents[:-1])):
                    span=[relay.start(),relay.end()]
                    select('FieldingAttemptAct',agents[0],span,witnesses(agents[0],{'f_fielded_ball'}))
                    for index,agent in enumerate(agents):
                        if index:
                            select('CatchAttemptAct',agent,span,witnesses(agent,{'f_assist','f_assist_of','f_putout'}))
                        if index < len(agents)-1:
                            select('ThrowAct',agent,span,witnesses(agent,{'f_assist','f_assist_of'}))
                    item['gaps'].append('RELAY_TERMINAL_TOUCH_AND_ORDER_UNRESOLVED')
            # D1 also accepts the provider's compact named groundout sentence
            # (822693 PA 2), with exactly the described assist and first-base
            # putout. Bare credits, extra deflectors and unassisted outs do not
            # satisfy that pattern. Terminal touch and timing remain unresolved.
            ground = re.search(r'('+position+r'.+?) fields (?:the )?(?:ground ball|grounder) and throws to ('+position+r'.+?), who catches the (?:ball|throw)\.', description, re.I)
            compact = re.match(r'.+? grounds out(?: (?:sharply|softly))?, ('+named_fielder+r') to ('+named_fielder+r')\.',description,re.I)
            if not ground and compact and play.get('result',{}).get('eventType')=='field_out':
                first,last=resolve(compact.group(1)),resolve(compact.group(2))
                outs=[r for _,r in associated if r.get('movement',{}).get('isOut') is True]
                allowed={(first,'f_assist'),(last,'f_putout')}
                if (first and last and first!=last and len(outs)==1
                        and outs[0].get('details',{}).get('runner',{}).get('id')==play.get('matchup',{}).get('batter',{}).get('id')
                        and outs[0].get('movement',{}).get('outBase')=='1B'
                        and witnesses(first,{'f_assist'}) and witnesses(last,{'f_putout'})
                        and all((str(c.get('player',{}).get('id')),c.get('credit')) in allowed for _,_,c in credits)):
                    ground=compact
            if not selected and ground:
                first,last = resolve(ground.group(1)),resolve(ground.group(2))
                if (first and last and first != last and witnesses(first,{'f_fielded_ball','f_assist'})
                        and witnesses(last,{'f_putout'}) and any(r.get('movement',{}).get('isOut') is True for _,r in associated)):
                    span=[ground.start(),ground.end()]
                    select('FieldingAttemptAct',first,span,witnesses(first,{'f_fielded_ball','f_assist'}))
                    select('ThrowAct',first,span,witnesses(first,{'f_assist'}))
                    select('CatchAttemptAct',last,span,witnesses(last,{'f_putout'}))
                    item['gaps'].append('GROUNDOUT_TERMINAL_TOUCH_AND_ORDER_UNRESOLVED')
            # Intentional tagging needs an explicit named act and out/base witness.
            # A bare putout, including a relay's last credit, never supplies it.
            if not selected:
                tag = re.search(r'('+position+r'.+?) tags (.+?) out at (first|second|third|home)(?: base| plate)?\.',description,re.I)
                if tag:
                    agent=resolve(tag.group(1)); base_name={'first':'1B','second':'2B','third':'3B','home':'4B'}[tag.group(3).lower()]
                    outs=[r for _,r in associated if r.get('movement',{}).get('isOut') is True
                          and r['movement'].get('outBase') in ({base_name,'HP'} if base_name=='4B' else {base_name})
                          and normalized(r.get('details',{}).get('runner',{}).get('fullName','')) == normalized(tag.group(2))]
                    if agent and len(outs)==1 and witnesses(agent,{'f_putout'}):
                        select('TagAttemptAct',agent,[tag.start(),tag.end()],witnesses(agent,{'f_putout'}))
            for number,act in enumerate(selected,1):
                row=dict(actIri=game+f'act/defense/{pid}/{number}',classIri=base+act['kind'],
                    agentIri=base+'data/player/'+act['agent'],roleIri=base+'data/player/'+act['agent']+'/role/fielder',
                    playIri=item['resolution'],recordIri=game+'event-record/pitch/'+pid,
                    catch=act['kind']=='CatchAttemptAct',atBatIndex=pa,playId=pid,performanceIndex=number,
                    descriptionPointer=f'/liveData/plays/allPlays/{pa}/result/description',
                    descriptionSpan=act['span'],description=play['result']['description'],creditPointers=act['creditPointers'])
                rows.append(row);item['acts'].append(row['actIri'])
            item['orderComplete'] = item['complete'] and len(selected)==1
            if not item['complete'] and not item['gaps']:item['gaps'].append('INCOMPLETE_DEFENSIVE_PERFORMANCES')
    # Corrections may retain already aligned performances, never silently
    # reassign a serialized position to another performance.
    if previous:
        if str(previous.get('gamePk')) != str(document['gamePk']):raise ValueError('D1 prior evidence game mismatch')
        signatures=lambda values:{r['actIri']:(r['classIri'],r['agentIri']) for r in values}
        old=signatures(previous.get('acts',[]));new=signatures(rows)
        for iri,signature in old.items():
            if new.get(iri)!=signature:raise ValueError('D1 correction has ambiguous performance alignment: '+iri)
        old_by_play=defaultdict(list);new_by_play=defaultdict(list)
        for r in previous.get('acts',[]):old_by_play[r['playId']].append(r['actIri'])
        for r in rows:new_by_play[r['playId']].append(r['actIri'])
        for pid,acts in old_by_play.items():
            if new_by_play[pid]!=acts:raise ValueError('D1 correction changes an established performance census: '+pid)
    result=dict(gamePk=str(document['gamePk']),decision='archive/design-records/mlb-game-defensive-acts/review.json',
        inputSha256=source.get('inputSha256'),sourceRevision=source.get('sourceRevision'),acts=rows,plays=inventory,
        populationComplete=source_complete and bool(inventory) and all(r['complete'] for r in inventory),
        orderComplete=source_complete and bool(inventory) and all(r['orderComplete'] for r in inventory),
        precedence=[],identityAlignmentChecked=previous is not None)
    document[CONTEXT_KEY]['defensiveActs']=rows
    document[CONTEXT_KEY]['defensiveEvidence']=result
    return result


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
    terminal_play = terminal_baseball_play(document)
    final_end_time = terminal_play['about']['endTime']
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
    previous_runner_history = None
    if args.previous_runner_history:
        previous_manifest = json.loads(args.previous_runner_history.read_text(encoding='utf-8-sig'))
        if str(previous_manifest.get('gamePk')) != game_pk:
            raise ValueError('C3 prior runner-history game mismatch')
        previous_runner_history = previous_manifest.get('runnerHistoryReconciliation')
    root_context: dict[str, object] = {
        "runnerHistoryReconciliation": personal_runner_histories(args.source.read_bytes(), previous_runner_history),
        "gameEndTime": clock_pair(terminal_play["about"])[1],
        "gameEndClockConflicted": clock_pair_conflicted(terminal_play["about"]),
        "gameEndClocks": [] if clock_pair_conflicted(terminal_play["about"]) else [{"value": final_end_time}],
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
    pitcher_role_ids: set[str] = set()
    root_context['pitcherParticipationIssues'] = []
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
            # A placement's base is an administrative destination, not an
            # observation of physical occupancy at the start of this PA.
            # Its adjudication and history come from personal_runner_histories.

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
            **runner_metric_evidence(play, at_bat_index, season, document=document),
            "balkAdvances": balk_runner_evidence(play, at_bat_index),
            "defensiveIndifferenceActs": defensive_indifference_evidence(play),
            "hasPlateAppearanceStructure": has_plate_appearance_structure,
            "hasPlateAppearanceClocks": has_plate_appearance_structure and not clock_pair_conflicted(about),
            "hasCompletedPlateAppearanceResult": has_completed_plate_appearance_result,
            "hasReview": False,
            "hasReviewStatus": False,
            "hasReviewChallengerId": False,
        }
        batting_context = batter_participation_context(play, game_pk,
            source_consistent=root_context['runnerHistoryReconciliation']['sourceConsistency'] == 'consistent')
        play_context['batterParticipations'] = batting_context['participations'] if has_plate_appearance_structure else []
        pitching_context = pitcher_participation_context(document, play)
        play_context['pitcherParticipations'] = pitching_context['participants'] if has_plate_appearance_structure else []
        pitcher_role_ids.update(pitching_context['pitches'].values())
        if has_plate_appearance_structure: pitcher_role_ids.add(pitcher_id)
        root_context['pitcherParticipationIssues'].extend(
            dict(atBatIndex=at_bat_index,**issue) for issue in pitching_context['issues'])
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
                **({'pitcherId': pitching_context['pitches'][play_id]}
                   if play_id in pitching_context['pitches'] else {}),
                "isBuntAttempt": is_bunt_attempt,
                "hasClockPair": not clock_pair_conflicted(event),
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

    root_context['pitcherRoleBearers'] = [dict(playerId=pid) for pid in sorted(pitcher_role_ids)]
    metric_pitch_context(document)
    root_context['compoundDoublePlayParts'] = [part for play in plays for part in compound_double_play_parts(play)]
    previous_defense = None
    if args.previous_defensive_evidence:
        previous_manifest = json.loads(args.previous_defensive_evidence.read_text(encoding='utf-8-sig'))
        previous_defense = previous_manifest.get('defensiveEvidence')
    defensive_act_context(document, previous_defense)
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
