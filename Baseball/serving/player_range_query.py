"""Read prepared player products independently of their producer fingerprint.

An unrelated historical reference cannot trigger reconstruction of the selected
season. Missing exact reference products remain unavailable until NiFi prepares
them. The immutable player/game calculation module is unchanged.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import io
import json


def reference_products(m, db, metric, scope):
    if scope['gameSet'] != 'regular_season':
        return []
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_reference_players'").fetchone():
        return []
    products=[]
    for year in range(int(scope['startDate'][:4]), int(scope['endDate'][:4])+1):
        cutoff=min(scope['endDate'], f'{year}-12-31')
        graphs=[r[0] for r in db.execute(
            "SELECT graph_iri FROM game_dimension WHERE game_set='regular_season' "
            'AND official_date BETWEEN ? AND ? ORDER BY graph_iri', (f'{year}-01-01',cutoff))]
        key=m._hash(m._json(graphs))
        row=db.execute('SELECT payload_sha256,payload FROM dashboard_reference_players WHERE metric_id=? AND season=? '
                       'AND graph_set_sha256=?', (metric,year,key)).fetchone()
        if not row:return []
        products.append((year,cutoff,graphs,row))
    return products


def reference_available(m, db, metric, scope):
    return bool(reference_products(m,db,metric,scope))


def reference_players(m, db, metric, scope, selected_graphs):
    """Pool prepared reference-relative game totals, without PA reconstruction."""
    products=reference_products(m,db,metric,scope)
    def denied(gap,**details):
        return dict(m.unavailable(gap),playerPopulationComplete=False,playerRecordsComplete=False,
                    playerResults=[],playerSummaryGaps=[gap],**details)
    if not products:return denied('SEASON_REFERENCE_UNAVAILABLE')
    people=defaultdict(lambda:dict(pa=0,games=0,count=0,total=Fraction(),graphs=set()))
    references=[];seen=set();selected=set(selected_graphs);gaps=set()
    for year,cutoff,graphs,(digest,compressed) in products:
        reference_scope=dict(gameSet='regular_season',startDate=f'{year}-01-01',endDate=cutoff)
        schedule=m.selected_schedule_coverage(db,reference_scope,graphs)
        if not schedule['complete']:return denied('REFERENCE_POPULATION_INCOMPLETE')
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:raw=stream.read(256*1024*1024+1)
        if len(raw)>256*1024*1024 or hashlib.sha256(raw).hexdigest()!=digest:
            raise m.EvidenceError('Prepared reference player checksum mismatch')
        product=json.loads(raw)
        if set(product['games'])!=set(graphs):raise m.EvidenceError('Prepared reference game census mismatch')
        references.append(dict(product['reference'],dateScope=reference_scope,schedule=schedule))
        for graph in selected.intersection(graphs):
            seen.add(graph)
            for player,row in product['games'][graph].items():
                gaps.update(row['gaps'])
                person=people[player];person['pa']+=row['pa'];person['games']+=1
                person['count']+=row['count'];person['total']+=m.fraction(row['sum'])
                if row['count']:person['graphs'].add(graph)
    if seen!=selected:raise m.EvidenceError('Selected games escaped the prepared reference')
    if gaps:return denied(sorted(gaps)[0],referencePopulations=references)
    output=[]
    for player,person in sorted(people.items()):
        count=person['count'];total=person['total']
        if not count or not person['pa']:continue
        summary=m.available(total/count)
        if metric!='paq-2.1':summary['components']=dict(count=count,total=m.exact(total))
        output.append(dict(summary,player=player,metricId=metric,dateScope=dict(scope),
            completeParticipation=True,plateAppearances=person['pa'],teamGames=person['games'],
            graphs=sorted(person['graphs']),aggregate=dict(kind='mean',sum=m.exact(total),count=count)))
    count=sum(p['aggregate']['count'] for p in output)
    total=sum((m.fraction(p['aggregate']['sum']) for p in output),Fraction())
    summary=m.available(total/count) if count else m.unavailable('EMPTY_DENOMINATOR')
    if count and metric!='paq-2.1':summary['components']=dict(count=count,total=m.exact(total))
    return dict(summary,playerPopulationComplete=True,playerRecordsComplete=True,
        playerResults=output,playerSummaryGaps=[],referencePopulations=references,
        scope='Season-relative percentiles averaged over applicable selected-period PAs; independent state cohorts for PAQ-A.')


def player_records(db, metrics, params, people):
    """Read requested products together, keeping exact range exclusions.

    Game-first traversal keeps each game's adjacent rows together instead of
    revisiting the season's pages separately for every dashboard card.
    """
    products={metric:(defaultdict(list),defaultdict(set),Counter()) for metric in metrics}
    if not products:return products
    marks=','.join('?' for _ in products)
    covered=db.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='dashboard_player_metric_coverage'").fetchone()
    index='dashboard_player_metric_coverage' if covered else \
        'sqlite_autoindex_dashboard_player_metric_1' if len(products)>1 else 'dashboard_player_metric_selection'
    aggregate='NULL' if covered else 'p.aggregate_json'
    rows=db.execute(f'SELECT p.metric_id,p.graph_iri,p.player,p.complete,{aggregate},p.reason '
        f'FROM game_dimension g CROSS JOIN dashboard_player_metric p INDEXED BY {index} ON p.graph_iri=g.graph_iri '
        f'WHERE g.game_set=? AND g.official_date BETWEEN ? AND ? AND p.metric_id IN ({marks})',
        (*params,*products))
    for metric,graph,player,complete,text,reason in rows:
        person=people.get(player)
        if person is None:continue
        grouped,blocked,seen=products[metric]
        # The primary key makes each metric/player/game unique. Count matching
        # games and reject any unexpected game without keeping millions of
        # duplicate graph strings in per-metric sets.
        if graph in person['graphs']:seen[player]+=1
        else:blocked[player].add('COMPLETE_PARTICIPATION')
        if not complete:blocked[player].add(reason or 'INCOMPLETE_PLAYER_RECORD')
        if blocked[player]:grouped.pop(player,None)
        elif not covered:grouped[player].append(text)
    if covered:
        # Fetch aggregates only after the entire selected range passes. Chunk
        # bound parameters for SQLite builds with the older 999-variable limit.
        eligible=[(metric,player) for metric,(_,blocked,seen) in products.items()
                  for player,person in people.items()
                  if person['roster'] and not blocked[player] and seen[player]==len(person['graphs'])]
        for offset in range(0,len(eligible),400):
            batch=eligible[offset:offset+400]
            values=','.join('(?,?)' for _ in batch)
            rows=db.execute(f'WITH eligible(metric_id,player) AS (VALUES {values}) '
                'SELECT p.metric_id,p.player,p.aggregate_json FROM eligible e CROSS JOIN game_dimension g '
                'CROSS JOIN dashboard_player_metric p INDEXED BY sqlite_autoindex_dashboard_player_metric_1 '
                'ON p.graph_iri=g.graph_iri AND p.player=e.player AND p.metric_id=e.metric_id '
                'WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',
                (*[value for pair in batch for value in pair],*params))
            for metric,player,text in rows:products[metric][0][player].append(text)
    return products


def query(m, products, db, request, scope):
    """Read small player/game products; never reconstruct graph or PA history."""
    ids=m.requested_metric_ids(request);params=(scope['gameSet'],scope['startDate'],scope['endDate'])
    graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE game_set=? '
                                   'AND official_date BETWEEN ? AND ? ORDER BY graph_iri',params)]
    schedule=m.selected_schedule_coverage(db,scope,graphs)
    expected=dict(db.execute('SELECT c.graph_iri,c.input_sha256 FROM dashboard_checkpoint c '
        'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params))
    saved=dict(db.execute('SELECT p.graph_iri,p.input_sha256 FROM dashboard_player_partition p '
        'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params))
    version=products.fingerprint()
    individual=dict(db.execute('SELECT a.graph_iri,a.proof_sha256 FROM dashboard_player_admission a '
        'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params))
    if any(saved.get(g)!=m._hash(key+version+individual.get(g,'')) for g,key in expected.items()):
        raise m.EvidenceError('Selected player products need NiFi preparation')
    missing_rosters=[dict(graph=graph,gamePk=graph.rsplit('/',1)[-1],date=day)
        for graph,day in db.execute('SELECT g.graph_iri,g.official_date FROM game_dimension g '
            'LEFT JOIN dashboard_player_game p USING(graph_iri) '
            'WHERE g.game_set=? AND g.official_date BETWEEN ? AND ? GROUP BY g.graph_iri '
            'HAVING MAX(COALESCE(p.roster_complete,0))=0 ORDER BY g.official_date,g.graph_iri',params)]
    participation_coverage=dict(games=len(graphs),verifiedGames=len(graphs)-len(missing_rosters),
                                unverifiedGames=missing_rosters)
    people=defaultdict(lambda:dict(pa=0,paKnown=True,games=set(),graphs=set(),roster=True))
    roster_graphs=set()
    participation=() if missing_rosters else db.execute('SELECT p.graph_iri,p.player,p.plate_appearances,p.roster_complete '
            'FROM dashboard_player_game p JOIN game_dimension g USING(graph_iri) '
            'WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params)
    for graph,player,pa,roster in participation:
        p=people[player];p['pa']+=pa or 0;p['paKnown'] &= pa is not None
        if roster:roster_graphs.add(graph)
        p['games'].add(graph);p['graphs'].add(graph);p['roster'] &= bool(roster)
    prepared=player_records(db,[metric for metric in ids if metric in products.PREPARED],params,people) \
        if schedule['complete'] and roster_graphs==set(graphs) else {}
    metrics=[]
    for metric in ids:
        entry=next(e for e in m.catalog()['metrics'] if e['id']==metric)
        base=dict(metricId=metric,grain='player',coverage=dict(games=len(graphs),populationComplete=False),
            playerPopulationComplete=False,playerRecordsComplete=False,playerResults=[],
            scope='Complete player records across the entire selected range; excluded records are disclosed.')
        if not schedule['complete']:
            metrics.append(dict(m.unavailable('COMPLETE_SELECTED_SCHEDULE'),**base,
                playerSummaryGaps=['COMPLETE_SELECTED_SCHEDULE'],schedule=schedule));continue
        if metric in products.REFERENCES:
            result=reference_players(m,db,metric,scope,graphs)
            base['coverage']['populationComplete']=result['playerPopulationComplete']
            base.update(result);metrics.append(base);continue
        if metric not in products.PREPARED:
            gap='REVIEW_PLAYER_POPULATION' if 'review' in metric or metric=='adjudication-volatility' else 'ROLE_REALIZATION_POPULATION'
            metrics.append(dict(m.unavailable(gap),**base,playerSummaryGaps=[gap]));continue
        if roster_graphs!=set(graphs):
            metrics.append(dict(m.unavailable('COMPLETE_PARTICIPATION'),**base,
                playerSummaryGaps=['COMPLETE_PARTICIPATION']));continue
        grouped,blocked,seen=prepared[metric]
        output=[];exclusions=Counter();complete_people=0
        for player,person in people.items():
            if not person['roster'] or seen[player]!=len(person['graphs']):
                blocked[player].add('COMPLETE_PARTICIPATION')
            if blocked[player]:
                exclusions.update(blocked[player]);continue
            complete_people+=1;parts=[json.loads(text) for text in grouped.pop(player,())]
            if metric=='empty-game-rate':
                aggregate=dict(kind='count',count=sum(p['count'] for p in parts),eligibleGames=sum(p['eligibleGames'] for p in parts))
                if not aggregate['eligibleGames']:continue
                value=m.exact(aggregate['count'])
            elif metric=='contribution-path-diversity':
                counts=[sum(p['channelCounts'][i] for p in parts) for i in range(3)]
                if not sum(counts):continue
                aggregate=dict(kind='channel_entropy',channelCounts=counts);value=None
            else:
                total=sum((m.fraction(p['sum']) for p in parts),Fraction());count=sum(p['count'] for p in parts)
                if not count:continue
                aggregate=dict(kind='mean',sum=m.exact(total),count=count);value=m.exact(total/count)
            output.append(dict(player=player,metricId=metric,status='available',completeParticipation=True,
                dateScope=dict(scope),teamGames=len(person['games']),graphs=sorted(person['graphs']),
                plateAppearances=person['pa'] if person['paKnown'] else None,
                independentRunningEpisodes=sum(p.get('independentRunningEpisodes',0) for p in parts),
                aggregate=aggregate,value=value))
        excluded=len(people)-complete_people
        base.update(playerRecordsComplete=True,playerPopulationComplete=excluded==0,
            playerResults=output,playerSummaryGaps=sorted(exclusions),
            rankingCoverage=dict(policy=products.POLICY,completePlayers=complete_people,
                excludedPlayers=excluded,rosteredPlayers=len(people),exclusionReasons=dict(exclusions),
                leaguePopulationComplete=excluded==0))
        base['coverage']['populationComplete']=excluded==0
        if metric=='empty-game-rate':
            total=sum(p['aggregate']['count'] for p in output);eligible=sum(p['aggregate']['eligibleGames'] for p in output)
            result=m.available(total,components=dict(emptyGames=total,eligibleGames=eligible)) if eligible else m.unavailable('EMPTY_DENOMINATOR')
        elif metric=='contribution-path-diversity':
            result=m.channel_entropy([sum(p['aggregate']['channelCounts'][i] for p in output) for i in range(3)])
        else:
            count=sum(p['aggregate']['count'] for p in output);total=sum((m.fraction(p['aggregate']['sum']) for p in output),Fraction())
            result=m.available(total/count) if count else m.unavailable('EMPTY_DENOMINATOR')
        metrics.append(dict(result,**base))
    return dict(execution='materialized-sql',implementationSha256=m.fingerprint(),dateScope=scope,
        graphCount=len(graphs),schedule=schedule,participationCoverage=participation_coverage,
        **({'metrics':metrics} if request.get('view')=='dashboard' else {'metric':metrics[0]}))
