"""Read prepared player products independently of their producer fingerprint.

An unrelated historical reference cannot trigger reconstruction of the selected
season. Missing exact reference products remain unavailable until NiFi prepares
them. The immutable player/game calculation module is unchanged.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import json


def reference_available(m, db, metric, scope):
    if scope['gameSet'] != 'regular_season':
        return False
    for year in range(int(scope['startDate'][:4]), int(scope['endDate'][:4])+1):
        cutoff=min(scope['endDate'], f'{year}-12-31')
        graphs=[r[0] for r in db.execute(
            "SELECT graph_iri FROM game_dimension WHERE game_set='regular_season' "
            'AND official_date BETWEEN ? AND ? ORDER BY graph_iri', (f'{year}-01-01',cutoff))]
        key=m._hash(m._json(graphs))
        if not db.execute('SELECT 1 FROM dashboard_reference WHERE metric_id=? AND season=? '
                          'AND graph_set_sha256=?', (metric,year,key)).fetchone():
            return False
    return True


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
    metrics=[]
    for metric in ids:
        entry=next(e for e in m.catalog()['metrics'] if e['id']==metric)
        base=dict(metricId=metric,grain='player',coverage=dict(games=len(graphs),populationComplete=False),
            playerPopulationComplete=False,playerRecordsComplete=False,playerResults=[],
            scope='Complete player records across the entire selected range; excluded records are disclosed.')
        if metric not in products.PREPARED:
            # Preserve the established reference producer when a prepared
            # reference exists. Never substitute a percentile of complete cases.
            if metric in products.REFERENCES and reference_available(m, db, metric, scope):
                metrics.append(m.query_sql(db,{'metricId':metric},scope)['metric']);continue
            gap='SEASON_REFERENCE_UNAVAILABLE' if metric in products.REFERENCES else 'REVIEW_PLAYER_POPULATION' if 'review' in metric or metric=='adjudication-volatility' else 'ROLE_REALIZATION_POPULATION'
            metrics.append(dict(m.unavailable(gap),**base,playerSummaryGaps=[gap]));continue
        if not schedule['complete']:
            metrics.append(dict(m.unavailable('COMPLETE_SELECTED_SCHEDULE'),**base,
                playerSummaryGaps=['COMPLETE_SELECTED_SCHEDULE'],schedule=schedule));continue
        if roster_graphs!=set(graphs):
            metrics.append(dict(m.unavailable('COMPLETE_PARTICIPATION'),**base,
                playerSummaryGaps=['COMPLETE_PARTICIPATION']));continue
        grouped=defaultdict(list);blocked=defaultdict(set);seen=defaultdict(set)
        for graph,player,complete,text,reason in db.execute('SELECT p.graph_iri,p.player,p.complete,p.aggregate_json,p.reason '
                'FROM dashboard_player_metric p JOIN game_dimension g USING(graph_iri) '
                'WHERE p.metric_id=? AND g.game_set=? AND g.official_date BETWEEN ? AND ?', (metric,*params)):
            seen[player].add(graph)
            if not complete:blocked[player].add(reason or 'INCOMPLETE_PLAYER_RECORD')
            else:grouped[player].append(json.loads(text))
        output=[];exclusions=Counter();complete_people=0
        for player,person in people.items():
            if not person['roster'] or seen[player]!=person['graphs']:
                blocked[player].add('COMPLETE_PARTICIPATION')
            if blocked[player]:
                exclusions.update(blocked[player]);continue
            complete_people+=1;parts=grouped[player]
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
