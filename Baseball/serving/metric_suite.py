"""Graph-native calculation components over admitted SPARQL bindings.

This module never reads MLB payloads, decides graph identity, or admits source
facts. Calculations are usable independently for tests; live adapters must
report unresolved prerequisites before invoking them. Rational results retain
numerator/denominator strings. Entropy retains exact channel counts because
logarithms generally have no rational representation.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime, timezone, timedelta
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

from rdflib import Graph, Literal

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / 'sparql/metrics'
VERSION = '2.0.25'


class EvidenceError(ValueError):
    pass


def catalog():
    return json.loads((METRICS / 'metric-catalog.json').read_text(encoding='utf-8'))


def gaps():
    return json.loads((METRICS / 'gap-register.json').read_text(encoding='utf-8'))


def policies():
    return json.loads((METRICS / 'batch-release-policy.json').read_text(encoding='utf-8'))


def fingerprint():
    paths = [Path(__file__), ROOT / 'serving/metric-suite-schema.sql',
             METRICS / 'metric-catalog.json', METRICS / 'gap-register.json',
             METRICS / 'batch-release-policy.json', METRICS / 'trajectory-origin-policy.json']
    paths.extend(sorted(METRICS.glob('*.rq')))
    paths.extend([ROOT / 'sources/mlb-game/pipeline/batting-admission.py',
                  ROOT / 'sources/mlb-game/pipeline/scoring-run-admission.py',
                  ROOT / 'sources/mlb-game/shacl/scoring-run-admission.ttl',
                  ROOT / 'sources/mlb-game/pipeline/runner-resolution-admission.py',
                  ROOT / 'sources/mlb-game/shacl/runner-resolution-admission.ttl',
                  ROOT / 'sources/mlb-game/pipeline/contact-continuation-admission.py',
                  ROOT / 'sources/mlb-game/shacl/contact-continuation.ttl',
                  ROOT / 'sources/mlb-game/shacl/batting-admission.ttl',
                  ROOT / 'sources/mlb-game/nifi/prepare-schedule-batch.py'])
    paths.extend(ROOT / e['authoritativeQuery'] for e in [*catalog()['metrics'], *catalog().get('components', [])])
    return hashlib.sha256('\n'.join(
        p.relative_to(ROOT).as_posix() + ':' + hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths).encode()).hexdigest()


def exact(value: Fraction | int):
    value = Fraction(value)
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def fraction(value):
    if isinstance(value, dict):
        return Fraction(int(value['numerator']), int(value['denominator']))
    if isinstance(value, float):
        raise EvidenceError('Floating-point inputs are not admitted as exact metric evidence')
    return Fraction(value)


def available(value, *, evidence=(), components=None, **extra):
    return {'status': 'available', 'value': exact(value), 'gaps': [],
            'evidence': sorted(set(evidence)), 'components': components or {}, **extra}


def unavailable(*reasons, evidence=(), **extra):
    return {'status': 'unavailable', 'value': None,
            'gaps': sorted(set(reasons or ('MISSING_EVIDENCE',))),
            'evidence': sorted(set(evidence)), **extra}


def ratio(numerator, denominator, **kwargs):
    if denominator == 0:
        components = dict(kwargs.pop('components', {}))
        components.update(numerator=exact(numerator), denominator=exact(denominator))
        return unavailable('EMPTY_DENOMINATOR', components=components, **kwargs)
    return available(Fraction(numerator) / Fraction(denominator), **kwargs)


def _integer(value, name, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise EvidenceError(f'Invalid {name}')
    return value


def _boolean(value, name):
    if type(value) is not bool:
        raise EvidenceError(f'Unknown or invalid {name}')
    return value


def _unique(rows, fields, nullable=()):
    unique = {}
    for row in rows:
        key = tuple(row.get(f) for f in fields)
        if any((v is None and f not in nullable) or v == '' for f, v in zip(fields, key)):
            raise EvidenceError('Missing evidence identity: ' + ', '.join(fields))
        if key in unique and unique[key] != row:
            raise EvidenceError('Conflicting evidence for ' + repr(key))
        unique[key] = row
    return list(unique.values())


def run_kernel(metric_id, rows):
    entry = next((e for e in [*catalog()['metrics'], *catalog().get('components', [])] if e['id'] == metric_id), None)
    if entry is None:
        raise EvidenceError('Unknown metric')
    columns = entry['inputColumns']
    values = []
    for row in rows:
        values.append('(' + ' '.join('UNDEF' if row.get(c) is None else Literal(row[c]).n3()
                                   for c in columns) + ')')
    query = (ROOT / entry['authoritativeQuery']).read_text(encoding='utf-8')
    query = query.replace('# INPUT_ROWS', '\n'.join(values))
    # Peer VALUES use the same ordered values, with independently named variables.
    query = query.replace('# PEER_ROWS', '\n'.join(values))
    if not rows:
        from rdflib.plugins.sparql.processor import prepareQuery
        prepareQuery(query)
        return []
    return [{str(k): v.toPython() for k, v in row.asdict().items()}
            for row in Graph().query(query)]


def trajectory_origin(row, batter):
    """Resolve the metric initial position from admitted, act-scoped evidence.

    This accepts graph bindings, not MLB source fields. A caller must supply
    positive PA-start/no-intervening-movement evidence for the optional fallback.
    Empty arrays or missing events do not certify that condition.
    """
    participant = row.get('participant')
    if not isinstance(batter, str) or not batter or not isinstance(participant, str) or not participant:
        return unavailable('AMBIGUOUS_BATTER_OR_RUNNER_IDENTITY')
    if participant == batter:
        return available(0, originBasis='metric-batter-HOME')
    codes = {'1B': 1, '2B': 2, '3B': 3}
    designations = row.get('originDesignations', [])
    if designations:
        identities, starts, evidence = set(), set(), []
        for designation in designations:
            if (not designation.get('designation') or not designation.get('record')
                    or not row.get('act') or designation.get('act') != row['act']
                    or designation.get('baseCode') not in codes):
                return unavailable('AMBIGUOUS_SEGMENT_ORIGIN')
            identities.add(designation['designation'])
            starts.add(designation['baseCode'])
            evidence.extend([designation['designation'], designation['record']])
        if len(identities) != 1 or len(starts) != 1:
            return unavailable('AMBIGUOUS_SEGMENT_ORIGIN')
        return available(codes[next(iter(starts))], evidence=evidence, originBasis='segment-designation')
    fallback = row.get('paStartOrigin') or {}
    if (fallback.get('actBeginsAtPAStart') is True
            and fallback.get('noInterveningSameRunnerMovement') is True
            and fallback.get('evidence') and fallback.get('stasis')
            and row.get('act') and fallback.get('act') == row['act']
            and fallback.get('runner') == participant and fallback.get('baseCode') in codes):
        return available(codes[fallback['baseCode']], evidence=[fallback['stasis'], *fallback['evidence']],
                         originBasis='positively-supported-PA-start')
    return unavailable('SEGMENT_ORIGIN_UNAVAILABLE')


def trajectories(participants, outs_before, attributed_outs, *, batter=None, batter_result_type=None):
    """One already coalesced, complete attributed consequence. No raw rows."""
    _integer(outs_before, 'outs before', 0, 2)
    _integer(attributed_outs, 'attributed outs', 0, 3 - outs_before)
    rows = _unique(participants, ('participant',))
    if not rows:
        return unavailable('MISSING_PARTICIPANTS')
    exclude_progress = (batter_result_type is not None and
                        batter_result_type in policies()['batterProgressExcludedResultTypes'])
    inputs, evidence = [], []
    for row in rows:
        if batter is not None:
            origin = trajectory_origin(row, batter)
            if origin['status'] != 'available':
                return origin
            start = int(fraction(origin['value']))
            evidence.extend(origin['evidence'])
        else:
            # Existing callers already supply admitted, coalesced trajectory starts.
            start = _integer(row.get('start'), 'original start', 0, 3)
        outcome = row.get('terminal')
        if outcome not in {'safe', 'scored', 'out', 'stranded'}:
            return unavailable('UNKNOWN_TERMINAL_STATE')
        end = row.get('end')
        if outcome in {'safe', 'stranded'}:
            _integer(end, 'terminal base', 1, 3)
        elif outcome == 'scored' and end != 4:
            raise EvidenceError('A scored path must terminate at SCORE')
        if outcome == 'stranded' and outs_before + attributed_outs != 3:
            raise EvidenceError('Stranding requires an evidenced inning-ending consequence')
        progress = _boolean(row.get('creditProgress'), 'progress attribution')
        # Owning MLB result contract maps InterferenceProcess only from
        # catcher_interf. This is a credit exclusion, not an inferred cause.
        if exclude_progress:
            progress = False
        credit_out = _boolean(row.get('creditOut'), 'out attribution')
        if credit_out and outcome != 'out':
            raise EvidenceError('Out attribution requires an out')
        evidence.extend(row.get('evidence', []))
        inputs.append(dict(key='consequence', participant=row['participant'],
                           start=start, end=end, terminal=outcome,
                           creditProgress=progress, creditOut=credit_out,
                           outsBefore=outs_before, attributedOuts=attributed_outs))
    if sum(r['creditOut'] for r in inputs) != attributed_outs:
        raise EvidenceError('Distinct attributed out count disagrees with participant evidence')
    result, = run_kernel('tfs', inputs)
    components = {k: exact(Fraction(result[k], 36)) for k in ['progress', 'destruction', 'erosion']}
    return available(Fraction(result['numerator']) / Fraction(result['denominator']),
                     evidence=evidence, components=components)


def failed_hit_and_run_scores(participants, outs_before, *, batter, runner,
                              confirmed=False, confirmation_evidence=(), complete=False):
    """Route one admitted swinging-K/runner-thrown-out consequence to its owner.

    Confirmation and complete coalesced participants must already be admitted
    independently. This is not a source classifier: a K/CS pair is insufficient.
    The empty running-score list prevents a duplicate damage observation; it is
    not a zero-valued running episode eligible for a participation denominator.
    Analytical responsibility does not change the agent of any running act.
    """
    _boolean(confirmed, 'called hit-and-run confirmation')
    _boolean(complete, 'consequence completeness')
    if not confirmed or not confirmation_evidence:
        return unavailable('CALLED_HIT_AND_RUN_UNCONFIRMED')
    if not complete:
        return unavailable('ATTRIBUTED_CONSEQUENCE_INCOMPLETE')
    if (not isinstance(confirmation_evidence, (list, tuple)) or
            any(not isinstance(item, str) or not item.strip() for item in confirmation_evidence)):
        raise EvidenceError('Confirmation requires admitted evidence identities')
    if not batter or not runner or batter == runner:
        raise EvidenceError('Distinct batter and runner identities are required')
    rows = _unique(participants, ('participant',))
    by_person = {row['participant']: row for row in rows}
    if not {batter, runner} <= by_person.keys():
        return unavailable('MISSING_PARTICIPANTS')
    if (by_person[batter].get('start') != 0 or
            type(by_person[runner].get('start')) is not int or
            by_person[runner]['start'] not in (1, 2, 3) or
            {row['participant'] for row in rows if row.get('terminal') == 'out'} != {batter, runner}):
        raise EvidenceError('This allocation requires the batter out and the identified runner out')
    # Both outs use the settled formula together. Other runners retain actual
    # terminal states, including a scored runner's zero remaining erosion.
    attributed = [dict(row, creditProgress=False, creditOut=row['participant'] in {batter, runner}) for row in rows]
    score = trajectories(attributed, outs_before, 2)
    if score['status'] != 'available':
        return score
    score['evidence'] = sorted(set(score['evidence']) | set(confirmation_evidence))
    return dict(score, batter=batter, runner=runner, attributedOuts=2,
                attribution='confirmed-failed-hit-and-run', independentRunningScores=[])


def percentiles(entries, *, metric_id='paq-2', complete_population=False):
    """Exact midranks, including exact lexicographic PAQ-2.1 tie breakers."""
    if metric_id not in {'paq-2', 'paq-a', 'recovery-quality', 'paq-2.1'}:
        raise EvidenceError('Not a percentile metric')
    _boolean(complete_population, 'reference population completeness')
    entries = _unique(entries, ('key',))
    if not complete_population:
        return {e['key']: unavailable('REFERENCE_POPULATION_INCOMPLETE') for e in entries}
    inputs = []
    for entry in entries:
        if metric_id == 'paq-a' and not entry.get('cohort'):
            return {e['key']: unavailable('PAQ_A_STATE') for e in entries}
        if 'cohort' in entry and (not isinstance(entry['cohort'], str) or not entry['cohort']):
            raise EvidenceError('Invalid reference cohort identity')
        score = fraction(entry['score'])
        row = {'key': entry['key'], 'cohort': entry.get('cohort', 'reference'),
               'scoreN': score.numerator, 'scoreD': score.denominator}
        if metric_id == 'paq-2.1':
            if entry.get('recovery') is None or entry.get('depth') is None:
                return {e['key']: unavailable('MISSING_LEXICOGRAPHIC_DIMENSION') for e in entries}
            recovery = fraction(entry['recovery'])
            row.update(recoveryN=recovery.numerator, recoveryD=recovery.denominator,
                       depth=_integer(entry['depth'], 'resolution depth'))
        inputs.append(row)
    result = {}
    for row in run_kernel(metric_id, inputs):
        result[row['key']] = ratio(row['numerator'], row['denominator'],
                                  components={'population': row['population'],
                                              'lower': row['lower'], 'ties': row['ties']})
    return result


def player_paq(results):
    if not results or any(r['status'] != 'available' for r in results):
        return unavailable('PLAYER_PAQ_COVERAGE_INCOMPLETE')
    values = sorted(fraction(r['value']) for r in results)
    n = len(values)
    median = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
    return available(sum(values) / n, components={
        'median': exact(median), 'plateAppearances': n,
        'topQuartileRate': exact(Fraction(sum(v >= 75 for v in values), n)),
        'bottomQuartileRate': exact(Fraction(sum(v <= 25 for v in values), n)),
        'distribution': [exact(v) for v in values]})


def paq_a_population(entries, *, complete_population=False):
    """Build cohorts only from admitted immediate pre-consequence base/out states."""
    entries = _unique(entries, ('key',))
    prepared = []
    for entry in entries:
        state = entry.get('comparisonState') or {}
        if (state.get('boundary') != policies()['paqAComparisonBoundary']
                or not state.get('evidence') or not entry.get('referencePopulation')
                or state.get('occupiedBases') is None or state.get('outs') is None):
            return {e['key']: unavailable('PAQ_A_STATE') for e in entries}
        bases = state['occupiedBases']
        if not isinstance(bases, list) or any(type(b) is not int or b not in (1,2,3) for b in bases) or len(set(bases)) != len(bases):
            raise EvidenceError('Invalid admitted occupied-base state')
        outs = _integer(state['outs'], 'pre-consequence outs', 0, 2)
        if not isinstance(entry['referencePopulation'], str):
            raise EvidenceError('Invalid PAQ-A reference population')
        cohort = _json([entry['referencePopulation'], sorted(bases), outs])
        prepared.append(dict(entry, cohort=cohort))
    results = percentiles(prepared, metric_id='paq-a', complete_population=complete_population)
    for entry in entries:
        results[entry['key']]['evidence'] = sorted(set(entry['comparisonState']['evidence']))
    return results


def project_runner_boundary(events, boundary, *, history_complete=False,
                            boundary_supported=False, evidence=()):
    """C2 over one admitted person's history, not raw source row indexes.

    Ordinals are supplied by independently supported analytical ordering.
    Equal ordinals do not imply order. Source coverage and graph validation
    remain outside this calculation; the public API cannot supply these flags.
    A returned base is an analytical state, never a new RDF assertion.
    """
    _integer(boundary, 'boundary ordinal')
    _boolean(history_complete, 'verified history completeness')
    _boolean(boundary_supported, 'boundary support')
    if not history_complete:
        return unavailable('RUN_CONTINUITY', 'COMPLETENESS', evidence=evidence)
    if not boundary_supported or not evidence:
        return unavailable('BOUNDARY_STATE', evidence=evidence)
    rows = _unique(events, ('event',))
    inputs = []
    for row in rows:
        _integer(row.get('ordinal'), 'supported event ordinal')
        _boolean(row.get('known'), 'event state support')
        _boolean(row.get('changesState'), 'state-change support')
        if row.get('base') is not None:
            _integer(row['base'], 'safe base position', 1, 3)
        inputs.append(dict(row, key='runner-boundary', boundary=boundary,
                           historyComplete=history_complete, boundarySupported=boundary_supported))
    result = run_kernel('runner-boundary-projection', inputs)
    if len(result) != 1:
        return unavailable('BOUNDARY_STATE', evidence=evidence)
    selected, = result
    return available(selected['base'], evidence=evidence,
                     basePosition=selected['base'], sourceEvent=selected['event'],
                     projection='safe-base-at-boundary')


def paq21_population(entries, *, complete_population=False):
    """Select the accepted applicable population without inventing zero scores."""
    _boolean(complete_population, 'reference population completeness')
    entries = _unique(entries, ('key',))
    eligible, excluded, unknown = [], {}, False
    for entry in entries:
        flags = [entry.get('twoStrikeEligible'), entry.get('defensiveApplicable')]
        if any(flag is not None and type(flag) is not bool for flag in flags):
            raise EvidenceError('Invalid PAQ-2.1 applicability evidence')
        if any(flag is False for flag in flags):
            excluded[entry['key']] = unavailable('PAQ21_NOT_APPLICABLE')
        elif any(flag is None for flag in flags):
            unknown = True
            excluded[entry['key']] = unavailable('PAQ21_ELIGIBILITY_UNKNOWN')
        else:
            eligible.append(entry)
    return {**excluded, **percentiles(eligible, metric_id='paq-2.1',
                                      complete_population=complete_population and not unknown)}


def empty_game_eligible(plate_appearances):
    """The count must already be complete and admitted for this player-game."""
    if plate_appearances is None:
        return None
    return _integer(plate_appearances, 'plate appearance count') >= policies()['emptyGameMinimumPlateAppearances']


def independent_runner_damage(participants, outs_before, attributed_outs):
    """Accepted direct destruction plus surviving-teammate erosion magnitude."""
    rows = [dict(row, creditProgress=False) for row in participants]
    result = trajectories(rows, outs_before, attributed_outs)
    if result['status'] != 'available':
        return result
    return available(-fraction(result['value']), evidence=result['evidence'],
                     components={k: result['components'][k] for k in ['destruction', 'erosion']})


def independent_runner_contribution(participants, outs_before, attributed_outs):
    """Gain, damage and net for one already admitted complete/coalesced episode.

    This does not join source segments or decide continuity. An out-ending
    personal path retains no intermediate advancement under the existing policy.
    """
    rows = _unique(participants, ('participant',))
    damage = independent_runner_damage(rows, outs_before, attributed_outs)
    if damage['status'] != 'available':
        return damage
    inputs = []
    for row in rows:
        credit = _boolean(row.get('creditProgress'), 'independent progress attribution')
        if credit and row['terminal'] in ('safe', 'scored'):
            _integer(row['start'], 'independent advance origin', 1, 3)
        inputs.append(dict(row, key='independent-episode'))
    calculated, = run_kernel('independent-runner-advancement', inputs)
    gain = Fraction(int(calculated['numerator']), int(calculated['denominator']))
    loss = fraction(damage['value'])
    return available(gain-loss, evidence=damage['evidence'], components={
        'advancement': exact(gain), 'damage': exact(loss), 'net': exact(gain-loss),
        'destruction': damage['components']['destruction'], 'erosion': damage['components']['erosion']})


def review_dependence_by_mechanism(rows, *, complete_populations):
    """Separate already admitted outcome populations; never pool mechanisms.

    reviewDependent means supported dependence of the operative outcome,
    not merely that a review occurred. The generic kernel's legacy column
    named reviewed receives this dependency flag.
    """
    mechanisms = policies()['reviewDependenceMechanisms']
    if any(row.get('mechanism') not in mechanisms for row in rows):
        return {m: unavailable('REVIEW_MECHANISM_UNKNOWN') for m in mechanisms}
    results = {}
    for mechanism in mechanisms:
        complete = complete_populations.get(mechanism, False)
        _boolean(complete, 'mechanism population completeness')
        selected = _unique([r for r in rows if r['mechanism'] == mechanism], ('outcome',))
        if not complete:
            results[mechanism] = unavailable('OUTCOME_POPULATION')
            continue
        if any(r.get('eligible') is None for r in selected):
            results[mechanism] = unavailable('OUTCOME_POPULATION')
            continue
        inputs = []
        for row in selected:
            if not _boolean(row['eligible'], 'review eligibility'):
                continue
            if row.get('reviewDependent') is None:
                break
            inputs.append(dict(key=mechanism, outcome=row['outcome'], eligible=True,
                               reviewed=_boolean(row['reviewDependent'], 'operative review dependence')))
        else:
            results[mechanism] = calculate('review-dependence-rate', inputs)
            continue
        results[mechanism] = unavailable('OPERATIVE_REVIEW')
    return results


def recovery_steps(pitches):
    """Already admitted, ordered count history, including Q5 non-pitch awards.

    A row identifies either a delivered ``pitch`` or a ``countAward`` process.
    Automatic awards update strikes but never contribute recovery pitches.
    No source membership or event ordering is inferred by this reducer.
    """
    events = []
    for row in pitches:
        pitch, award = row.get('pitch'), row.get('countAward')
        if bool(pitch) == bool(award):
            raise EvidenceError('Identify exactly one pitch or automatic count award')
        if award and row.get('awardKind') not in {'ball', 'strike'}:
            raise EvidenceError('An automatic award needs its admitted ball/strike kind')
        events.append(dict(row, event=pitch or award, isPitch=bool(pitch)))
    pitches = _unique(events, ('event',))
    if not pitches:
        return unavailable('EXACT_PITCH_COUNTS')
    two_strikes, steps, previous_strikes = False, 0, 0
    for index, pitch in enumerate(pitches):
        strikes = _integer(pitch.get('strikesAfter'), 'post-pitch strikes', 0, 3)
        terminal = _boolean(pitch.get('terminal'), 'terminal count-history event')
        if strikes < previous_strikes or (strikes == 3 and not terminal):
            raise EvidenceError('Inconsistent operative strike-count sequence')
        if not pitch['isPitch'] and strikes != previous_strikes + (pitch['awardKind'] == 'strike'):
            raise EvidenceError('Automatic award disagrees with its operative count increment')
        previous_strikes = strikes
        if terminal and index != len(pitches) - 1:
            raise EvidenceError('A terminal event cannot precede another event in this PA')
        if two_strikes and not terminal and pitch['isPitch']:
            steps += 1
        two_strikes = two_strikes or strikes >= 2
    if not pitches[-1]['terminal']:
        return unavailable('INCOMPLETE_PLATE_APPEARANCE')
    if not two_strikes:
        return unavailable('NOT_TWO_STRIKE_ELIGIBLE')
    return available(steps, evidence=[p['event'] for p in pitches])


def defensive_depth(acts):
    """Longest directed path counted in intentional acts, not edges."""
    acts = _unique(acts, ('act',))
    if not acts:
        return unavailable('MISSING_DEFENSIVE_ACTS')
    nodes = {a['act'] for a in acts}
    nexts, indegree, depth = {}, dict.fromkeys(nodes, 0), dict.fromkeys(nodes, 1)
    for act in acts:
        if not act.get('agent'):
            return unavailable('MISSING_DEFENSIVE_AGENT')
        nexts[act['act']] = set(act.get('next', []))
        if not nexts[act['act']] <= nodes:
            return unavailable('INCOMPLETE_DEFENSIVE_PATH')
        for target in nexts[act['act']]:
            indegree[target] += 1
    queue = deque(n for n in nodes if indegree[n] == 0)
    visited = 0
    while queue:
        node = queue.popleft(); visited += 1
        for target in nexts[node]:
            depth[target] = max(depth[target], depth[node] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes):
        return unavailable('CYCLIC_DEFENSIVE_ORDER')
    return available(max(depth.values()), evidence=nodes,
                     components={'defenderBreadth': len({a['agent'] for a in acts})})


def channel_entropy(counts):
    if len(counts)!=3 or any(type(c) is not int or c<0 for c in counts):
        raise EvidenceError('Channel entropy requires three nonnegative integer counts')
    total=sum(counts)
    if total==0:
        return unavailable('EMPTY_DENOMINATOR',components={'channelCounts':counts,'pathBreadth':0})
    probabilities=[Fraction(c,total) for c in counts]
    entropy=-sum(float(p)*math.log(float(p)) for p in probabilities if p)/math.log(3)
    return {'status':'available','value':None,'approximateValue':entropy,
            'exactExpression':'-sum(p*ln(p))/ln(3)','gaps':[],
            'components':{'channelCounts':counts,'probabilities':[exact(p) for p in probabilities],
                          'pathBreadth':sum(c>0 for c in counts)},'evidence':[]}


def calculate(metric_id, rows):
    """Compute a declared kernel on admitted facts. Never accepts feed JSON."""
    entry = next((e for e in catalog()['metrics'] if e['id'] == metric_id), None)
    if entry is None:
        raise EvidenceError('Unknown metric')
    if not rows:
        return unavailable('EMPTY_DENOMINATOR')
    rows = _unique(rows, tuple(entry['rowIdentity']), entry.get('nullableColumns', []))
    if len({r.get('key') for r in rows}) != 1:
        raise EvidenceError('Use separate calls for distinct aggregation keys')
    for row in rows:
        for column in entry['inputColumns']:
            if row.get(column) is None and column not in entry.get('nullableColumns', []):
                raise EvidenceError('Missing kernel input ' + column)
            if isinstance(row.get(column), float):
                raise EvidenceError('Inexact floating point kernel input')
        for field in ['eligible', 'resolved', 'reversed', 'reviewed', 'runnerOnBase', 'empty', 'changesState']:
            if field in row:
                _boolean(row[field], field)
        for field in ['progress36', 'batterProgress36', 'otherProgress36', 'existingDestruction36',
                      'existingRunnerOuts', 'erosion36', 'positiveEpisodes', 'plateAppearances']:
            if field in row:
                _integer(row[field], field)
        if 'score36' in row and type(row['score36']) is not int:
            raise EvidenceError('Trajectory score must have an exact integer numerator')
        if metric_id == 'contribution-path-diversity' and row['channel'] not in {'batter_self', 'batter_other', 'runner_self'}:
            raise EvidenceError('Unknown contribution channel')
    if metric_id == 'resolution-depth':
        edges = run_kernel(metric_id, rows)
        acts = {}
        for edge in edges:
            a = acts.setdefault(edge['act'], {'act': edge['act'], 'agent': edge['agent'], 'next': []})
            if a['agent'] != edge['agent']:
                raise EvidenceError('Conflicting defensive agent')
            if edge.get('next') is not None:
                a['next'].append(edge['next'])
        return defensive_depth(list(acts.values()))
    results = run_kernel(metric_id, rows)
    if not results:
        return unavailable('EMPTY_DENOMINATOR')
    if len(results) != 1:
        raise EvidenceError('Use separate calls for distinct aggregation keys')
    result = results[0]
    if metric_id == 'contribution-path-diversity':
        return channel_entropy([int(result[c]) for c in ['self','other','running']])
    components = {k: v for k, v in result.items() if k not in {'key', 'numerator', 'denominator'}}
    if metric_id == 'empty-game-rate':
        components.update(emptyGames=int(result['numerator']), eligibleGames=int(result['denominator']))
    return ratio(int(result['numerator']), int(result['denominator']), components=components)


def empty_game_damage(pa_scores, independent_scores, *, empty, complete):
    if not complete or empty is None:
        return unavailable('OFFENSIVE_EPISODE_COMPLETENESS')
    if not empty:
        return unavailable('NOT_AN_EMPTY_GAME')
    scores = [*pa_scores, *independent_scores]
    if any(s['status'] != 'available' for s in scores):
        return unavailable('DAMAGE_EPISODE_INCOMPLETE')
    return available(sum((max(Fraction(0), -fraction(s['value'])) for s in scores), Fraction(0)),
                     components={'episodes': len(scores)})


def summarize(values, *, threshold=None):
    """Exact complete-population mean; never drop unavailable members."""
    if not values:
        return unavailable('EMPTY_DENOMINATOR')
    if any(v['status'] != 'available' or v.get('value') is None for v in values):
        return unavailable('INCOMPLETE_AGGREGATE')
    numbers = [fraction(v['value']) for v in values]
    components = {'count': len(numbers), 'total': exact(sum(numbers, Fraction(0)))}
    if threshold is not None:
        components['atOrAboveThresholdRate'] = exact(Fraction(sum(n >= threshold for n in numbers), len(numbers)))
    return available(sum(numbers, Fraction(0)) / len(numbers), components=components)


def public_catalog():
    result = catalog()
    result['gapRegister'] = gaps()
    result['implementationSha256'] = fingerprint()
    return result


def evidence_query(graphs):
    """Compose accepted inventories within explicit promoted game graphs."""
    graph_list = sorted(set(graphs))
    if any(not isinstance(g, str) or not re.fullmatch(r'https://w3id\.org/baseball/graph/game/[0-9]+', g)
           for g in graph_list):
        raise EvidenceError('Unsafe or non-authoritative metric graph')
    if not graph_list:
        return 'SELECT ?graph ?game ?kind ?entity WHERE { BIND(0 AS ?emptyScope) FILTER(?emptyScope = 1) }'
    # A false filter avoids SPARQL engine differences around empty VALUES.
    scope = ('VALUES ?graph { ' + ' '.join('<' + g + '>' for g in graph_list) + ' }') if graph_list else 'FILTER(false)'
    prefixes, queries = set(), []
    for name in ('suite-evidence.rq', 'runner-movement-evidence.rq'):
        source = (METRICS / name).read_text(encoding='utf-8')
        # Both canonical files name the same OBO namespace with different
        # aliases. Use one alias in the composed query for RDFLib/Jena parity.
        source = source.replace('bfo:', 'obo:')
        prefixes.update(re.findall(r'^PREFIX .+$', source, flags=re.MULTILINE))
        source = re.sub(r'^PREFIX .+\n', '', source, flags=re.MULTILINE)
        queries.append(source.replace('WHERE {', 'WHERE {\n  ' + scope, 1))
    # Reuse the canonical movement query rather than maintaining another copy
    # of the accepted graph paths in a serving-only query or RDF index.
    # Restrict the dataset as well as the bindings: otherwise Jena can scan
    # unrelated named graphs before joining the selected graph VALUES.
    dataset = ''.join('\nFROM NAMED <' + g + '>' for g in graph_list)
    return ('\n'.join(sorted(prefixes)) + '\nSELECT *' + dataset + '\nWHERE {\n{ {\n' + queries[0]
            + '\n} } UNION { {\n' + queries[1]
            + '\n} BIND("runner_movement" AS ?kind) BIND(?resolution AS ?entity) }\n}')


def normalize_bindings(bindings, graphs):
    allowed = set(graphs)
    rows = []
    for binding in bindings:
        if not isinstance(binding, dict):
            raise EvidenceError('Invalid SPARQL evidence binding')
        row = {key: term['value'] for key, term in binding.items()}
        if row.get('graph') not in allowed or not row.get('entity') or not row.get('game'):
            raise EvidenceError('Evidence escaped its graph scope or lacks a referent')
        for field in ('graph', 'game', 'entity', 'player', 'act', 'roleType', 'reviewRecord',
                      'playerTeamRole', 'team', 'teamRole', 'paResult', 'paResultType',
                      'paResultJudgment', 'paResultDecision', 'paResultRecord',
                      'original', 'operative', 'disposition', 'plateAppearance', 'resolution',
                      'runner', 'originDesignation', 'originBase', 'destinationBase', 'batter',
                      'awardRule', 'contactPlay', 'award', 'record', 'episode',
                      'originRecord', 'safeJudgment', 'safeDecision', 'trajectory',
                      'trajectoryHalf', 'trajectoryInterval', 'paHalf', 'paInterval',
                      'paStartInstant', 'paEndInstant', 'paStartTimestamp', 'paEndTimestamp', 'paOutCount',
                      'countJudgment', 'countDecision', 'countRule', 'priorPitch', 'nextPitch',
                      'trajectoryEndInstant', 'gameEndTimestamp', 'independentStealAct'):
            if field in binding and binding[field].get('type') != 'uri':
                raise EvidenceError('Evidence identity must be an IRI: ' + field)
        for field in ('paStart', 'paEnd', 'gameEnd'):
            if field in binding and (binding[field].get('type') != 'literal'
                    or binding[field].get('datatype') != 'http://www.w3.org/2001/XMLSchema#dateTime'):
                raise EvidenceError('PA boundary requires an explicit dateTime value: ' + field)
        if row.get('kind') not in {'plate_appearance', 'batted_play', 'run', 'player_game', 'player_team_game', 'review', 'runner_movement', 'runner_history', 'automatic_count_award'}:
            raise EvidenceError('Unknown evidence grain')
        if row['kind'] == 'automatic_count_award' and (row.get('countAwardKind') not in {'ball', 'strike'} or
                not all(row.get(f) for f in ('plateAppearance', 'countJudgment', 'countDecision', 'countRule', 'record'))):
            raise EvidenceError('Automatic count award lacks its admitted process/judgment/decision structure')
        if row['kind'] == 'player_team_game' and (row.get('playerTeamRole') != row['entity'] or not row.get('player')):
            raise EvidenceError('Player/team game evidence lacks its realized role or bearer')
        if row['kind'] == 'runner_history' and (row.get('trajectory') != row['entity'] or
                not all(row.get(f) for f in ('episode', 'player', 'trajectoryHalf', 'trajectoryInterval'))):
            raise EvidenceError('Personal history lacks its graph membership or scope')
        if row['kind'] == 'runner_movement' and (
                not all(row.get(f) for f in ('plateAppearance', 'resolution', 'act'))
                or row['entity'] != row['resolution']):
            raise EvidenceError('Movement evidence lacks its PA, act or resolution identity')
        rows.append(row)
    # Stable exact duplicates are harmless; conflicting review facts survive
    # normalization so the disposition adapter can refuse them explicitly.
    return [json.loads(s) for s in sorted({_json(row) for row in rows})]


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def movement_coverage(rows):
    """Count observed bindings, without certifying trajectory completeness."""
    groups = defaultdict(list)
    for row in rows:
        if row['kind'] == 'runner_movement':
            groups[(row['graph'], row['plateAppearance'], row['act'], row['resolution'])].append(row)
    coverage = {'observedPairs': len(groups), 'populationComplete': False}
    for label, fields in {
        'withRunnerBinding': ('runner',),
        'withEpisodeBinding': ('episode',),
        'withRunnerEpisodeRecordBinding': ('runner', 'episode', 'record'),
        'withPersonalTrajectoryBinding': ('trajectory', 'trajectoryHalf', 'trajectoryInterval'),
        'withSegmentOriginBinding': ('originDesignation', 'originBase', 'originCode'),
        'withOriginRecordBinding': ('originDesignation', 'originRecord'),
        'withSafeDestinationBinding': ('destinationBase', 'destinationCode'),
        'withSafeDecisionBinding': ('safeJudgment', 'safeDecision', 'destinationBase'),
        'withContactPlayBinding': ('contactPlay',),
        'withCausalRequiredAwardBinding': ('award', 'awardRule'),
        'withSourceRecordBinding': ('record',),
    }.items():
        coverage[label] = sum(any(all(r.get(f) is not None for f in fields) for r in observations)
                              for observations in groups.values())
    origins = [set(r['metricOrigin'] for r in observations if 'metricOrigin' in r)
               for observations in groups.values()]
    coverage.update(withOneMetricOriginBinding=sum(len(values) == 1 for values in origins),
                    withMultipleMetricOriginBindings=sum(len(values) > 1 for values in origins),
                    withoutMetricOriginBinding=sum(not values for values in origins))
    return coverage


def movement_coverage_by_game(rows, consequences=()):
    """Inventory observed graph bindings, never diagnose source freshness from absence.

    Keep games with PA evidence but no movement evidence visible. Selected
    graphs with no rows at all are reported separately by the caller; they
    cannot be given invented per-game evidence here.
    """
    groups, scored = defaultdict(list), defaultdict(int)
    for row in rows:
        groups[row['graph']].append(row)
    for consequence in consequences:
        scored[consequence['graph']] += 1
    return [dict(graph=graph,
                 observedPlateAppearances=len({r['entity'] for r in observations if r['kind'] == 'plate_appearance'}),
                 runnerMovements=movement_coverage(observations),
                 supportedAwardConsequences=scored[graph])
            for graph, observations in sorted(groups.items())]


def batting_participation(rows):
    """Inventory accepted PA/Batter Act/realized Role paths, not official PA credit."""
    pas, players = defaultdict(set), defaultdict(set)
    for row in rows:
        if row['kind'] != 'plate_appearance':
            continue
        key = (row['graph'], row['entity'])
        pas[key]  # Preserve PAs whose participation path is absent.
        if row.get('player') and row.get('act'):
            pas[key].add(row['player'])
            players[row['player']].add(key)
    return dict(observedPlateAppearances=len(pas),
                withOneBatter=sum(len(values) == 1 for values in pas.values()),
                withMultipleBatters=sum(len(values) > 1 for values in pas.values()),
                withoutBatter=sum(not values for values in pas.values()),
                players=[dict(player=player, observedPlateAppearances=len(members))
                         for player, members in sorted(players.items())],
                officialPlateAppearanceCreditVerified=False,
                teamGameExposureVerified=False)


def batting_qualification(rows, *, graphs, admissions, date_scope, selected_games_complete=False):
    """Project B1-admitted RDF counts; source expectations never enter here.

    Per-game admission and selected-game coverage are independent. A loaded
    subset cannot supply the denominator of a wider selected-period ranking.
    """
    graph_set = set(graphs)
    denied = sorted(g for g in graph_set if admissions.get(g, {}).get('status') != 'admitted'
                    or admissions[g].get('sourceReconciled') is not True
                    or admissions[g].get('graphConforms') is not True)
    result = dict(officialPlateAppearanceCreditVerified=False, teamGameExposureVerified=False,
                  selectedGamesComplete=selected_games_complete is True,
                  admittedGames=len(graph_set)-len(denied), withheldGraphs=denied,
                  expectedObservations=[], participation=[])
    if not graph_set or denied:
        return result
    people, members = defaultdict(set), {}
    observed_graphs = set()
    for row in rows:
        if row['graph'] not in graph_set:
            raise EvidenceError('Batting qualification escaped selected graphs')
        if row['kind'] == 'player_team_game':
            if not all(row.get(f) for f in ('player','game','team','teamRole')):
                raise EvidenceError('Admitted batting exposure has incomplete RDF bindings')
            people[row['player']].add((row['game'], row['team']))
            observed_graphs.add(row['graph'])
        if row['kind'] == 'plate_appearance' and row.get('recognizedBattingResult') in ('true','1'):
            if not all(row.get(f) for f in ('player','act','paResult','paResultType',
                                           'paResultJudgment','paResultDecision','paResultRecord')):
                raise EvidenceError('Admitted PA has incomplete adjudicated RDF bindings')
            key = (row['graph'],row['entity'])
            value = dict(graph=row['graph'],plateAppearance=row['entity'],player=row['player'])
            if key in members and members[key] != value:
                raise EvidenceError('Admitted PA has conflicting player assignment')
            members[key] = value
    if observed_graphs != graph_set or any(m['player'] not in people for m in members.values()):
        raise EvidenceError('Admitted qualification is missing game/player evidence')
    counts = defaultdict(int)
    for member in members.values():
        counts[member['player']] += 1
    result.update(officialPlateAppearanceCreditVerified=True,
                  teamGameExposureVerified=selected_games_complete is True,
                  expectedObservations=sorted(members.values(),key=_json),
                  participation=[dict(player=player, plateAppearances=counts[player],
                      completeParticipation=selected_games_complete is True, dateScope=date_scope,
                      teamGameExposure=[dict(game=game,team=team) for game,team in sorted(exposure)])
                      for player,exposure in sorted(people.items())])
    return result


def selected_schedule_coverage(connection, scope, graphs):
    """Compare independent schedule provenance with selected promoted graphs."""
    game_types = {'regular_season': {'R'}, 'postseason': {'F','D','L','W','C','P'},
                  'preseason': {'S'}, 'exhibition': {'E'}, 'all_star': {'A'}}
    allowed = game_types.get(scope['gameSet'])
    if allowed is None:
        return dict(complete=False, gaps=['UNSUPPORTED_SCHEDULE_SCOPE'])
    expected, unresolved, missing_days = set(), set(), []
    day, end = date.fromisoformat(scope['startDate']), date.fromisoformat(scope['endDate'])
    while day <= end:
        row = connection.execute('SELECT proof_json,proof_sha256 FROM metric_suite_schedule_coverage '
                                 'WHERE official_date=?', (day.isoformat(),)).fetchone()
        if not row:
            missing_days.append(day.isoformat())
        else:
            text, digest = row
            if _hash(text) != digest:
                raise EvidenceError('Selected schedule proof checksum mismatch')
            proof = json.loads(text)
            if proof.get('completeResponse') is not True:
                missing_days.append(day.isoformat())
            for game in proof.get('games', []):
                if game['gameType'] not in allowed:
                    continue
                graph = 'https://w3id.org/baseball/graph/game/'+game['gamePk']
                if game['final']:
                    expected.add(graph)
                elif not game['unplayed']:
                    unresolved.add(graph)
        day += timedelta(days=1)
    missing, unexpected = sorted(expected-set(graphs)), sorted(set(graphs)-expected)
    return dict(complete=not (missing_days or missing or unexpected or unresolved),
                missingDates=missing_days, missingGraphs=missing, unexpectedGraphs=unexpected,
                unresolvedGraphs=sorted(unresolved), expectedGames=len(expected))


def summarize_batting_players(metric_id, scores, *, expected_observations,
                              participation, date_scope, population_complete=False):
    """Exact selected-period PA means over independently admitted memberships.

    Internal reducer only. Callers must derive the observation census, official
    PA credit and applicable team-game exposure from admitted graph contracts.
    This function neither infers those contracts nor accepts HTTP evidence.
    The source adapters currently cannot supply that full input contract.
    """
    pa_metrics = {'tfs', 'offensive-reach', 'paq-2', 'paq-a', 'paq-2.1',
                  'hidden-help-rate', 'rally-kill-rate', 'rally-kill-severity',
                  'opportunity-erosion', 'recovery-quality'}
    if metric_id not in pa_metrics:
        raise EvidenceError('This reducer requires a per-PA mean metric')
    missing = dict(playerPopulationComplete=False, playerResults=[])
    if population_complete is not True:
        return dict(missing, playerSummaryGaps=['COMPLETE_PLAYER_POPULATION'])
    if (not isinstance(date_scope, dict) or
            not all(isinstance(date_scope.get(f), str) and date_scope[f]
                    for f in ('startDate', 'endDate', 'gameSet'))):
        raise EvidenceError('Player summary lacks its selected date scope')
    if date_scope['startDate'] > date_scope['endDate']:
        raise EvidenceError('Reversed player summary date scope')
    fields = ('graph', 'plateAppearance', 'player')
    expected = _unique(expected_observations, fields)
    scored = _unique(scores, fields)
    people = _unique(participation, ('player',))
    keys = lambda collection: {tuple(r[f] for f in fields) for r in collection}
    if keys(expected) != keys(scored):
        return dict(missing, playerSummaryGaps=['COMPLETE_PA_SCORES'])
    if any(r.get('metricId') != metric_id or r.get('status') != 'available'
           or r.get('completePlateAppearance') is not True or r.get('dateScope') != date_scope
           for r in scored):
        return dict(missing, playerSummaryGaps=['COMPLETE_PA_SCORES'])
    owners = {r['player'] for r in people}
    if any(r['player'] not in owners for r in expected):
        return dict(missing, playerSummaryGaps=['COMPLETE_PARTICIPATION'])
    grouped = defaultdict(list)
    for row in scored:
        value = row.get('value')
        if (not isinstance(value, dict) or set(value) != {'numerator', 'denominator'}
                or not all(isinstance(v, str) for v in value.values())):
            raise EvidenceError('Player observation requires an exact fraction')
        try:
            score = Fraction(int(value['numerator']), int(value['denominator']))
        except (ValueError, ZeroDivisionError):
            raise EvidenceError('Invalid player observation fraction') from None
        if exact(score) != value:
            raise EvidenceError('Player observation fraction must be normalized')
        grouped[row['player']].append(score)
    output = []
    for person in people:
        if (not re.fullmatch(r'https://baseballontology[.]org/data/player/[0-9]+', person['player'])
                or person.get('completeParticipation') is not True
                or person.get('dateScope') != date_scope):
            return dict(missing, playerSummaryGaps=['COMPLETE_PARTICIPATION'])
        official = _integer(person.get('plateAppearances'), 'official PA total')
        # A missed game is still an exposure. Independent membership comes
        # from the caller; never derive this list from the scored PA rows.
        games = person.get('teamGameExposure')
        if not isinstance(games, list) or not games:
            return dict(missing, playerSummaryGaps=['TEAM_GAME_EXPOSURE'])
        exposure = _unique(games, ('game', 'team'))
        if any(not all(isinstance(r[f], str) and re.match(r'^https?://\S+$', r[f])
                       for f in ('game', 'team')) for r in exposure):
            raise EvidenceError('Team-game exposure requires graph identities')
        values = grouped[person['player']]
        if official == 0:
            # Accepted batting eligibility; independent running is separate.
            continue
        if not values:
            return dict(missing, playerSummaryGaps=['COMPLETE_PA_SCORES'])
        total = sum(values, Fraction())
        output.append(dict(player=person['player'], metricId=metric_id, status='available',
                           dateScope=dict(date_scope), completeParticipation=True,
                           plateAppearances=official, teamGames=len(exposure),
                           aggregate=dict(kind='mean', sum=exact(total), count=len(values)),
                           value=exact(total / len(values))))
    return dict(playerPopulationComplete=True,
                playerResults=sorted(output, key=lambda r: r['player']), playerSummaryGaps=[])


def live_result(metric_id, rows, *, graph_count):
    entry = next((e for e in catalog()['metrics'] if e['id'] == metric_id), None)
    if entry is None:
        raise EvidenceError('Unknown metric')
    coverage = {'games': graph_count, 'evidenceRows': len(rows),
                'observedEntities': {kind: len({(r['graph'], r['entity']) for r in rows if r['kind'] == kind})
                                     for kind in ['plate_appearance', 'batted_play', 'run', 'player_game', 'review']},
                'runnerMovements': movement_coverage(rows),
                'battingParticipation': batting_participation(rows),
                'populationComplete': False}
    if entry['requires']:
        result = unavailable(*entry['requires'], coverage=coverage, metricId=metric_id,
                             scope='selected promoted game graphs', grain=entry['grain'])
        if metric_id in {'run-construction-depth', 'run-construction-breadth'}:
            result.update(run_construction_evidence(rows, metric_id=metric_id))
            coverage['supportedRuns'] = len(result['runs'])
            coverage['observedRunsWithoutResult'] = len(result['unresolvedRuns'])
            coverage['runGapCounts'] = dict(sorted(
                (reason, sum(reason in run['gaps'] for run in result['unresolvedRuns']))
                for reason in {reason for run in result['unresolvedRuns'] for reason in run['gaps']}))
            result['scope'] = 'Complete individual scoring histories below; coverage of all selected runs remains separately gated.'
        if metric_id in {'tfs', 'offensive-reach'}:
            result['consequences'] = loaded_award_consequences(rows, metric_id=metric_id)
            coverage['byGame'] = movement_coverage_by_game(rows, result['consequences'])
            coverage['selectedGraphsWithoutEvidence'] = max(0, graph_count - len(coverage['byGame']))
            coverage['supportedAwardConsequences'] = len(result['consequences'])
            coverage['observedPAsWithoutSupportedAwardConsequence'] = max(
                0, coverage['observedEntities']['plate_appearance'] - len(result['consequences']))
            result['scope'] = ('Award-consequence results below; complete plate-appearance '
                               f'and selected-population {entry["label"]} remain unavailable.')
        if metric_id == 'tfs':
            boundaries = runner_boundary_states(rows)
            result['runnerBoundaryStates'] = boundaries['states']
            coverage['runnerBoundaryProjection'] = boundaries['coverage']
        return result
    # AV deliberately describes only explicitly resolved mapped reviews. It
    # makes no claim about all league reviews or the correctness of officials.
    review_groups = defaultdict(list)
    for row in rows:
        if row['kind'] == 'review':
            review_groups[(row['graph'], row['entity'])].append(row)
    admitted, unresolved, evidence = [], 0, []
    for (_, review), observations in review_groups.items():
        resolved = [r for r in observations if r.get('decision') in {'affirmed', 'reversed'}]
        signatures = {(r.get('original'), r.get('operative'), r.get('decision')) for r in resolved}
        if len(signatures) > 1:
            return unavailable('CONFLICTING_REVIEW_DISPOSITION', coverage=coverage, metricId=metric_id)
        if not resolved:
            unresolved += 1
            continue
        if any(not all(r.get(f) for f in ['reviewRecord', 'original', 'operative', 'disposition']) for r in resolved):
            raise EvidenceError('Resolved review lacks its supporting graph structure')
        admitted.append({'key': 'resolved-mapped-reviews', 'review': review,
                         'resolved': True, 'reversed': resolved[0]['decision'] == 'reversed'})
        evidence.extend(r[f] for r in resolved for f in ['entity', 'reviewRecord', 'original', 'operative', 'disposition'])
    coverage.update(resolvedReviews=len(admitted), unresolvedReviews=unresolved,
                    population='explicitly resolved mapped reviews in selected graphs')
    result = calculate(metric_id, admitted)
    result.update(coverage=coverage, metricId=metric_id, evidence=sorted(set(evidence)),
                  scope=coverage['population'], grain=entry['grain'])
    return result


def run_construction_results(rows):
    return run_construction_evidence(rows)['runs']


def runner_boundary_states(rows):
    """C2 for unchanged runners bracketed by complete C1 history episodes.

    Existing PA timestamp/instant paths provide conservative episode bounds.
    No source index becomes an ordering assertion. A runner with no episode
    during a PA, a prior Safe outcome, and a later episode in the same complete
    history retains that safe base throughout the PA. Unknown order, missing
    member bindings and unbounded termination cannot supply this projection.
    This supplies individual base states, not a complete PA occupancy or score.
    """
    pas, histories, movements = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        if row['kind'] == 'plate_appearance':
            pas[(row['graph'], row['entity'])].append(row)
        elif row['kind'] == 'runner_history':
            histories[(row['graph'], row['trajectory'])].append(row)
        elif row['kind'] == 'runner_movement' and row.get('trajectory'):
            movements[(row['graph'], row['trajectory'])].append(row)

    temporal_fields = ('game', 'paHalf', 'paInterval', 'paStartInstant', 'paEndInstant',
                       'paStartTimestamp', 'paEndTimestamp', 'paStart', 'paEnd')
    intervals = {}
    for key, observations in pas.items():
        signatures = {tuple(row.get(field) for field in temporal_fields) for row in observations}
        if len(signatures) != 1 or any(value is None for value in next(iter(signatures))):
            continue
        row = observations[0]
        try:
            start = datetime.fromisoformat(row['paStart'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(row['paEnd'].replace('Z', '+00:00'))
        except ValueError:
            continue
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            continue
        intervals[key] = dict(row, start=start.astimezone(timezone.utc), end=end.astimezone(timezone.utc))

    by_half = defaultdict(list)
    for (graph, pa), bounds in intervals.items():
        by_half[(graph, bounds['game'], bounds['paHalf'])].append((pa, bounds))
    states, withheld, ordered = [], [], 0
    state_fields = ('game', 'plateAppearance', 'runner', 'act', 'resolution',
                    'hasSafeType', 'hasOutType', 'hasRunType', 'safeJudgment', 'safeDecision',
                    'destinationBase', 'destinationCode', 'trajectoryHalf', 'trajectoryInterval',
                    'originDesignation', 'originBase', 'originCode', 'metricOrigin', 'batter')
    for key, members in sorted(histories.items()):
        signatures = {(row['game'], row['player'], row['trajectoryHalf'], row['trajectoryInterval']) for row in members}
        reason = None
        if len(signatures) != 1:
            reason = 'CONFLICTING_PERSONAL_HISTORY'
        else:
            game, runner, half, interval = next(iter(signatures))
            expected = {row['episode'] for row in members}
            observed = defaultdict(list)
            for row in movements[key]:
                observed[row.get('episode')].append(row)
            if set(observed) != expected:
                reason = 'PERSONAL_HISTORY_MEMBER_COVERAGE'
        episodes, seen_pas = [], set()
        if reason is None:
            for episode in sorted(expected):
                candidates = observed[episode]
                signatures = {tuple(row.get(field) for field in state_fields) for row in candidates}
                if len(signatures) != 1:
                    reason = 'CONFLICTING_SEGMENT_STATE'; break
                row = candidates[0]
                if (row.get('game') != game or row.get('runner') != runner or row.get('trajectoryHalf') != half
                        or row.get('trajectoryInterval') != interval):
                    reason = 'CONFLICTING_PERSONAL_HISTORY'; break
                pa = row['plateAppearance']
                bounds = intervals.get((key[0], pa))
                if bounds is None or bounds['paHalf'] != half or bounds['game'] != game:
                    reason = 'UNSUPPORTED_PA_BOUNDARY'; break
                if pa in seen_pas:
                    reason = 'UNSUPPORTED_WITHIN_PA_EPISODE_ORDER'; break
                seen_pas.add(pa)
                outcome = (row.get('hasSafeType'), row.get('hasOutType'), row.get('hasRunType'))
                if outcome == ('true', 'false', 'false') and row.get('destinationCode') in {'1B', '2B', '3B'}:
                    if not all(row.get(field) for field in ('safeJudgment', 'safeDecision', 'destinationBase')):
                        reason = 'UNSUPPORTED_SEGMENT_END'; break
                    base = int(row['destinationCode'][0])
                    origin = segment_origin(row)
                    if origin is None:
                        reason = 'UNSUPPORTED_SEGMENT_ORIGIN'; break
                    changes = origin != base
                elif outcome in {('false', 'true', 'false'), ('false', 'false', 'true')}:
                    base, changes = None, True
                else:
                    reason = 'UNSUPPORTED_SEGMENT_END'; break
                episodes.append(dict(row, bounds=bounds, base=base, changes=changes))
        if reason is None:
            episodes.sort(key=lambda row: row['bounds']['start'])
            if any(a['bounds']['end'] >= b['bounds']['start'] for a, b in zip(episodes, episodes[1:])):
                reason = 'OVERLAPPING_EPISODE_BOUNDS'
            elif any(row['base'] is None for row in episodes[:-1]):
                reason = 'EVENT_AFTER_TERMINAL_OUTCOME'
            elif any(segment_origin(b) != a['base'] for a, b in zip(episodes, episodes[1:])):
                reason = 'UNSUPPORTED_EPISODE_STATE_ORDER'
        if reason is not None:
            withheld.append(dict(graph=key[0], trajectory=key[1], gap=reason))
            continue
        ordered += 1
        # A later episode bounds continuity independently of this projection.
        # No projection beyond the final episode or across a reset is inferred.
        for prior, following in zip(episodes, episodes[1:]):
            if prior['base'] is None:
                continue
            for pa, bounds in by_half[(key[0], game, half)]:
                if (pa in seen_pas
                        or not (prior['bounds']['end'] < bounds['start'] < bounds['end'] < following['bounds']['start'])):
                    continue
                evidence = {key[1], interval, half, *expected,
                            *(row[field] for row in episodes for field in ('act', 'resolution')),
                            prior['safeJudgment'], prior['safeDecision'], prior['destinationBase'],
                            *(row[field] for row in (prior['bounds'], bounds, following['bounds'])
                              for field in ('entity', 'paInterval', 'paStartInstant', 'paEndInstant',
                                            'paStartTimestamp', 'paEndTimestamp'))}
                # The complete interval being projected lies between these two
                # adjacent members of the independently checked whole. Earlier
                # observations do not replace the most recent Safe evidence.
                events = [dict(event=row['resolution'], ordinal=2 * index, base=row['base'],
                               known=True, changesState=row['changes'])
                          for index, row in enumerate((prior, following))]
                projected = project_runner_boundary(events, 1, history_complete=True,
                                                     boundary_supported=True, evidence=evidence)
                if projected['status'] == 'available':
                    states.append(dict(projected, graph=key[0], game=game, runner=runner, trajectory=key[1],
                                       plateAppearance=pa, halfInning=half,
                                       boundaryScope='unchanged throughout this plate appearance',
                                       beforeEpisode=following['episode'], afterEpisode=prior['episode'],
                                       completePlateAppearance=False, populationComplete=False))
    identities = defaultdict(list)
    for state in states:
        identities[(state['graph'], state['plateAppearance'], state['runner'])].append(state)
    ambiguous = [key for key, values in identities.items() if len(values) != 1]
    states = [values[0] for values in identities.values() if len(values) == 1]
    return {'states': sorted(states, key=lambda row: (row['graph'], row['plateAppearance'], row['runner'], row['trajectory'])),
            'coverage': {'historiesChecked': len(histories), 'historiesWithSupportedOrder': ordered,
                         'unchangedRunnerPAs': len(states), 'withheldHistories': withheld,
                         'ambiguousRunnerPAs': len(ambiguous),
                         'populationComplete': False,
                         'boundaryScope': 'intervening PAs strictly between supported episode bounds'}}


def segment_origin(row):
    """Actual segment start; keep the batter-consequence HOME override scoped."""
    if row.get('originDesignation') or row.get('originBase') or row.get('originCode'):
        if (row.get('originDesignation') and row.get('originBase')
                and row.get('originCode') in {'1B', '2B', '3B'}):
            return int(row['originCode'][0])
    elif (row.get('runner') and row.get('metricOrigin') == '0'
          and row.get('runner') == row.get('batter')):
        return 0
    return None


def run_construction_evidence(rows, *, metric_id='run-construction-depth'):
    """Complete per-run depth over promoted E1/C1 wholes and exact members.

    Never infer a whole from adjacent movement rows. The independent C1 member
    inventory ensures a missing movement binding cannot shorten a scored run.
    Source reconciliation and source SHACL precede graph promotion in NiFi.
    """
    if metric_id not in {'run-construction-depth','run-construction-breadth'}:
        raise EvidenceError('Not a run-construction metric')
    histories, movements, pa_types = defaultdict(list), defaultdict(list), defaultdict(set)
    observed_runs, run_histories, failures = {}, defaultdict(set), {}
    for row in rows:
        if row['kind'] == 'runner_history':
            histories[(row['graph'], row['trajectory'])].append(row)
        elif row['kind'] == 'runner_movement' and row.get('trajectory'):
            movements[(row['graph'], row['trajectory'])].append(row)
            if row.get('hasRunType') == 'true':
                run_histories[(row['graph'], row['resolution'])].add((row['graph'], row['trajectory']))
        elif row['kind'] == 'run':
            observed_runs[(row['graph'], row['entity'])] = row['game']
        elif row['kind'] == 'plate_appearance' and row.get('recognizedBattingResult') in ('true','1'):
            pa_types[(row['graph'],row['entity'])].add(row.get('paResultType'))
    results = []
    for key, members in sorted(histories.items()):
        signatures = {(r['game'], r['player'], r['trajectoryHalf'], r['trajectoryInterval']) for r in members}
        if len(signatures) != 1:
            failures[key] = 'CONFLICTING_PERSONAL_HISTORY'
            continue
        game, runner, half, interval = next(iter(signatures))
        expected = {r['episode'] for r in members}
        observed = defaultdict(list)
        for row in movements[key]:
            observed[row.get('episode')].append(row)
        if set(observed) != expected:
            failures[key] = 'PERSONAL_HISTORY_MEMBER_COVERAGE'
            continue
        inputs, supporters, trace, runs = [], [], [], []
        for episode in sorted(expected):
            candidates = observed[episode]
            # Optional paths may have duplicates; conflicting or missing state
            # facts must remain visible instead of selecting the first value.
            fields = ('game', 'runner', 'act', 'resolution', 'batter', 'metricOrigin',
                      'originDesignation', 'originBase', 'originCode', 'hasSafeType',
                      'hasOutType', 'hasRunType', 'destinationBase', 'destinationCode',
                      'trajectoryHalf', 'trajectoryInterval')
            states = {tuple(r.get(f) for f in fields) for r in candidates}
            if metric_id == 'run-construction-breadth':
                states = {tuple(r.get(f) for f in (*fields, 'plateAppearance','contactPlay','award','awardRule','independentStealAct'))
                          for r in candidates}
            if len(states) != 1:
                failures[key] = 'CONFLICTING_SEGMENT_STATE'
                break
            row = candidates[0]
            if (row.get('game') != game or row.get('runner') != runner or row.get('trajectoryHalf') != half
                    or row.get('trajectoryInterval') != interval or row.get('metricOrigin') not in {'0', '1', '2', '3'}
                    or row.get('hasOutType') != 'false'):
                failures[key] = 'UNSUPPORTED_SCORING_HISTORY'
                break
            if row.get('hasRunType') == 'true' and row.get('hasSafeType') == 'false':
                end = 4; runs.append(row['resolution'])
            elif row.get('hasRunType') == 'false' and row.get('hasSafeType') == 'true' and row.get('destinationCode') in {'1B', '2B', '3B'}:
                end = int(row['destinationCode'][0])
            else:
                failures[key] = 'UNSUPPORTED_SEGMENT_END'
                break
            # metricOrigin belongs to the batter-attributed consequence: it is
            # HOME=0 for that PA's batter even after the batter reaches base.
            # Run depth counts each actual segment's state change instead.
            # An explicit segment origin takes priority and must not disappear
            # behind that analytical HOME override, including conflicting codes.
            start = segment_origin(row)
            if start is None:
                failures[key] = 'UNSUPPORTED_SEGMENT_ORIGIN'
                break
            inputs.append(dict(key=key[1], episode=episode, changesState=start != end))
            if metric_id == 'run-construction-breadth' and start != end:
                if end <= start:
                    failures[key] = 'UNSUPPORTED_CONTRIBUTION_DIRECTION'
                    break
                channels = [bool(row.get('contactPlay')), bool(row.get('award') and row.get('awardRule')),
                            row.get('independentStealAct') == row['act']]
                if sum(channels) != 1:
                    failures[key] = 'UNSUPPORTED_RUN_CONTRIBUTOR'
                    break
                contributor = runner if channels[2] else row.get('batter')
                if not contributor:
                    failures[key] = 'UNSUPPORTED_RUN_CONTRIBUTOR'
                    break
                if not channels[2]:
                    types = pa_types[(key[0],row['plateAppearance'])]
                    if len(types) != 1:
                        failures[key] = 'UNSUPPORTED_BATTING_CREDIT_CLASSIFICATION'
                        break
                    if next(iter(types)) in policies()['batterProgressExcludedResultTypes']:
                        contributor = None
                if contributor:
                    supporters.append(dict(key=key[1],episode=episode,supporter=contributor,
                        channel='independent-running' if channels[2] else 'batting',
                        support=row['act'] if channels[2] else row['contactPlay'] if channels[0] else row['award']))
            trace.append(dict(episode=episode, act=row['act'], resolution=row['resolution'],
                              start=start, end=end, changesState=start != end))
        else:
            if len(runs) != 1:
                failures[key] = 'SCORING_HISTORY_TERMINAL_COVERAGE'
                continue
            calculated = (calculate(metric_id, inputs) if metric_id == 'run-construction-depth'
                          else calculate(metric_id, supporters) if supporters else available(0))
            calculated.update(graph=key[0], game=game, trajectory=key[1], runner=runner,
                              run=runs[0], grain='run', completeTrajectory=True, episodes=trace,
                              scope='complete admitted scoring-runner history',
                              evidence=sorted({key[1], interval, half, *expected, *runs}))
            if metric_id == 'run-construction-breadth':
                calculated['contributors'] = sorted({s['supporter'] for s in supporters})
                calculated['contributions'] = [{k:v for k,v in s.items() if k!='key'} for s in supporters]
                calculated['evidence'] = sorted({*calculated['evidence'],
                    *(s['support'] for s in supporters), *calculated['contributors']})
            results.append(calculated)
    # A counted Run must have one supported personal history. Never pick the
    # first candidate or count it twice when two wholes claim the same Run.
    supported = {(run['graph'], run['run']): run for run in results
                 if len(run_histories[(run['graph'], run['run'])]) == 1
                 and (run['graph'], run['run']) in observed_runs}
    unresolved = []
    for key, game in sorted(observed_runs.items()):
        if key in supported:
            continue
        owners = run_histories[key]
        if len(owners) > 1:
            reasons = ['AMBIGUOUS_SCORING_HISTORY']
        elif not owners:
            reasons = ['MISSING_PERSONAL_SCORING_HISTORY']
        else:
            owner, = owners
            reasons = [failures.get(owner, 'MISSING_PERSONAL_SCORING_HISTORY')]
        unresolved.append(dict(graph=key[0], game=game, run=key[1], status='unavailable',
                               value=None, gaps=reasons,
                               trajectories=sorted(owner[1] for owner in owners)))
    return {'runs': [supported[key] for key in sorted(supported)], 'unresolvedRuns': unresolved}


def scoring_run_players(rows, *, graphs, admissions, date_scope, schedule, evidence):
    """Pool complete run histories by scorer after independent source admission.

    Counted-run membership, C1 member coverage, complete selected schedules and
    game rosters are separate gates. This does not infer official PA credit or
    require a batting minimum for a pinch runner.
    """
    metric_id = evidence.get('metricId', 'run-construction-depth')
    if metric_id not in {'run-construction-depth','run-construction-breadth'}:
        raise EvidenceError('Not a scoring-run player metric')
    missing = dict(playerPopulationComplete=False, playerResults=[])
    denied = sorted(g for g in graphs if admissions.get(g, {}).get('status') != 'admitted'
                    or admissions[g].get('sourceReconciled') is not True
                    or admissions[g].get('graphConforms') is not True)
    blockers = []
    if not graphs or denied:
        blockers.append('COUNTED_RUN_POPULATION')
    if schedule.get('complete') is not True:
        blockers.append('COMPLETE_SELECTED_SCHEDULE')
    if evidence['unresolvedRuns']:
        blockers.append('COMPLETE_SCORING_HISTORIES')
    if blockers:
        return dict(missing, playerSummaryGaps=blockers,
                    playerCoverage=dict(withheldGraphs=denied, unresolvedRuns=len(evidence['unresolvedRuns'])))
    graph_set = set(graphs)
    exposure, game_rosters = defaultdict(set), defaultdict(set)
    observed = {}
    for row in rows:
        if row['graph'] not in graph_set:
            raise EvidenceError('Run population escaped the selected graphs')
        if row['kind'] == 'run':
            key = (row['graph'], row['entity'])
            if key in observed and observed[key] != row['game']:
                raise EvidenceError('Counted Run has conflicting game scope')
            observed[key] = row['game']
        elif row['kind'] == 'player_team_game':
            if not all(row.get(f) for f in ('player','game','team','teamRole')):
                raise EvidenceError('Admitted run population lacks complete game roster bindings')
            if not re.fullmatch(r'https://baseballontology[.]org/data/player/[0-9]+', row['player']):
                raise EvidenceError('Invalid scoring population player identity')
            exposure[row['player']].add((row['game'], row['team']))
            game_rosters[(row['graph'], row['game'])].add(row['player'])
    if {g for g, _ in game_rosters} != graph_set:
        raise EvidenceError('Admitted run population lacks a selected game roster')
    runs = _unique(evidence['runs'], ('graph','run'))
    if {(r['graph'], r['run']) for r in runs} != set(observed):
        return dict(missing, playerSummaryGaps=['COMPLETE_SCORING_HISTORIES'])
    grouped = defaultdict(list)
    for run in runs:
        if (run.get('status') != 'available' or run.get('completeTrajectory') is not True
                or observed[(run['graph'], run['run'])] != run['game']
                or run.get('runner') not in game_rosters[(run['graph'], run['game'])]):
            return dict(missing, playerSummaryGaps=['COMPLETE_SCORING_HISTORIES'])
        value = fraction(run['value'])
        if exact(value) != run['value'] or value.denominator != 1 or value < (metric_id == 'run-construction-depth'):
            raise EvidenceError('Run metric requires an exact nonnegative count; depth must be positive')
        grouped[run['runner']].append(value)
    output = []
    for player, values in sorted(grouped.items()):
        games = exposure[player]
        if len({game for game, _ in games}) != len(games):
            raise EvidenceError('One player has conflicting team exposure in a selected game')
        total = sum(values, Fraction())
        output.append(dict(player=player, metricId=metric_id, status='available',
            dateScope=dict(date_scope), completeParticipation=True, teamGames=len(games),
            graphs=sorted({r['graph'] for r in runs if r['runner']==player}),
            aggregate=dict(kind='mean', sum=exact(total), count=len(values)), value=exact(total/len(values))))
    summary = summarize(runs) if runs else unavailable('EMPTY_DENOMINATOR')
    return dict(playerPopulationComplete=True, playerResults=output, playerSummaryGaps=[],
                status=summary['status'], value=summary['value'], gaps=summary['gaps'],
                coverage={**evidence.get('coverage', {}), 'populationComplete':True},
                scope='Complete selected-period scoring-run population; player means are by scoring runner.',
                playerCoverage=dict(admittedGames=len(graph_set), countedRuns=len(runs),
                                    scoringPlayers=len(output), rosteredPlayers=len(exposure)))


def loaded_award_consequences(rows, *, metric_id='tfs'):
    """Select bounded award consequences in SPARQL, retaining incomplete PAs.

    This does not admit a whole-PA score or erase the general TFS prerequisites.
    Python groups/serializes evidence; the query owns analytical eligibility and
    exact calculation. No unknown out count is replaced with zero.
    """
    if metric_id not in {'tfs', 'offensive-reach'}:
        raise EvidenceError('Unsupported award-consequence metric')
    groups = defaultdict(dict)
    for row in rows:
        if row['kind'] == 'runner_movement':
            groups[_json([row['graph'], row['plateAppearance']])][_json(row)] = row
    candidates = {key: observations for key, observations in groups.items()
                  if any(r.get('award') for r in observations.values())}
    inputs = [dict(row, key=key, binding=identity)
              for key, observations in candidates.items() for identity, row in observations.items()]
    if not inputs:
        return []
    results = []
    for calculated in run_kernel('loaded-award-tfs', inputs):
        observations = list(candidates[calculated['key']].values())
        first = observations[0]
        evidence_fields = ('plateAppearance', 'batter', 'runner', 'award', 'awardRule',
                           'act', 'resolution', 'episode', 'record', 'originDesignation',
                           'originRecord', 'originBase', 'safeJudgment', 'safeDecision', 'destinationBase')
        value = Fraction(calculated['numerator'], calculated['denominator'])
        components = {'progress': exact(value), 'destruction': exact(0), 'erosion': exact(0)}
        if metric_id == 'offensive-reach':
            # The shared SPARQL selection proves strictly positive attributed
            # progress for every counted runner; no source rows or generic
            # participants outside that admitted consequence enter this count.
            value = Fraction(calculated['offensiveReach'])
            components = {'positiveTrajectories': exact(value)}
        results.append(available(value, graph=first['graph'], game=first['game'],
            plateAppearance=first['plateAppearance'], batter=first['batter'], award=first['award'],
            grain='award_consequence', scope='positively supported loaded Walk/HBP force chain',
            completePlateAppearance=False,
            components=components,
            evidence=[r[f] for r in observations for f in evidence_fields if f in r],
            movements=sorted(observations, key=lambda r: r['metricOrigin'])))
    return sorted(results, key=lambda r: (r['graph'], r['plateAppearance'], r['award']))


PROGRESS_METRICS = {'offensive-reach','hidden-help-rate','empty-game-rate','contribution-path-diversity'}


def batting_progress_evidence(rows):
    """Complete single-resolution contributions; population admission is separate.

    A repeated resolution in one attributed consequence still needs supported
    coalescence. It cannot become two positives or retain progress before an
    out. Different supported channels remain separate contributions.
    """
    pas, movements = defaultdict(list), defaultdict(list)
    for row in rows:
        if row['kind']=='plate_appearance':pas[(row['graph'],row['entity'])].append(row)
        elif row['kind']=='runner_movement':movements[(row['graph'],row['plateAppearance'])].append(row)
    completed, withheld = [], []
    fields=('runner','act','episode','resolution','originDesignation','originBase','originCode',
            'metricOrigin','destinationBase','destinationCode','safeJudgment','safeDecision',
            'hasSafeType','hasOutType','hasRunType','contactPlay','award','awardRule','independentStealAct')
    for (graph,pa), observations in sorted(pas.items()):
        reasons=[]
        players={r.get('player') for r in observations};games={r.get('game') for r in observations}
        types={r['paResultType'] for r in observations if r.get('recognizedBattingResult') in ('true','1')}
        if len(players)!=1 or None in players or len(games)!=1 or len(types)>1:
            withheld.append(dict(graph=graph,plateAppearance=pa,gaps=['AMBIGUOUS_BATTING_CONTRIBUTOR']));continue
        player,=players;game,=games
        excluded=bool(types & set(policies()['batterProgressExcludedResultTypes']))
        resolutions=defaultdict(list)
        for row in movements[(graph,pa)]:resolutions[row['resolution']].append(row)
        channels, independent, other = defaultdict(list), [], set()
        positive_channels=set();independent_episodes=[];independent_gaps=[]
        unsupported_outs=set();positive_runners=set()
        self_positive=False
        for resolution,candidates in resolutions.items():
            if len({tuple(r.get(f) for f in fields) for r in candidates})!=1:
                reasons.append('CONFLICTING_SEGMENT_STATE');continue
            row=candidates[0];runner=row.get('runner')
            if not runner or not row.get('episode') or not row.get('act'):
                reasons.append('MISSING_RUNNER_PARTICIPATION');continue
            outcome=(row.get('hasSafeType'),row.get('hasOutType'),row.get('hasRunType'))
            if outcome not in {('true','false','false'),('false','true','false'),('false','false','true')}:
                reasons.append('UNSUPPORTED_SEGMENT_END');continue
            supports=[]
            if row.get('contactPlay'):supports.append(('contact',row['contactPlay']))
            if row.get('award') and row.get('awardRule'):supports.append(('award',row['award']))
            if row.get('independentStealAct')==row['act']:supports.append(('running',row['act']))
            # An out has no positive terminal progress, but it must still join
            # any same-contact continuation so earlier safe progress is not kept.
            positive=False
            if outcome[1]!='true':
                start=segment_origin(row)
                end=4 if outcome[2]=='true' else int(row['destinationCode'][0]) if row.get('destinationCode') in {'1B','2B','3B'} else None
                if start is None or end is None or end<start:
                    reasons.append('UNSUPPORTED_PROGRESS_BOUNDARY');continue
                positive=end>start
            if positive:positive_runners.add(runner)
            if outcome[1]=='true' and not supports:
                unsupported_outs.add(runner)
                if runner!=player:independent_gaps.append('UNRESOLVED_RUNNING_EPISODE_ATTRIBUTION')
            if len(supports)>1 or (positive and len(supports)!=1):
                reasons.append('UNRESOLVED_PROGRESS_ATTRIBUTION');continue
            if supports:
                channel,support=supports[0]
                channels[(runner,channel,support)].append((row,positive))
        if positive_runners & unsupported_outs:
            reasons.append('COMPLETE_CONSEQUENCE_COALESCENCE')
        for (runner,channel,support), members in channels.items():
            if len(members)!=1:
                reasons.append('COMPLETE_CONSEQUENCE_COALESCENCE');continue
            row,positive=members[0]
            if channel=='running':
                independent_episodes.append(dict(player=runner,episode=row['episode'],support=support))
                if row.get('hasOutType')=='true' and any(t.endswith('/StrikeoutProcess') for t in types):
                    # K + CS does not establish whether this was the accepted
                    # batter-owned failed hit-and-run or an independent attempt.
                    independent_gaps.append('STRIKEOUT_RUNNING_OUT_STRATEGY_UNRESOLVED')
            if not positive:continue
            if channel=='running':
                independent.append(dict(player=runner,episode=row['episode'],support=support))
                positive_channels.add((runner,row['episode'],'runner_self'))
            elif not types:
                reasons.append('UNRESOLVED_BATTING_RESULT')
            elif not excluded:
                if runner==player:self_positive=True
                else:other.add(runner)
                positive_channels.add((player,support,'batter_self' if runner==player else 'batter_other'))
        if types and player not in {r.get('runner') for r in movements[(graph,pa)]}:
            reasons.append('MISSING_BATTER_RESOLUTION')
        if reasons:
            withheld.append(dict(graph=graph,plateAppearance=pa,gaps=sorted(set(reasons))));continue
        completed.append(dict(graph=graph,game=game,plateAppearance=pa,player=player,
            officialResult=bool(types),batterPositive=self_positive,otherPositivePlayers=sorted(other),
            independentPositive=independent,
            independentEpisodes=independent_episodes,independentEpisodeGaps=sorted(set(independent_gaps)),
            positiveChannels=[dict(player=p,play=play,channel=channel) for p,play,channel in sorted(positive_channels)],
            evidence=sorted({r[f] for r in movements[(graph,pa)] for f in
                ('resolution','act','episode','contactPlay','award','awardRule','independentStealAct') if r.get(f)})))
    inputs=[]
    for pa in completed:
        key=_json([pa['graph'],pa['plateAppearance']])
        # Reach uses only positivity; these integer indicators do not stand for
        # a measured distance or an invented TFS magnitude.
        inputs.append(dict(key=key,participant=pa['player'],progress36=int(pa['batterPositive'])))
        inputs.extend(dict(key=key,participant=p,progress36=1) for p in pa['otherPositivePlayers'])
    reach={r['key']:int(r['numerator']) for r in run_kernel('offensive-reach',inputs)}
    for pa in completed:pa['reach']=reach[_json([pa['graph'],pa['plateAppearance']])]
    return dict(plateAppearances=completed,unresolvedPlateAppearances=withheld)


def batting_progress_players(metric_id, rows, *, graphs, admissions, qualification, date_scope):
    if metric_id not in PROGRESS_METRICS:raise EvidenceError('Not a batting-progress metric')
    missing=dict(playerPopulationComplete=False,playerResults=[])
    denied=[g for g in graphs if admissions.get(g,{}).get('status')!='admitted'
            or admissions[g].get('sourceReconciled') is not True or admissions[g].get('graphConforms') is not True]
    reasons=[]
    if not graphs or denied:reasons.append('COMPLETE_RUNNER_RESOLUTION_POPULATION')
    if not qualification['officialPlateAppearanceCreditVerified']:reasons.append('OFFICIAL_PA_POPULATION')
    if not qualification['teamGameExposureVerified']:reasons.append('COMPLETE_SELECTED_SCHEDULE')
    if reasons:return dict(missing,playerSummaryGaps=reasons)
    if any(r['graph'] not in set(graphs) for r in rows):raise EvidenceError('Progress escaped selected graphs')
    evidence=batting_progress_evidence(rows)
    if evidence['unresolvedPlateAppearances']:
        return dict(missing,playerSummaryGaps=['COMPLETE_PA_PROGRESS'],progressEvidence=evidence)
    pas=evidence['plateAppearances'];expected=qualification['expectedObservations']
    if {(p['graph'],p['plateAppearance'],p['player']) for p in pas if p['officialResult']} != {
            (p['graph'],p['plateAppearance'],p['player']) for p in expected}:
        return dict(missing,playerSummaryGaps=['COMPLETE_PA_PROGRESS'])
    if metric_id=='contribution-path-diversity':
        return contribution_mix_players(evidence,qualification=qualification,date_scope=date_scope)
    people=qualification['participation'];output=[]
    by_player=defaultdict(list);running=defaultdict(set)
    for pa in pas:
        if pa['officialResult']:by_player[pa['player']].append(pa)
        for episode in pa['independentPositive']:running[(episode['player'],pa['game'])].add(episode['episode'])
    kernel_inputs=[]
    if metric_id=='hidden-help-rate':
        kernel_inputs=[dict(key=pa['player'],pa=_json([pa['graph'],pa['plateAppearance']]),
            batterProgress36=int(pa['batterPositive']),otherProgress36=int(bool(pa['otherPositivePlayers'])))
            for pa in pas if pa['officialResult']]
    elif metric_id=='empty-game-rate':
        for player,observations in by_player.items():
            by_game=defaultdict(list)
            for pa in observations:by_game[pa['game']].append(pa)
            kernel_inputs.extend(dict(key=player,game=game,plateAppearances=len(ps),
                positiveEpisodes=sum(p['reach'] for p in ps)+len(running[(player,game)])) for game,ps in by_game.items())
    counted={r['key']:r for r in run_kernel(metric_id,kernel_inputs)} if kernel_inputs else {}
    for person in people:
        player=person['player'];observations=by_player[player]
        if not person['plateAppearances']:continue
        if len(observations)!=person['plateAppearances']:
            return dict(missing,playerSummaryGaps=['COMPLETE_PA_PROGRESS'])
        games=person['teamGameExposure']
        if len({g['game'] for g in games})!=len(games):raise EvidenceError('Conflicting progress team exposure')
        if metric_id=='offensive-reach':
            count=len(observations);total=sum(p['reach'] for p in observations)
            aggregate=dict(kind='mean',sum=exact(total),count=count);value=exact(Fraction(total,count))
        elif metric_id=='hidden-help-rate':
            total=int(counted[player]['numerator']);count=int(counted[player]['denominator'])
            if not count:continue  # A known empty denominator has no rate.
            aggregate=dict(kind='mean',sum=exact(total),count=count);value=exact(Fraction(total,count))
        else:
            total=int(counted[player]['numerator']);eligible=int(counted[player]['denominator'])
            aggregate=dict(kind='count',count=total,eligibleGames=eligible);value=exact(total)
        output.append(dict(player=player,metricId=metric_id,status='available',dateScope=dict(date_scope),
            completeParticipation=True,plateAppearances=person['plateAppearances'],teamGames=len(games),
            graphs=sorted({p['graph'] for p in observations}),aggregate=aggregate,value=value))
    # The headline uses the same pooled applicable population as the player rows.
    if metric_id=='empty-game-rate':
        total=sum(p['aggregate']['count'] for p in output);eligible=sum(p['aggregate']['eligibleGames'] for p in output)
        summary=available(total,components=dict(emptyGames=total,eligibleGames=eligible)) if eligible else unavailable('EMPTY_DENOMINATOR')
    else:
        count=sum(p['aggregate']['count'] for p in output);total=sum((fraction(p['aggregate']['sum']) for p in output),Fraction())
        summary=available(total/count) if count else unavailable('EMPTY_DENOMINATOR')
    return dict(summary,playerPopulationComplete=True,playerResults=output,playerSummaryGaps=[],
        progressEvidence=evidence,scope='Complete selected-period batting progress and independent positive running; official PA eligibility applied.')


def contribution_mix_players(evidence, *, qualification, date_scope):
    """Pool positive play/channel occurrences after the common admission gates."""
    pas=evidence['plateAppearances']
    gaps=sorted({gap for pa in pas for gap in pa['independentEpisodeGaps']})
    if gaps:return dict(playerPopulationComplete=False,playerResults=[],playerSummaryGaps=gaps,progressEvidence=evidence)
    people={p['player']:p for p in qualification['participation']}
    inputs=[];running=defaultdict(set);graphs=defaultdict(set);official=defaultdict(int)
    for pa in pas:
        if pa['officialResult']:official[pa['player']]+=1
        for item in pa['positiveChannels']:
            player=item['player']
            if player not in people:raise EvidenceError('Contribution player lacks admitted roster exposure')
            inputs.append(dict(key=player,play=_json([pa['graph'],item['play']]),channel=item['channel']))
            graphs[player].add(pa['graph'])
        for item in pa['independentEpisodes']:
            if item['player'] not in people:raise EvidenceError('Running participant lacks admitted roster exposure')
            running[item['player']].add((pa['graph'],item['episode']))
    inputs=_unique(inputs,('key','play','channel'))
    counts={row['key']:[int(row[c]) for c in ('self','other','running')]
            for row in run_kernel('contribution-path-diversity',inputs)} if inputs else {}
    output=[]
    for player,person in sorted(people.items()):
        if official[player]!=person['plateAppearances']:
            return dict(playerPopulationComplete=False,playerResults=[],playerSummaryGaps=['COMPLETE_PA_PROGRESS'])
        score=channel_entropy(counts.get(player,[0,0,0]))
        if score['status']!='available':continue  # Known zero contribution denominator, not a zero entropy score.
        games=person['teamGameExposure']
        if len({g['game'] for g in games})!=len(games):raise EvidenceError('Conflicting contribution team exposure')
        output.append(dict(score,player=player,metricId='contribution-path-diversity',dateScope=dict(date_scope),
            completeParticipation=True,plateAppearances=official[player],teamGames=len(games),
            independentRunningEpisodes=len(running[player]),graphs=sorted(graphs[player]),
            aggregate=dict(kind='channel_entropy',channelCounts=counts[player])))
    summary=channel_entropy([sum(p['aggregate']['channelCounts'][i] for p in output) for i in range(3)])
    return dict(summary,playerPopulationComplete=True,playerResults=output,playerSummaryGaps=[],
        progressEvidence=evidence,scope='Complete selected-period positive play/channel counts; batting or independent-running qualification applies.')


def initialize_sql(connection):
    connection.executescript((ROOT / 'serving/metric-suite-schema.sql').read_text(encoding='utf-8'))
    connection.execute('INSERT OR REPLACE INTO metric_suite_manifest VALUES (1,?,?)', (VERSION, fingerprint()))


def store_result(connection, graph, metric_id, key, result):
    if metric_id not in {e['id'] for e in catalog()['metrics']}:
        raise EvidenceError('Unknown metric')
    canonical = _json(result)
    value = result.get('value')
    normalized = exact(fraction(value)) if value is not None else None
    if value is not None and normalized != value:
        raise EvidenceError('Result must use a normalized exact fraction')
    connection.execute('INSERT OR REPLACE INTO metric_suite_result VALUES (?,?,?,?,?,?,?,?)',
                       (graph, metric_id, key, result['status'],
                        value['numerator'] if value else None, value['denominator'] if value else None,
                        canonical, _hash(canonical)))


def read_results(connection, graph, metric_id):
    results = []
    for status, numerator, denominator, text, digest in connection.execute(
            'SELECT status,numerator,denominator,result_json,result_sha256 FROM metric_suite_result '
            'WHERE graph_iri=? AND metric_id=? ORDER BY entity_key', (graph, metric_id)):
        if _hash(text) != digest:
            raise EvidenceError('Metric SQL result checksum mismatch')
        result = json.loads(text)
        value = result.get('value')
        if result['status'] != status or (value and (value['numerator'], value['denominator']) != (numerator, denominator)):
            raise EvidenceError('Metric SQL columns disagree with exact result')
        if value is None and (numerator is not None or denominator is not None):
            raise EvidenceError('Metric SQL unavailable value mismatch')
        results.append(result)
    return results


def materialize_game(connection, graph, bindings, *, batting_admission=None, scoring_run_admission=None,
                     runner_resolution_admission=None):
    rows = normalize_bindings(bindings, [graph])
    connection.execute('DELETE FROM metric_suite_evidence WHERE graph_iri=?', (graph,))
    connection.execute('DELETE FROM metric_suite_result WHERE graph_iri=?', (graph,))
    # Caller is the NiFi materializer, which validates promotion-bound proof
    # provenance. HTTP callers have no path to submit these admission inputs.
    proof_text = _json(batting_admission or {'status':'withheld'})
    connection.execute('INSERT OR REPLACE INTO metric_suite_admission VALUES (?,?,?)',
                       (graph, proof_text, _hash(proof_text)))
    run_proof_text = _json(scoring_run_admission or {'status':'withheld'})
    connection.execute('INSERT OR REPLACE INTO metric_suite_run_admission VALUES (?,?,?)',
                       (graph, run_proof_text, _hash(run_proof_text)))
    resolution_proof_text = _json(runner_resolution_admission or {'status':'withheld'})
    connection.execute('INSERT OR REPLACE INTO metric_suite_runner_resolution_admission VALUES (?,?,?)',
                       (graph, resolution_proof_text, _hash(resolution_proof_text)))
    for row in rows:
        text = _json(row)
        connection.execute('INSERT INTO metric_suite_evidence VALUES (?,?,?)', (graph, _hash(text), text))
    for entry in catalog()['metrics']:
        result = live_result(entry['id'], rows, graph_count=1)
        store_result(connection, graph, entry['id'], 'game-scope', result)
        # Verify exact serialized result, not rounded display values. Per-game
        # proofs do not admit incomplete season percentiles.
        if read_results(connection, graph, entry['id']) != [result]:
            raise EvidenceError('Metric SQL equivalence failed: ' + entry['id'])
    return {'metrics': len(catalog()['metrics']), 'evidenceRows': len(rows), 'exactRoundTrip': True}


def requested_metric_ids(request):
    ids = [entry['id'] for entry in catalog()['metrics']]
    if request.get('view') == 'dashboard' and 'metricId' not in request:
        return ids
    if request.get('view') is not None or request.get('metricId') not in ids:
        raise EvidenceError('Unknown metric selection')
    return [request['metricId']]


def selected_results(request, rows, *, graph_count):
    ids = requested_metric_ids(request)
    results = [live_result(metric_id, rows, graph_count=graph_count) for metric_id in ids]
    return {'metrics': results} if request.get('view') == 'dashboard' else {'metric': results[0]}


def query_sql(connection, request, scope):
    manifest = connection.execute('SELECT version,implementation_sha256 FROM metric_suite_manifest WHERE singleton=1').fetchone()
    if manifest != (VERSION, fingerprint()):
        raise EvidenceError('Serving build is stale for the metric suite')
    metric_ids = requested_metric_ids(request)
    if request.get('filters'):
        raise EvidenceError('Metric suite currently supports game/date scope only')
    parameters = (scope['gameSet'], scope['startDate'], scope['endDate'])
    graphs = [r[0] for r in connection.execute(
        'SELECT graph_iri FROM game_dimension WHERE game_set=? AND official_date BETWEEN ? AND ? ORDER BY graph_iri', parameters)]
    rows = []
    admissions, run_admissions, resolution_admissions = {}, {}, {}
    for graph in graphs:
        for metric_id in metric_ids:
            if len(read_results(connection, graph, metric_id)) != 1:
                raise EvidenceError('Metric build lacks a selected game')
        for text, digest in connection.execute('SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?', (graph,)):
            if _hash(text) != digest:
                raise EvidenceError('Metric SQL evidence checksum mismatch')
            rows.append(json.loads(text))
        record = connection.execute('SELECT proof_json,proof_sha256 FROM metric_suite_admission WHERE graph_iri=?', (graph,)).fetchone()
        if record:
            text, digest = record
            if _hash(text) != digest:
                raise EvidenceError('Metric SQL admission checksum mismatch')
            admissions[graph] = json.loads(text)
        record = connection.execute('SELECT proof_json,proof_sha256 FROM metric_suite_run_admission WHERE graph_iri=?', (graph,)).fetchone()
        if record:
            text, digest = record
            if _hash(text) != digest:
                raise EvidenceError('Metric SQL run admission checksum mismatch')
            run_admissions[graph] = json.loads(text)
        record = connection.execute('SELECT proof_json,proof_sha256 FROM metric_suite_runner_resolution_admission WHERE graph_iri=?', (graph,)).fetchone()
        if record:
            text, digest = record
            if _hash(text) != digest:
                raise EvidenceError('Metric SQL runner-resolution admission checksum mismatch')
            resolution_admissions[graph] = json.loads(text)
    # Pool distinct resolved reviews; never average per-game percentages. Full
    # cohort metrics remain unavailable until their admission gaps are closed.
    result = selected_results(request, rows, graph_count=len(graphs))
    schedule = selected_schedule_coverage(connection,scope,graphs)
    qualification = batting_qualification(rows, graphs=graphs, admissions=admissions,
        date_scope=scope, selected_games_complete=schedule['complete'])
    for metric in result.get('metrics', [result.get('metric')]):
        if metric['metricId'] in {'run-construction-depth','run-construction-breadth'}:
            metric.update(scoring_run_players(rows, graphs=graphs, admissions=run_admissions,
                date_scope=scope, schedule=schedule, evidence=metric))
        if metric['metricId'] in PROGRESS_METRICS:
            metric.update(batting_progress_players(metric['metricId'],rows,graphs=graphs,
                admissions=resolution_admissions,qualification=qualification,date_scope=scope))
            if metric['playerPopulationComplete']:
                metric['coverage']={**metric['coverage'],'populationComplete':True}
    # Admission metadata is separate from scores, retaining exact equality
    # between the existing RDF calculation and its SQL result.
    result['battingQualification'] = {
        **{k:v for k,v in qualification.items() if k not in {'expectedObservations','participation'}},
        'officialPlateAppearances':len(qualification['expectedObservations']),
        'rosteredPlayers':len(qualification['participation']), 'schedule':schedule}
    return {**result,
            'implementationSha256': fingerprint(), 'dateScope': scope,
            'execution': 'materialized-sql', 'graphCount': len(graphs)}
