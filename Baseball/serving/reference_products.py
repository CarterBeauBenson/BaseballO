"""NiFi-prepared exact ranks for every supported historical date cutoff.

Reuse the accepted population and ranking functions; only their storage and
execution time change. This module is independent of per-game calculations.
"""
from contextlib import contextmanager
from fractions import Fraction
import gzip
import io
import json
from pathlib import Path
import hashlib


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def initialize(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS dashboard_reference (
        metric_id TEXT NOT NULL, season INTEGER NOT NULL, graph_set_sha256 TEXT NOT NULL,
        row_count INTEGER NOT NULL, payload_sha256 TEXT NOT NULL, payload BLOB NOT NULL,
        PRIMARY KEY(metric_id,season,graph_set_sha256))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS dashboard_reference_players (
        metric_id TEXT NOT NULL, season INTEGER NOT NULL, graph_set_sha256 TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL, payload BLOB NOT NULL,
        PRIMARY KEY(metric_id,season,graph_set_sha256))''')


def prepare_players(m, db, metric, year, graphs, qualification, result):
    """Retain exact game/player aggregates only after the existing reducer passes.

    Qualification supplies official PA credit and team exposure, including
    missed games. The established percentile functions supply the scores.
    This product changes neither admission nor the reference population.
    """
    # A one-observation PAQ-A cohort has no percentile, even though its
    # reference census is complete. Retain that existing failure per game:
    # a selected range outside the cohort can still use other ranked PAs.
    small_cohort=metric=='paq-a' and result['playerSummaryGaps']==['EMPTY_DENOMINATOR']
    if result['playerPopulationComplete'] is not True and not small_cohort:return
    games=dict(db.execute('SELECT game_iri,graph_iri FROM game_dimension'))
    grouped={graph:{} for graph in graphs}
    for person in qualification['participation']:
        for exposure in person['teamGameExposure']:
            grouped[games[exposure['game']]][person['player']]=dict(pa=0,count=0,sum=Fraction(),gaps=[])
    for row in qualification['expectedObservations']:
        grouped[row['graph']][row['player']]['pa']+=1
    family='paq21' if metric=='paq-2.1' else 'recovery' if metric=='recovery-quality' else 'contribution'
    inputs=m._blocks.read_inputs(m._block_api(),db,family,graphs)
    def missing_ranks():raise m.EvidenceError('Reference ranks were not prepared')
    ranks=m._blocks.reference_ranks(m._block_api(),db,metric,year,graphs,missing_ranks)
    for graph in graphs:
        for row in inputs[graph]['plateAppearances']:
            if metric=='recovery-quality' and not row['twoStrikeEligible']:continue
            key=m._json([row['graph'],row['game'],row['plateAppearance'],row['player'],year]) \
                if metric=='paq-2.1' else m._json([row['graph'],row['plateAppearance']])
            rank=ranks[key]
            if metric=='paq-2.1' and rank['status']!='available' and rank['gaps']==['PAQ21_NOT_APPLICABLE']:continue
            person=grouped[graph][row['player']]
            if small_cohort and rank['status']!='available' and rank['gaps']==['EMPTY_DENOMINATOR']:
                person['gaps']=['EMPTY_DENOMINATOR'];continue
            if rank['status']!='available':raise m.EvidenceError('Incomplete reference player product')
            person['count']+=1;person['sum']+=m.fraction(rank['value'])
    for people in grouped.values():
        for person in people.values():person['sum']=m.exact(person['sum'])
    product=dict(games=grouped,reference=result['referencePopulations'][0])
    raw=m._json(product).encode('utf-8')
    if len(raw)>256*1024*1024:raise m.EvidenceError('Reference player product exceeds its read limit')
    key=(metric,year,m._hash(m._json(sorted(graphs))))
    db.execute('INSERT INTO dashboard_reference_players VALUES (?,?,?,?,?)',
        (*key,hashlib.sha256(raw).hexdigest(),gzip.compress(raw,compresslevel=1,mtime=0)))


@contextmanager
def prepared_ranks(m, connection):
    original = m._blocks.reference_ranks
    def retained(api, db, metric_id, year, graphs, compute, *, write=False):
        if db is not connection: raise m.EvidenceError('Wrong reference connection')
        key=(metric_id,year,m._hash(m._json(sorted(graphs))))
        row=db.execute('SELECT row_count,payload_sha256,payload FROM dashboard_reference '
            'WHERE metric_id=? AND season=? AND graph_set_sha256=?',key).fetchone()
        if row:
            with gzip.GzipFile(fileobj=io.BytesIO(row[2])) as stream: raw=stream.read(256*1024*1024+1)
            if len(raw)>256*1024*1024 or hashlib.sha256(raw).hexdigest()!=row[1]:
                raise m.EvidenceError('Prepared reference checksum mismatch')
            ranks=json.loads(raw)
            if not isinstance(ranks,dict) or len(ranks)!=row[0]:
                raise m.EvidenceError('Prepared reference observation census mismatch')
            return ranks
        if not write:
            raise m.EvidenceError('Selected reference ranks need NiFi preparation')
        ranks=compute()
        raw=m._json(ranks).encode('utf-8')
        if len(raw)>256*1024*1024: raise m.EvidenceError('Reference product exceeds its read limit')
        db.execute('INSERT INTO dashboard_reference VALUES (?,?,?,?,?,?)',
            (*key,len(ranks),hashlib.sha256(raw).hexdigest(),gzip.compress(raw,compresslevel=1,mtime=0)))
        return ranks
    m._blocks.reference_ranks=retained
    try: yield
    finally: m._blocks.reference_ranks=original


def prepare_individual_inputs(m, connection, player_admissions, seasons):
    """Complete game inputs from a full set of existing individual B1 checks.

    Read only retained RDF bindings in SQL. This cannot manufacture a source
    admission or relax count, boundary, resolution or defensive requirements.
    """
    player_partitions=connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_player_partition'").fetchone()
    for graph, individual in player_admissions.items():
        if not m.complete_batting_admission({}, individual):continue
        game=connection.execute('SELECT season,game_set FROM game_dimension WHERE graph_iri=?',(graph,)).fetchone()
        if not game or game[0] not in seasons or game[1]!='regular_season':continue
        proofs={}
        for family,table in [('batting','metric_suite_admission'),('count','metric_suite_count_admission'),
                             ('boundary','metric_suite_boundary_admission'),('resolution','metric_suite_runner_resolution_admission')]:
            row=connection.execute(f'SELECT proof_json,proof_sha256 FROM {table} WHERE graph_iri=?',(graph,)).fetchone()
            proofs[family]=m._blocks.decode(m._block_api(),*row) if row else {}
        if m.complete_batting_admission(proofs['batting']):continue
        inputs={family:m._blocks.read_inputs(m._block_api(),connection,family,[graph])[graph]
                for family in ('contribution','recovery')}
        recover=(not inputs['recovery'].get('complete') and m.complete_batting_admission(proofs['count']))
        contribute=(not inputs['contribution'].get('complete') and
                    all(m.complete_batting_admission(proofs[f]) for f in ('boundary','resolution')))
        if not (recover or contribute):continue
        rows=[m._blocks.decode(m._block_api(),text,digest) for text,digest in connection.execute(
            'SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,))]
        retained,=m.read_results(connection,graph,'tfs')
        if len(rows)!=retained['coverage']['evidenceRows']:
            raise m.EvidenceError('Stored reference evidence is incomplete')
        rows.sort(key=m._json)
        if recover:
            inputs['recovery']=m.recovery_game_inputs(rows,graph=graph,batting_admission=proofs['batting'],
                pitch_count_admission=proofs['count'],player_admission=individual)
        if contribute:
            inputs['contribution']=m.contribution_game_inputs(rows,graph=graph,batting_admission=proofs['batting'],
                runner_boundary_admission=proofs['boundary'],runner_resolution_admission=proofs['resolution'],
                player_admission=individual)
        defense=m._blocks.read_inputs(m._block_api(),connection,'defense',[graph])[graph]
        inputs['paq21']=m.paq21_game_inputs(inputs['contribution'],inputs['recovery'],defense)
        for metric,family,key in [('tfs','contribution','contributionInputs'),
                ('recovery-quality','recovery','recoveryInputs'),('paq-2.1','paq21','paq21Inputs')]:
            result,=m.read_results(connection,graph,metric)
            if result[key]!=inputs[family]:
                result[key]=inputs[family]
                m.store_result(connection,graph,metric,'game-scope',result)
                if player_partitions:
                    connection.execute('DELETE FROM dashboard_player_partition WHERE graph_iri=?',(graph,))


def prepare(m, connection, seasons=None, checkpoint=None, player_admissions=None, metric_ids=None):
    initialize(connection)
    player_admissions=player_admissions or {}
    dates=connection.execute("SELECT DISTINCT season,official_date FROM game_dimension "
        "WHERE game_set='regular_season' ORDER BY season,official_date").fetchall()
    affected=set(seasons) if seasons is not None else {r[0] for r in dates}
    selected={'paq-2','paq-a','recovery-quality','paq-2.1'} if metric_ids is None else set(metric_ids) & {'paq-2','paq-a','recovery-quality','paq-2.1'}
    # Family builds already calculate inputs with the individual admission.
    # The legacy combined builder still upgrades those inputs here.
    if metric_ids is None:prepare_individual_inputs(m,connection,player_admissions,affected)
    for year in affected:
        for metric in selected:
            connection.execute('DELETE FROM dashboard_reference WHERE season=? AND metric_id=?',(year,metric))
            connection.execute('DELETE FROM dashboard_reference_players WHERE season=? AND metric_id=?',(year,metric))
    output=[]
    with prepared_ranks(m,connection):
        for year,cutoff in dates:
            if year not in affected: continue
            scope=dict(gameSet='regular_season',startDate=f'{year}-01-01',endDate=cutoff)
            graphs=[r[0] for r in connection.execute("SELECT graph_iri FROM game_dimension "
                "WHERE game_set='regular_season' AND season=? AND official_date<=? ORDER BY graph_iri",(year,cutoff))]
            api=m._block_api()
            # Qualification rejects a withheld source admission before it
            # consumes any RDF-derived rows. Preserve that short circuit: a
            # rejected historical population must not decode every prior game.
            def rows():
                yield from m._blocks.read_scope(api,connection,graphs)
            admissions={}
            for group in m._blocks.batches(graphs):
                for graph,text,digest in connection.execute('SELECT graph_iri,proof_json,proof_sha256 '
                        f'FROM metric_suite_admission WHERE graph_iri IN ({m._blocks.placeholders(group)})',group):
                    admissions[graph]=m._blocks.decode(api,text,digest)
            schedule=m.selected_schedule_coverage(connection,scope,graphs)
            qualification=m.batting_qualification(rows(),graphs=graphs,admissions=admissions,date_scope=scope,
                selected_games_complete=schedule['complete'],player_admissions=player_admissions)
            for metric_id in ('paq-2','paq-a','recovery-quality','paq-2.1'):
                if metric_id not in selected:continue
                args=dict(graphs=graphs,qualification=qualification,date_scope=scope,_write_reference=True,
                    player_admissions=player_admissions)
                result=(m.paq21_players(connection,**args) if metric_id=='paq-2.1' else
                    m.season_rank_players(connection,metric_id=metric_id,**args))
                prepare_players(m,connection,metric_id,year,graphs,qualification,result)
                output.append(dict(season=year,cutoff=cutoff,metricId=metric_id,
                    populationComplete=result['playerPopulationComplete'],gaps=result['playerSummaryGaps']))
            if checkpoint: checkpoint(referenceCutoff=cutoff,referenceSeasons=sorted(affected))
    return output
