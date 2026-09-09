"""Graph-native calculation components over admitted SPARQL bindings.

This module never reads MLB payloads, decides graph identity, or admits source
facts. Calculations are usable independently for tests; live adapters must
report unresolved prerequisites before invoking them. Rational results retain
numerator/denominator strings. Entropy retains exact channel counts because
logarithms generally have no rational representation.
"""
from __future__ import annotations

from collections import defaultdict, deque
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
VERSION = '2.0.5'


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


def trajectories(participants, outs_before, attributed_outs, *, batter=None):
    """One already coalesced, complete attributed consequence. No raw rows."""
    _integer(outs_before, 'outs before', 0, 2)
    _integer(attributed_outs, 'attributed outs', 0, 3 - outs_before)
    rows = _unique(participants, ('participant',))
    if not rows:
        return unavailable('MISSING_PARTICIPANTS')
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
    """Input is already ordered, unique, exact post-pitch count evidence."""
    pitches = _unique(pitches, ('pitch',))
    if not pitches:
        return unavailable('EXACT_PITCH_COUNTS')
    two_strikes, steps, previous_strikes = False, 0, 0
    for index, pitch in enumerate(pitches):
        strikes = _integer(pitch.get('strikesAfter'), 'post-pitch strikes', 0, 3)
        terminal = _boolean(pitch.get('terminal'), 'terminal pitch')
        if strikes < previous_strikes or (strikes == 3 and not terminal):
            raise EvidenceError('Inconsistent operative strike-count sequence')
        previous_strikes = strikes
        if terminal and index != len(pitches) - 1:
            raise EvidenceError('A terminal pitch cannot precede another pitch in this PA')
        if two_strikes and not terminal:
            steps += 1
        two_strikes = two_strikes or strikes >= 2
    if not pitches[-1]['terminal']:
        return unavailable('INCOMPLETE_PLATE_APPEARANCE')
    if not two_strikes:
        return unavailable('NOT_TWO_STRIKE_ELIGIBLE')
    return available(steps, evidence=[p['pitch'] for p in pitches])


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
        counts = [int(result[c]) for c in ['self', 'other', 'running']]
        total = sum(counts)
        if total == 0:
            return unavailable('EMPTY_DENOMINATOR', components={'channelCounts': counts, 'pathBreadth': 0})
        probabilities = [Fraction(c, total) for c in counts]
        entropy = -sum(float(p) * math.log(float(p)) for p in probabilities if p) / math.log(3)
        return {'status': 'available', 'value': None, 'approximateValue': entropy,
                'exactExpression': '-sum(p*ln(p))/ln(3)', 'gaps': [],
                'components': {'channelCounts': counts, 'probabilities': [exact(p) for p in probabilities],
                               'pathBreadth': sum(c > 0 for c in counts)}, 'evidence': []}
    return ratio(int(result['numerator']), int(result['denominator']),
                 components={k: v for k, v in result.items() if k not in {'key', 'numerator', 'denominator'}})


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
                      'original', 'operative', 'disposition', 'plateAppearance', 'resolution',
                      'runner', 'originDesignation', 'originBase', 'destinationBase', 'batter',
                      'awardRule', 'contactPlay', 'award', 'record', 'episode',
                      'originRecord', 'safeJudgment', 'safeDecision', 'trajectory',
                      'trajectoryHalf', 'trajectoryInterval'):
            if field in binding and binding[field].get('type') != 'uri':
                raise EvidenceError('Evidence identity must be an IRI: ' + field)
        if row.get('kind') not in {'plate_appearance', 'batted_play', 'run', 'player_game', 'review', 'runner_movement'}:
            raise EvidenceError('Unknown evidence grain')
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


def live_result(metric_id, rows, *, graph_count):
    entry = next((e for e in catalog()['metrics'] if e['id'] == metric_id), None)
    if entry is None:
        raise EvidenceError('Unknown metric')
    coverage = {'games': graph_count, 'evidenceRows': len(rows),
                'observedEntities': {kind: len({(r['graph'], r['entity']) for r in rows if r['kind'] == kind})
                                     for kind in ['plate_appearance', 'batted_play', 'run', 'player_game', 'review']},
                'runnerMovements': movement_coverage(rows),
                'populationComplete': False}
    if entry['requires']:
        return unavailable(*entry['requires'], coverage=coverage, metricId=metric_id,
                           scope='selected promoted game graphs', grain=entry['grain'])
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


def materialize_game(connection, graph, bindings):
    rows = normalize_bindings(bindings, [graph])
    connection.execute('DELETE FROM metric_suite_evidence WHERE graph_iri=?', (graph,))
    connection.execute('DELETE FROM metric_suite_result WHERE graph_iri=?', (graph,))
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


def query_sql(connection, request, scope):
    manifest = connection.execute('SELECT version,implementation_sha256 FROM metric_suite_manifest WHERE singleton=1').fetchone()
    if manifest != (VERSION, fingerprint()):
        raise EvidenceError('Serving build is stale for the metric suite')
    metric_id = request.get('metricId')
    if metric_id not in {e['id'] for e in catalog()['metrics']}:
        raise EvidenceError('Unknown metric')
    if request.get('filters'):
        raise EvidenceError('Metric suite currently supports game/date scope only')
    parameters = (scope['gameSet'], scope['startDate'], scope['endDate'])
    graphs = [r[0] for r in connection.execute(
        'SELECT graph_iri FROM game_dimension WHERE game_set=? AND official_date BETWEEN ? AND ? ORDER BY graph_iri', parameters)]
    rows = []
    for graph in graphs:
        if len(read_results(connection, graph, metric_id)) != 1:
            raise EvidenceError('Metric build lacks a selected game')
        for text, digest in connection.execute('SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?', (graph,)):
            if _hash(text) != digest:
                raise EvidenceError('Metric SQL evidence checksum mismatch')
            rows.append(json.loads(text))
    # Pool distinct resolved reviews; never average per-game percentages. Full
    # cohort metrics remain unavailable until their admission gaps are closed.
    return {'metric': live_result(metric_id, rows, graph_count=len(graphs)),
            'implementationSha256': fingerprint(), 'dateScope': scope,
            'execution': 'materialized-sql', 'graphCount': len(graphs)}
