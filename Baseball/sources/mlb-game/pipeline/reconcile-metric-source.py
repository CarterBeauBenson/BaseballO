"""Retain a revision-bound source inventory before NiFi removes transient input.

Mechanical source consistency only. This does not admit exhaustive histories,
interpret omitted movements, create RDF, or compute metrics from raw JSON.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile


VERSION = 1


def digest(value):
    return hashlib.sha256(value).hexdigest()


def reconcile(raw: bytes, game_pk: str):
    doc = json.loads(raw)
    if str(doc.get('gamePk')) != game_pk:
        raise ValueError('Source game identity differs from requested game')
    root = doc.get('liveData', {}).get('plays', {})
    plays = root.get('allPlays')
    if not isinstance(plays, list) or not plays:
        raise ValueError('Missing unfiltered allPlays source collection')
    issues, inventory = [], []

    def issue(code, path, **detail):
        issues.append(dict(code=code, path=path, **detail))

    def integer(value):
        return type(value) is int and value >= 0

    def indexes(values, path):
        if not isinstance(values, list) or any(not integer(v) for v in values):
            issue('INVALID_INDEX_COLLECTION', path)
            return []
        if len(set(values)) != len(values):
            issue('DUPLICATE_INDEX', path)
        return values

    def timestamp(value):
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed if parsed.tzinfo is not None else None
        except ValueError:
            return None

    if doc.get('gameData', {}).get('status', {}).get('abstractGameState') != 'Final':
        issue('GAME_NOT_FINAL', '/gameData/status/abstractGameState')
    revision = doc.get('metaData', {}).get('timeStamp')
    if not isinstance(revision, str) or not revision:
        issue('MISSING_SOURCE_REVISION', '/metaData/timeStamp')

    pa_ids, half_members = [], defaultdict(list)
    scoring_ids, scoring_by_half = [], Counter()
    for position, play in enumerate(plays):
        path = f'/liveData/plays/allPlays/{position}'
        about = play.get('about', {})
        pa = play.get('atBatIndex')
        if not integer(pa) or about.get('atBatIndex') != pa:
            issue('AMBIGUOUS_PA_INDEX', path)
        pa_ids.append(pa)
        inning, half = about.get('inning'), about.get('halfInning')
        if not integer(inning) or inning == 0 or half not in ('top', 'bottom'):
            issue('INVALID_HALF_INNING', path + '/about')
        half_members[(inning, half)].append(pa)
        if about.get('isComplete') is not True:
            issue('INCOMPLETE_SOURCE_PLAY', path + '/about/isComplete')
        for field in ('startTime', 'endTime'):
            if timestamp(about.get(field)) is None:
                issue('UNSUPPORTED_PLAY_TIME', path + '/about/' + field)
        start, end = timestamp(about.get('startTime')), timestamp(about.get('endTime'))
        if start and end and end < start:
            issue('REVERSED_PLAY_TIMES', path + '/about')

        events = play.get('playEvents')
        if not isinstance(events, list):
            issue('MISSING_EVENT_COLLECTION', path + '/playEvents'); events = []
        event_ids = [event.get('index') for event in events]
        indexes(event_ids, path + '/playEvents/index')
        event_counts = Counter(event_ids)
        pitch_ids = [event.get('index') for event in events if event.get('isPitch') is True]
        pitch_indexes = indexes(play.get('pitchIndex'), path + '/pitchIndex')
        # The real feed includes pickoffs, step-offs and no-pitch entries in
        # pitchIndex. Validate membership, never count this list as pitches.
        if (any(event_counts[index] != 1 for index in pitch_indexes)
                or any(index not in pitch_indexes for index in pitch_ids)):
            issue('PITCH_MEMBERSHIP_MISMATCH', path + '/pitchIndex')
        actions = indexes(play.get('actionIndex'), path + '/actionIndex')
        if any(event_counts[index] != 1 for index in actions):
            issue('DANGLING_ACTION_INDEX', path + '/actionIndex')
        event_rows = []
        for event_position, event in enumerate(events):
            event_path = path + f'/playEvents/{event_position}'
            event_start, event_end = timestamp(event.get('startTime')), timestamp(event.get('endTime'))
            if event_start and event_end and event_end < event_start:
                issue('REVERSED_EVENT_TIMES', event_path)
            event_rows.append(dict(sourcePosition=event_position, index=event.get('index'),
                playId=event.get('playId'), type=event.get('type'), isPitch=event.get('isPitch'),
                eventType=event.get('details', {}).get('eventType'),
                startTime=event.get('startTime'), endTime=event.get('endTime'),
                count=event.get('count'), reviewDetails=event.get('reviewDetails'),
                sourceSha256=digest(json.dumps(event, sort_keys=True, separators=(',', ':')).encode())))
        movements = play.get('runners')
        if not isinstance(movements, list):
            issue('MISSING_MOVEMENT_COLLECTION', path + '/runners'); movements = []
        movement_rows, scored = [], 0
        for row_position, row in enumerate(movements):
            row_path = path + f'/runners/{row_position}'
            details, movement = row.get('details', {}), row.get('movement', {})
            index = details.get('playIndex')
            if not integer(index) or event_counts[index] != 1:
                issue('MOVEMENT_EVENT_MEMBERSHIP_MISMATCH', row_path, playIndex=index)
            runner = details.get('runner', {}).get('id')
            if not integer(runner) or runner == 0:
                issue('MISSING_RUNNER_IDENTITY', row_path)
            if type(details.get('isScoringEvent')) is not bool:
                issue('UNKNOWN_SCORING_FLAG', row_path)
            scored += details.get('isScoringEvent') is True
            movement_rows.append(dict(sourcePosition=row_position, playIndex=index, runnerId=runner,
                movement=movement, eventType=details.get('eventType'),
                isScoringEvent=details.get('isScoringEvent'),
                sourceSha256=digest(json.dumps(row, sort_keys=True, separators=(',', ':')).encode())))
        is_scoring = about.get('isScoringPlay')
        scoring_event_ids = {event.get('index') for event in events
                             if event.get('details', {}).get('isScoringPlay') is True}
        scoring_movement_ids = {row['playIndex'] for row in movement_rows if row['isScoringEvent'] is True}
        # A run on an earlier event (for example a passed ball before a
        # groundout) may have an event scoring flag while the PA result's
        # header flag is false. Reconcile that explicit event/runner evidence
        # with scoringPlays and the inning totals; do not drop the run or turn
        # it into a positive batting consequence.
        supported_event_scores = bool(scored) and scoring_movement_ids <= scoring_event_ids
        if (type(is_scoring) is not bool or is_scoring and not scored
                or is_scoring is False and scored and not supported_event_scores):
            issue('SCORING_MEMBERSHIP_MISMATCH', path)
        if not scoring_event_ids <= scoring_movement_ids:
            issue('SCORING_EVENT_MEMBERSHIP_MISMATCH', path)
        if scored:
            scoring_ids.append(pa)
        scoring_by_half[(inning, half)] += scored
        inventory.append(dict(sourcePosition=position, atBatIndex=pa, inning=inning, half=half,
            startTime=about.get('startTime'), endTime=about.get('endTime'),
            hasReview=about.get('hasReview'), reviewDetails=play.get('reviewDetails'),
            paCount=play.get('count'), pitchIndex=pitch_indexes, actionIndex=actions,
            events=event_rows, movements=movement_rows,
            postBaseObservations={key: play.get('matchup', {}).get(key) for key in
                                  ('postOnFirst', 'postOnSecond', 'postOnThird')
                                  if key in play.get('matchup', {})}))
    indexes(pa_ids, '/liveData/plays/allPlays/atBatIndex')
    by_inning = root.get('playsByInning')
    reported_members = defaultdict(list)
    if not isinstance(by_inning, list):
        issue('MISSING_INNING_MEMBERSHIP', '/liveData/plays/playsByInning')
    else:
        for i, row in enumerate(by_inning):
            for half in ('top', 'bottom'):
                reported_members[(i + 1, half)] = indexes(row.get(half), f'/liveData/plays/playsByInning/{i}/{half}')
        for key in set(half_members) | set(reported_members):
            # A defaultdict lookup would insert an unplayed bottom half into
            # the observed census. Preserve absence for the linescore check.
            if Counter(half_members.get(key, [])) != Counter(reported_members.get(key, [])):
                issue('INNING_MEMBERSHIP_MISMATCH', '/liveData/plays/playsByInning', inning=key[0], half=key[1])
    if Counter(indexes(root.get('scoringPlays'), '/liveData/plays/scoringPlays')) != Counter(scoring_ids):
        issue('SCORING_INDEX_MISMATCH', '/liveData/plays/scoringPlays')

    linescore = doc.get('liveData', {}).get('linescore', {})
    innings = linescore.get('innings')
    line_totals = Counter()
    line_keys = set()
    if not isinstance(innings, list) or not innings:
        issue('MISSING_LINESCORE_INNINGS', '/liveData/linescore/innings'); innings = []
    for position, inning in enumerate(innings):
        for side, half in [('away', 'top'), ('home', 'bottom')]:
            key = (inning.get('num'), half)
            runs = inning.get(side, {}).get('runs')
            # An unplayed bottom half is not invented as an observed zero.
            if runs is None and key not in half_members:
                continue
            if key in line_keys:
                issue('DUPLICATE_LINESCORE_HALF', f'/liveData/linescore/innings/{position}')
            line_keys.add(key)
            if not integer(runs) or runs != scoring_by_half[key]:
                issue('INNING_RUN_TOTAL_MISMATCH', f'/liveData/linescore/innings/{position}/{side}',
                      reported=runs, observedScoringRows=scoring_by_half[key])
            if integer(runs):
                line_totals[side] += runs
    for key in half_members:
        if key not in line_keys:
            issue('MISSING_LINESCORE_HALF', '/liveData/linescore/innings', inning=key[0], half=key[1])
    for side in ('away', 'home'):
        total = linescore.get('teams', {}).get(side, {}).get('runs')
        if not integer(total) or total != line_totals[side]:
            issue('TEAM_RUN_TOTAL_MISMATCH', '/liveData/linescore/teams/' + side, reported=total, inningTotal=line_totals[side])

    return dict(artifactType='baseballo-mlb-metric-source-reconciliation', contractVersion=VERSION,
        gamePk=game_pk, inputSha256=digest(raw), sourceRevision=revision,
        reconcilerSha256=digest(Path(__file__).read_bytes()),
        status='consistent' if not issues else 'inconsistent', issues=issues,
        counts=dict(plays=len(plays), events=sum(len(p['events']) for p in inventory),
                    movements=sum(len(p['movements']) for p in inventory)),
        inventory=inventory, sourceHistoryAdmitted=False, graphCoverageVerified=False,
        metricPopulationAdmitted=False,
        pending=['exhaustive-source-authority', 'operative-event-effects-and-boundaries',
                 'source-to-graph-reconciliation', 'eligible-population-reconciliation'],
        scope='Mechanical source consistency and retained membership; no metric admission or RDF assertions.')


def write_atomic(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, sort_keys=True, ensure_ascii=True, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--game-pk', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Reconciliation cannot overwrite raw source')
    report = reconcile(args.input.read_bytes(), args.game_pk)
    write_atomic(args.output, report)
    print(json.dumps({k: report[k] for k in ('gamePk', 'inputSha256', 'status', 'counts', 'pending')}))


if __name__ == '__main__':
    main()
