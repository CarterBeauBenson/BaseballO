"""Indexed analytical inputs projected once from accepted game evidence.

These are disposable SQL products, not new RDF terms or source admissions.
Scalar identities/values support selection and joins; record JSON retains the
existing exact reducer contract and diagnostic detail. Requests never project
runner histories, pitch histories or graph patterns from these records.
"""
from collections import defaultdict
from copy import deepcopy

VERSION = 1
INPUTS = {
    'tfs': ('contribution', 'contributionInputs', 'plateAppearances'),
    'recovery-quality': ('recovery', 'recoveryInputs', 'plateAppearances'),
    'resolution-depth': ('defense', 'defensiveInputs', 'resolutions'),
    'paq-2.1': ('paq21', 'paq21Inputs', 'plateAppearances'),
    'empty-game-rate': ('progress', 'progressInputs', 'plateAppearances'),
}
SCOPE_FIELDS = {
    'plate_appearance': ('graph','game','kind','entity','player','act','recognizedBattingResult',
        'paResult','paResultType','paResultJudgment','paResultDecision','paResultRecord'),
    'player_team_game': ('graph','game','kind','entity','player','team','teamRole','playerTeamRole'),
    'run': ('graph','game','kind','entity'),
    'batted_play': ('graph','game','kind','entity'),
}


def batches(graphs):
    graphs = sorted(set(graphs))
    for offset in range(0, len(graphs), 800):
        yield graphs[offset:offset+800]


def placeholders(values):
    return ','.join('?' for _ in values)


def decode(m, text, digest):
    if m._hash(text) != digest:
        raise m.EvidenceError('Metric building block checksum mismatch')
    import json
    return json.loads(text)


def row_columns(m, record):
    entity = record.get('resolution') or record.get('plateAppearance')
    value = record.get('value') or record.get('score', {}).get('value')
    # PAQ-2.1 retains the contribution fraction directly in score.
    if value is None and isinstance(record.get('score'), dict) and 'numerator' in record['score']:
        value = record['score']
    eligible = record.get('twoStrikeEligible', record.get('officialResult'))
    return (entity, record.get('player'), record.get('game'),
            int(eligible) if type(eligible) is bool else None,
            value['numerator'] if value is not None else None,
            value['denominator'] if value is not None else None)


def store_input(m, connection, graph, family, product, member_key):
    connection.execute('DELETE FROM metric_suite_input_row WHERE graph_iri=? AND family=?', (graph, family))
    state = {k:v for k,v in product.items() if k != member_key}
    records = product.get(member_key, [])
    for record in records:
        if record.get('graph', graph) != graph:
            raise m.EvidenceError('Metric input escaped its graph')
        columns = row_columns(m, record)
        if not columns[0]:
            raise m.EvidenceError('Metric input lacks its observation identity')
        text = m._json(record)
        connection.execute('INSERT INTO metric_suite_input_row VALUES (?,?,?,?,?,?,?,?,?,?)',
            (graph, family, *columns, text, m._hash(text),))
    text = m._json(state)
    connection.execute('INSERT OR REPLACE INTO metric_suite_input_state VALUES (?,?,?,?,?,?)',
        (graph, family, member_key, len(records), text, m._hash(text)))


def store_metric(m, connection, graph, metric_id, result):
    projection = INPUTS.get(metric_id)
    if projection and projection[1] in result:
        family, key, members = projection
        store_input(m, connection, graph, family, result[key], members)
    shell = {k:v for k,v in result.items() if k not in {p[1] for p in INPUTS.values()}}
    text = m._json(shell)
    connection.execute('INSERT OR REPLACE INTO metric_suite_shell VALUES (?,?,?,?)',
        (graph, metric_id, text, m._hash(text)))


def store_game(m, connection, graph, rows):
    connection.execute('DELETE FROM metric_suite_scope_fact WHERE graph_iri=?', (graph,))
    facts = {m._json({k:r[k] for k in SCOPE_FIELDS[r['kind']] if k in r})
             for r in rows if r['kind'] in SCOPE_FIELDS}
    import json
    for text in sorted(facts):
        row = json.loads(text)
        connection.execute('INSERT INTO metric_suite_scope_fact VALUES (?,?,?,?,?,?,?,?)',
            (graph, row['kind'], row['entity'], row.get('player'), row['game'],
             m._hash(text), text, m._hash(text)))
    connection.execute('INSERT OR REPLACE INTO metric_suite_block_manifest VALUES (?,?,?)',
        (graph, VERSION, len(facts)))


def read_scope(m, connection, graphs):
    output = []
    for group in batches(graphs):
        marks = placeholders(group)
        manifests = dict((g,(v,n)) for g,v,n in connection.execute(
            f'SELECT graph_iri,version,scope_rows FROM metric_suite_block_manifest WHERE graph_iri IN ({marks})', group))
        counts = defaultdict(int)
        for graph, kind, entity, player, game, key, text, digest in connection.execute(
                f'SELECT * FROM metric_suite_scope_fact WHERE graph_iri IN ({marks}) ORDER BY graph_iri,record_json', group):
            row = decode(m, text, digest)
            if (graph,kind,entity,player,game,key) != (row['graph'],row['kind'],row['entity'],row.get('player'),row['game'],digest):
                raise m.EvidenceError('Metric scope columns disagree with retained record')
            output.append(row); counts[graph] += 1
        if any(manifests.get(g) != (VERSION, counts[g]) for g in group):
            raise m.EvidenceError('Metric build lacks current game building blocks')
    return output


def read_inputs(m, connection, family, graphs):
    output = {}
    for group in batches(graphs):
        marks = placeholders(group)
        metric_id = next(metric for metric,(name,_,_) in INPUTS.items() if name == family)
        current = {row[0] for row in connection.execute(
            f'SELECT b.graph_iri FROM metric_suite_block_manifest b JOIN metric_suite_shell s USING(graph_iri) '
            f'WHERE b.version=? AND s.metric_id=? AND b.graph_iri IN ({marks})', [VERSION,metric_id,*group])}
        if current != set(group):
            raise m.EvidenceError('Metric input checksum provenance is no longer current')
        states = {}
        for graph, member_key, count, text, digest in connection.execute(
                f'SELECT graph_iri,member_key,row_count,state_json,state_sha256 FROM metric_suite_input_state '
                f'WHERE family=? AND graph_iri IN ({marks})', [family, *group]):
            states[graph] = (member_key, count)
            output[graph] = {**decode(m, text, digest), member_key:[]}
        if set(states) != set(group):
            raise m.EvidenceError('Metric build lacks input family: ' + family)
        for graph, entity, player, game, eligible, numerator, denominator, text, digest in connection.execute(
                f'SELECT graph_iri,entity_iri,player_iri,game_iri,eligible,numerator,denominator,record_json,record_sha256 '
                f'FROM metric_suite_input_row WHERE family=? AND graph_iri IN ({marks}) ORDER BY graph_iri,entity_iri', [family,*group]):
            record = decode(m, text, digest)
            if (entity,player,game,eligible,numerator,denominator) != row_columns(m, record):
                raise m.EvidenceError('Metric input columns disagree with exact record')
            if record.get('graph', graph) != graph:
                raise m.EvidenceError('Metric input escaped its retained graph')
            output[graph][states[graph][0]].append(record)
        if any(len(output[g][key]) != count for g,(key,count) in states.items()):
            raise m.EvidenceError('Metric input observation census mismatch')
    return output


def progress(m, connection, graphs):
    inputs = read_inputs(m, connection, 'progress', graphs)
    return {key:sorted([row for g in sorted(inputs) for row in inputs[g].get(key,[])],
                       key=lambda row:(row['graph'],row['plateAppearance']))
            for key in ('plateAppearances','unresolvedPlateAppearances')}


def _coverage(m, products, graph_count):
    base = m._EvidenceEvaluation([], 0).coverage()
    coverages = [p['coverage'] for p in products]
    base['games'] = graph_count
    base['evidenceRows'] = sum(c['evidenceRows'] for c in coverages)
    for key in base['observedEntities']:
        base['observedEntities'][key] = sum(c['observedEntities'][key] for c in coverages)
    for key in base['runnerMovements']:
        if key != 'populationComplete':
            base['runnerMovements'][key] = sum(c['runnerMovements'][key] for c in coverages)
    batting = base['battingParticipation']; people = defaultdict(int)
    for key in ('observedPlateAppearances','withOneBatter','withMultipleBatters','withoutBatter'):
        batting[key] = sum(c['battingParticipation'][key] for c in coverages)
    for coverage in coverages:
        for person in coverage['battingParticipation']['players']:
            people[person['player']] += person['observedPlateAppearances']
    batting['players'] = [dict(player=p,observedPlateAppearances=n) for p,n in sorted(people.items())]
    return base


def merge_metric(m, metric_id, products, graph_count):
    # An empty selection has no graph work; use the established empty response.
    if not products:
        return m.live_result(metric_id, [], graph_count=graph_count)
    coverage = _coverage(m, products, graph_count)
    entry = next(e for e in m.catalog()['metrics'] if e['id'] == metric_id)
    concatenate = lambda key:[row for product in products for row in product.get(key, [])]
    if entry['requires']:
        result = deepcopy(products[0]); result['coverage'] = coverage
        if metric_id in {'run-construction-depth','run-construction-breadth'}:
            for key in ('runs','unresolvedRuns'): result[key] = concatenate(key)
            coverage.update(supportedRuns=len(result['runs']),observedRunsWithoutResult=len(result['unresolvedRuns']))
            coverage['runGapCounts'] = dict(sorted((gap,sum(gap in r['gaps'] for r in result['unresolvedRuns']))
                for gap in {gap for r in result['unresolvedRuns'] for gap in r['gaps']}))
        if metric_id in {'tfs','offensive-reach'}:
            result['consequences'] = concatenate('consequences')
            coverage['byGame'] = [row for p in products for row in p['coverage']['byGame']]
            coverage['selectedGraphsWithoutEvidence'] = max(0,graph_count-len(coverage['byGame']))
            coverage['supportedAwardConsequences'] = len(result['consequences'])
            coverage['observedPAsWithoutSupportedAwardConsequence'] = max(0,
                coverage['observedEntities']['plate_appearance']-len(result['consequences']))
        if metric_id == 'tfs':
            result['runnerBoundaryStates'] = concatenate('runnerBoundaryStates')
            boundaries = [p['coverage']['runnerBoundaryProjection'] for p in products]
            projection = deepcopy(boundaries[0])
            for key,value in projection.items():
                if type(value) is int: projection[key] = sum(b[key] for b in boundaries)
                elif isinstance(value,list): projection[key] = [r for b in boundaries for r in b[key]]
            coverage['runnerBoundaryProjection'] = projection
        return result
    if any('CONFLICTING_REVIEW_DISPOSITION' in p['gaps'] for p in products):
        return m.unavailable('CONFLICTING_REVIEW_DISPOSITION',coverage=coverage,metricId=metric_id)
    resolved = sum(p['coverage']['resolvedReviews'] for p in products)
    overturned = sum((m.fraction(p['value'])*p['coverage']['resolvedReviews'] for p in products if p['value'] is not None), m.Fraction())
    result = m.available(overturned/resolved) if resolved else m.unavailable('EMPTY_DENOMINATOR')
    coverage.update(resolvedReviews=resolved, unresolvedReviews=sum(p['coverage']['unresolvedReviews'] for p in products),
        population=products[0]['coverage']['population'],
        reviewsWithAffectedPlayer=sum(p['coverage']['reviewsWithAffectedPlayer'] for p in products))
    result.update(coverage=coverage,metricId=metric_id,evidence=sorted(set(concatenate('evidence'))),
        scope=coverage['population'],grain=entry['grain'],reviewEvidence=concatenate('reviewEvidence'))
    return result


def selected_results(m, connection, request, graphs):
    ids = m.requested_metric_ids(request)
    by_metric = defaultdict(list)
    for group in batches(graphs):
        found = set()
        for graph, metric_id, text, digest in connection.execute(
                f'SELECT graph_iri,metric_id,result_json,result_sha256 FROM metric_suite_shell '
                f'WHERE graph_iri IN ({placeholders(group)}) AND metric_id IN ({placeholders(ids)}) '
                'ORDER BY graph_iri,metric_id', [*group,*ids]):
            product = decode(m,text,digest)
            if product.get('metricId') != metric_id:
                raise m.EvidenceError('Metric shell identity mismatch')
            by_metric[metric_id].append(product); found.add((graph,metric_id))
        if found != {(g,metric_id) for g in group for metric_id in ids}:
            raise m.EvidenceError('Metric build lacks a selected game result')
    results = [merge_metric(m,metric_id,by_metric[metric_id],len(graphs)) for metric_id in ids]
    return {'metrics':results} if request.get('view') == 'dashboard' else {'metric':results[0]}


def reference_ranks(m, connection, metric_id, year, graphs, compute, *, write=False):
    """Reuse only the identical independently admitted reference population.

    The caller checks current source proofs and the requested calendar scope
    before lookup. A historical cutoff with different graphs computes its own
    exact ranks and never consumes the latest population's ranks.
    """
    key = (metric_id, year, m._hash(m._json(sorted(graphs))))
    manifest = connection.execute('SELECT row_count FROM metric_suite_reference '
        'WHERE metric_id=? AND season=? AND graph_set_sha256=?', key).fetchone()
    if manifest:
        ranks = {identity:decode(m,text,digest) for identity,text,digest in connection.execute(
            'SELECT observation_key,rank_json,rank_sha256 FROM metric_suite_reference_rank '
            'WHERE metric_id=? AND season=? AND graph_set_sha256=? ORDER BY observation_key', key)}
        if len(ranks) != manifest[0]:
            raise m.EvidenceError('Season rank observation census mismatch')
        return ranks
    ranks = compute()
    if write:
        connection.execute('INSERT INTO metric_suite_reference VALUES (?,?,?,?)', (*key,len(ranks)))
        for identity,rank in sorted(ranks.items()):
            text = m._json(rank)
            connection.execute('INSERT INTO metric_suite_reference_rank VALUES (?,?,?,?,?,?)',
                (*key,identity,text,m._hash(text)))
    return ranks


def coverage(m, connection, graphs):
    families = defaultdict(lambda:dict(games=0,completeProjections=0,observations=0,unresolvedObservations=0,withheldGraphs=[],gaps={}))
    for group in batches(graphs):
        for graph,family,count,text,digest in connection.execute(
                f'SELECT graph_iri,family,row_count,state_json,state_sha256 FROM metric_suite_input_state '
                f'WHERE graph_iri IN ({placeholders(group)}) ORDER BY family,graph_iri',group):
            state = decode(m,text,digest); row = families[family]
            row['games'] += 1; row['observations'] += count
            complete = state.get('complete', not state.get('unresolvedPlateAppearances'))
            if complete: row['completeProjections'] += 1
            else: row['withheldGraphs'].append(graph)
            reasons = {g for g in state.get('gaps',[]) if isinstance(g,str)}
            unresolved = [*state.get('unresolvedPlateAppearances',[]),
                *(g for g in state.get('gaps',[]) if isinstance(g,dict))]
            row['unresolvedObservations'] += len(unresolved)
            for item in unresolved:
                reasons.update(item.get('gaps', [item['gap']] if 'gap' in item else []))
            for reason in sorted(reasons): row['gaps'][reason] = row['gaps'].get(reason,0)+1
    return dict(sorted(families.items()))
