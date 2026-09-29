"""NiFi-prepared player/game products; exact full-range pooling at read time.

Source proofs are never upgraded. A missing applicable observation excludes
the player's entire selected-range result, not just the troublesome game.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path

POLICY = 'complete-player-selected-range-v1'
CONTRIBUTION = {'tfs','rally-kill-rate','rally-kill-severity','opportunity-erosion'}
PROGRESS = {'offensive-reach','hidden-help-rate','empty-game-rate','contribution-path-diversity'}
RUNS = {'run-construction-depth','run-construction-breadth'}
DEFENSE = {'resolution-depth','defender-breadth'}
PREPARED = CONTRIBUTION | PROGRESS | RUNS | DEFENSE | {'empty-game-damage'}
REFERENCES = {'paq-2','paq-a','paq-2.1','recovery-quality'}
PREVIOUS_VERSION = '4890951c9161d99efdbf52c5364c4ca08bbd4f9cd3e2853127846a728ae1282d'
PREVIOUS_INDIVIDUAL_VERSION = '38deead69127b00c2383239c1c8abb172ec3b29d1f3ea4e4fbde652cb7d61617'
PREVIOUS_BOUNDARY_VERSION = 'dbb26a1f1e64c9f38dea522450e509e51de3024d8bbf6e2c9bd4903650821ade'


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS dashboard_player_partition (
        graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri), input_sha256 TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS dashboard_player_admission (
        graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
        proof_json TEXT NOT NULL, proof_sha256 TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS dashboard_player_game (
        graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri), player TEXT NOT NULL,
        team TEXT NOT NULL, plate_appearances INTEGER, roster_complete INTEGER NOT NULL,
        PRIMARY KEY(graph_iri,player));
      CREATE TABLE IF NOT EXISTS dashboard_player_metric (
        graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri), player TEXT NOT NULL,
        metric_id TEXT NOT NULL, complete INTEGER NOT NULL,
        aggregate_json TEXT NOT NULL, reason TEXT,
        PRIMARY KEY(graph_iri,player,metric_id));
      CREATE INDEX IF NOT EXISTS dashboard_player_metric_selection
        ON dashboard_player_metric(metric_id,graph_iri,player);
    ''')


def admitted(proof):
    return all(proof.get(k)==v for k,v in
               dict(status='admitted',sourceReconciled=True,graphConforms=True).items())


def zero():
    return dict(kind='mean',sum={'numerator':'0','denominator':'1'},count=0)


def mean(m, values):
    return dict(kind='mean',sum=m.exact(sum(values,Fraction())),count=len(values))


def qualification(m,rows,graph,scope,batting,individual):
    if admitted(batting):
        return m.batting_qualification(rows,graphs=[graph],admissions={graph:batting},
            date_scope=scope,selected_games_complete=True)
    # SHACL admits players individually; counts and membership still come from
    # RDF bindings. A source boxscore count is never a serving value.
    valid={p['player'] for p in individual.get('players',[]) if p['status']=='admitted'}
    if not individual.get('rosterComplete') or not individual.get('plateAppearanceInventoryComplete'):
        valid=set()
    members={};exposures=defaultdict(set)
    for row in rows:
        if row.get('player') not in valid:continue
        if row['kind']=='player_team_game':exposures[row['player']].add((row['game'],row['team']))
        if row['kind']=='plate_appearance' and row.get('recognizedBattingResult') in ('true','1'):
            if not all(row.get(k) for k in ('player','act','paResult','paResultType','paResultJudgment','paResultDecision','paResultRecord')):
                raise m.EvidenceError('Individually admitted PA lacks RDF result bindings')
            value=dict(graph=graph,plateAppearance=row['entity'],player=row['player'])
            if row['entity'] in members and members[row['entity']]!=value:
                raise m.EvidenceError('Individually admitted PA has conflicting ownership')
            members[row['entity']]=value
    if set(exposures)!=valid:raise m.EvidenceError('Individually admitted player lacks RDF participation')
    counts=Counter(r['player'] for r in members.values())
    return dict(officialPlateAppearanceCreditVerified=bool(valid),teamGameExposureVerified=bool(valid),
        selectedGamesComplete=True,expectedObservations=sorted(members.values(),key=m._json),
        participation=[dict(player=p,plateAppearances=counts[p],completeParticipation=True,dateScope=scope,
            teamGameExposure=[dict(game=g,team=t) for g,t in sorted(exposures[p])]) for p in sorted(valid)])


def project(m, *, graph, scope, rows, proofs, inputs, runs, run_people):
    """Project complete player records from already calculated game inputs."""
    game=next((r['game'] for r in rows),None)
    roster=defaultdict(set)
    for r in rows:
        if r['kind']=='player_team_game' and all(r.get(k) for k in ('player','team','teamRole')):
            roster[r['player']].add(r['team'])
    if any(len(t)!=1 for t in roster.values()):
        raise m.EvidenceError('Player has conflicting game-team exposure')
    individual=proofs.get('players',{})
    roster_ok=bool(roster) and (admitted(proofs['batting']) or admitted(proofs['run']) or individual.get('rosterComplete') is True)
    q=qualification(m,rows,graph,scope,proofs['batting'],individual)
    people={p['player']:p for p in q['participation']}
    expected=defaultdict(set)
    for p in q['expectedObservations']:expected[p['player']].add(p['plateAppearance'])
    contrib=inputs['contribution'];progress=inputs['progress'];defense=inputs['defense']
    by_pa={p['plateAppearance']:p for p in contrib.get('plateAppearances',[])}
    progress_pa={p['plateAppearance']:p for p in progress.get('plateAppearances',[]) if p['officialResult']}
    positive=set();uncertain=set();mix_uncertain=set();channels=defaultdict(set);episodes=defaultdict(set)
    for pa in progress.get('plateAppearances',[]):
        if pa['reach']:positive.add(pa['player'])
        positive.update(r['player'] for r in pa['independentPositive'])
        uncertain.update(pa.get('unresolvedRunningPositivePlayers',[]))
        if pa.get('independentPositiveGaps') and not pa.get('unresolvedRunningPositivePlayers'):
            uncertain.update(roster)
        for r in pa['positiveChannels']:channels[r['player']].add((r['play'],r['channel']))
        for r in pa['independentEpisodes']:episodes[r['player']].add(r['episode'])
        if pa['independentEpisodeGaps']:
            # Without a bounded participant for the missing episode, no other
            # player's complete channel census can be claimed from this play.
            mix_uncertain.update(roster)
    for pa in progress.get('unresolvedPlateAppearances',[]):
        affected=pa.get('possiblePositivePlayers')
        affected=set(roster) if affected is None else set(affected)
        positive.update(pa.get('confirmedPositivePlayers',[]))
        uncertain.update(affected);mix_uncertain.update(affected)
    classified={p['plateAppearance']:p for p in
                [*progress.get('plateAppearances',[]),*progress.get('unresolvedPlateAppearances',[])]
                if p.get('officialResult')}
    all_expected={p['plateAppearance'] for p in q['expectedObservations']}
    # Individually rejected batters do not invalidate another batter's PA
    # census. Their possible running contributions still enter the uncertainty
    # sets above, including uncertainty affecting an admitted player.
    qualified_classified={pa:r for pa,r in classified.items() if r['player'] in people}
    progress_census=(set(qualified_classified)==all_expected and
        all(classified[p]['player']==r['player'] for r in q['expectedObservations'] for p in [r['plateAppearance']]))
    run_values={};run_unknown={}
    observed={r['entity'] for r in rows if r['kind']=='run'}
    for metric,result in runs.items():
        values=defaultdict(list);unknown=set()
        members=[*result.get('runs',[]),*result.get('unresolvedRuns',[])]
        if (not admitted(proofs['run']) or {r['run'] for r in members}!=observed
                or len(members)!=len(observed)):
            unknown.update(roster)
        for r in result.get('unresolvedRuns',[]):
            unknown.update(run_people.get(r['run']) or roster)
        for r in result.get('runs',[]):
            if r.get('completeTrajectory') is True and r.get('status')=='available' and r.get('runner') in roster:
                values[r['runner']].append(m.fraction(r['value']))
            else:unknown.update(run_people.get(r['run']) or roster)
        run_values[metric]=values;run_unknown[metric]=unknown
    defensive={}
    for metric in DEFENSE:
        result=m.defensive_players(metric,[defense],rows,graphs=[graph],date_scope=scope,
            schedule={'complete':True},roster_admissions={graph:[proofs['batting'],proofs['run']]})
        defensive[metric]=(result.get('playerPopulationComplete') is True,
                           {p['player']:p['aggregate'] for p in result.get('playerResults',[])})
    records=[];participation=[]
    for player,teams in sorted(roster.items()):
        person=people.get(player);pa_count=person['plateAppearances'] if person else None
        participation.append((graph,player,next(iter(teams)),pa_count,int(roster_ok)))
        own=expected[player];own_contrib=[by_pa[p] for p in own if p in by_pa and by_pa[p]['player']==player]
        contrib_ok=person is not None and len(own_contrib)==len(own)
        own_progress=[progress_pa[p] for p in own if p in progress_pa and progress_pa[p]['player']==player]
        progress_ok=person is not None and admitted(proofs['resolution']) and len(own_progress)==len(own)
        empty_known=(person is not None and admitted(proofs['resolution']) and progress_census
                     and (player in positive or player not in uncertain))
        for metric in sorted(PREPARED):
            complete=False;aggregate=zero();reason='OFFICIAL_PA_POPULATION'
            if metric in RUNS:
                complete=player not in run_unknown[metric]
                aggregate=mean(m,run_values[metric][player]);reason='COMPLETE_SCORING_HISTORIES'
            elif metric in DEFENSE:
                complete,values=defensive[metric]
                aggregate=values.get(player,zero());reason='DEFENSIVE_POPULATION'
            elif person is not None:
                reason='COMPLETE_PA_CONTRIBUTIONS'
                if metric in CONTRIBUTION:
                    complete=contrib_ok
                    if complete and own_contrib:
                        selected_q=dict(q,participation=[person],expectedObservations=[r for r in q['expectedObservations'] if r['player']==player])
                        product=dict(contrib,complete=True,plateAppearances=own_contrib)
                        scored=m.contribution_players(metric,[product],qualification=selected_q,date_scope=scope)
                        complete=scored.get('playerPopulationComplete') is True
                        aggregate=next((r['aggregate'] for r in scored.get('playerResults',[]) if r['player']==player),zero())
                elif metric in {'offensive-reach','hidden-help-rate'}:
                    complete=progress_ok;reason='COMPLETE_PA_PROGRESS'
                    selected=own_progress if metric=='offensive-reach' else [p for p in own_progress if not p['batterPositive']]
                    aggregate=mean(m,[Fraction(p['reach'] if metric=='offensive-reach' else bool(p['otherPositivePlayers'])) for p in selected])
                elif metric=='empty-game-rate':
                    complete=empty_known or not own;reason='COMPLETE_EMPTY_GAME_CLASSIFICATION'
                    aggregate=dict(kind='count',count=int(bool(own) and player not in positive),eligibleGames=int(bool(own)))
                elif metric=='contribution-path-diversity':
                    complete=(admitted(proofs['resolution']) and progress_census and player not in mix_uncertain
                              and progress_ok)
                    reason='COMPLETE_CONTRIBUTION_CHANNELS'
                    counts=Counter(c for _,c in channels[player])
                    aggregate=dict(kind='channel_entropy',channelCounts=[counts[c] for c in ('batter_self','batter_other','runner_self')],
                                   independentRunningEpisodes=len(episodes[player]))
                elif metric=='empty-game-damage':
                    complete=not own or (empty_known and player in positive)
                    if own and empty_known and player not in positive and contrib_ok and contrib.get('independentDamageComplete') is True:
                        score=m.empty_game_damage([r['score'] for r in own_contrib],[],empty=True,complete=True)
                        complete=score['status']=='available'
                        if complete:aggregate=mean(m,[m.fraction(score['value'])])
                    reason='INDEPENDENT_DAMAGE_COVERAGE'
            complete=complete and roster_ok
            records.append((graph,player,metric,int(complete),m._json(aggregate),None if complete else reason))
    return participation,records


def prepare(m, db, checkpoint=None, player_admissions=None):
    initialize(db);version=fingerprint();changed=0
    # The player dashboard serves only these game sets. Exhibition/WBC roster
    # patterns must not participate in, or block, MLB dashboard preparation.
    inventory=db.execute('SELECT g.graph_iri,g.official_date,g.game_set,c.input_sha256 '
        "FROM game_dimension g JOIN dashboard_checkpoint c USING(graph_iri) "
        "WHERE g.game_set IN ('regular_season','all_star') ORDER BY g.graph_iri").fetchall()
    saved=dict(db.execute('SELECT graph_iri,input_sha256 FROM dashboard_player_partition'))
    player_admissions=player_admissions or {}
    for graph,day,game_set,key in inventory:
        individual=player_admissions.get(graph) or {}
        individual_text=m._json(individual);proof_sha=m._hash(individual_text) if individual else ''
        identity=m._hash(key+version+proof_sha)
        if saved.get(graph)==identity:continue
        # The new path changes only games with individual admissions. Preserve
        # all other existing player aggregates byte-for-byte on deployment.
        if (not individual and (saved.get(graph) in
                {m._hash(key+v+proof_sha) for v in (PREVIOUS_INDIVIDUAL_VERSION,PREVIOUS_BOUNDARY_VERSION)}
                or (not individual and saved.get(graph)==m._hash(key+PREVIOUS_VERSION)))):
            with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        rows=m._blocks.read_scope(m._block_api(),db,[graph])
        proofs={}
        for kind,table in [('batting','metric_suite_admission'),('run','metric_suite_run_admission'),
                           ('resolution','metric_suite_runner_resolution_admission'),
                           ('boundary','metric_suite_boundary_admission')]:
            row=db.execute(f'SELECT proof_json,proof_sha256 FROM {table} WHERE graph_iri=?',(graph,)).fetchone()
            proofs[kind]=m._blocks.decode(m._block_api(),*row) if row else {}
        proofs['players']=individual
        inputs={f:m._blocks.read_inputs(m._block_api(),db,f,[graph])[graph] for f in ('contribution','progress','defense')}
        if individual.get('paBoundaries') and not inputs['contribution'].get('complete'):
            evidence=[m._blocks.decode(m._block_api(),text,sha) for text,sha in db.execute(
                'SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,))]
            saved_proof=json.loads(db.execute('SELECT proof_json FROM dashboard_checkpoint WHERE graph_iri=?',(graph,)).fetchone()[0])
            if len(evidence)!=saved_proof['evidenceRows']:raise m.EvidenceError('Stored dashboard evidence is incomplete')
            evidence.sort(key=m._json)
            inputs['contribution']=m.contribution_game_inputs(evidence,graph=graph,batting_admission=proofs['batting'],
                runner_resolution_admission=proofs['resolution'],runner_boundary_admission=proofs['boundary'],player_admission=individual)
        runs={metric:m.read_results(db,graph,metric)[0] for metric in RUNS}
        unresolved={r['run'] for result in runs.values() for r in result.get('unresolvedRuns',[])}
        run_people=defaultdict(set)
        if unresolved:
            for text,digest in db.execute('SELECT binding_json,binding_sha256 FROM metric_suite_evidence '
                    'WHERE graph_iri=? AND json_extract(binding_json,\'$.kind\')=\'runner_movement\'',(graph,)):
                r=m._blocks.decode(m._block_api(),text,digest)
                if r.get('resolution') in unresolved and r.get('runner'):
                    run_people[r['resolution']].add(r['runner'])
        people,records=project(m,graph=graph,scope=dict(gameSet=game_set,startDate=day,endDate=day),
            rows=rows,proofs=proofs,inputs=inputs,runs=runs,run_people=run_people)
        with db:
            db.execute('DELETE FROM dashboard_player_admission WHERE graph_iri=?',(graph,))
            if individual:db.execute('INSERT INTO dashboard_player_admission VALUES (?,?,?)',(graph,individual_text,proof_sha))
            for table in ('dashboard_player_game','dashboard_player_metric'):
                db.execute(f'DELETE FROM {table} WHERE graph_iri=?',(graph,))
            db.executemany('INSERT INTO dashboard_player_game VALUES (?,?,?,?,?)',people)
            db.executemany('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',records)
            db.execute('INSERT OR REPLACE INTO dashboard_player_partition VALUES (?,?)',(graph,identity))
        changed+=1
        if checkpoint and changed%100==0:checkpoint(preparedPlayerGames=changed)
    return dict(preparedGames=changed,reusedGames=len(inventory)-changed,version=version)


def query(m, db, request, scope):
    """Read small player/game products; never reconstruct graph or PA history."""
    ids=m.requested_metric_ids(request);params=(scope['gameSet'],scope['startDate'],scope['endDate'])
    graphs=[r[0] for r in db.execute('SELECT graph_iri FROM game_dimension WHERE game_set=? '
                                   'AND official_date BETWEEN ? AND ? ORDER BY graph_iri',params)]
    schedule=m.selected_schedule_coverage(db,scope,graphs)
    expected=dict(db.execute('SELECT c.graph_iri,c.input_sha256 FROM dashboard_checkpoint c '
        'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params))
    saved=dict(db.execute('SELECT p.graph_iri,p.input_sha256 FROM dashboard_player_partition p '
        'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params))
    version=fingerprint()
    individual=dict(db.execute('SELECT a.graph_iri,a.proof_sha256 FROM dashboard_player_admission a '
        'JOIN game_dimension g USING(graph_iri) WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params))
    if any(saved.get(g)!=m._hash(key+version+individual.get(g,'')) for g,key in expected.items()):
        raise m.EvidenceError('Selected player products need NiFi preparation')
    people=defaultdict(lambda:dict(pa=0,paKnown=True,games=set(),graphs=set(),roster=True))
    roster_graphs=set()
    for graph,player,pa,roster in db.execute('SELECT p.graph_iri,p.player,p.plate_appearances,p.roster_complete '
            'FROM dashboard_player_game p JOIN game_dimension g USING(graph_iri) '
            'WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?',params):
        p=people[player];p['pa']+=pa or 0;p['paKnown'] &= pa is not None
        if roster:roster_graphs.add(graph)
        p['games'].add(graph);p['graphs'].add(graph);p['roster'] &= bool(roster)
    metrics=[]
    for metric in ids:
        entry=next(e for e in m.catalog()['metrics'] if e['id']==metric)
        base=dict(metricId=metric,grain='player',coverage=dict(games=len(graphs),populationComplete=False),
            playerPopulationComplete=False,playerRecordsComplete=False,playerResults=[],
            scope='Complete player records across the entire selected range; excluded records are disclosed.')
        if metric not in PREPARED:
            # Preserve the established reference producer when a prepared
            # reference exists. Never substitute a percentile of complete cases.
            if metric in REFERENCES and db.execute('SELECT 1 FROM dashboard_reference WHERE metric_id=? LIMIT 1',(metric,)).fetchone():
                metrics.append(m.query_sql(db,{'metricId':metric},scope)['metric']);continue
            gap='SEASON_REFERENCE_UNAVAILABLE' if metric in REFERENCES else 'REVIEW_PLAYER_POPULATION' if 'review' in metric or metric=='adjudication-volatility' else 'ROLE_REALIZATION_POPULATION'
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
            rankingCoverage=dict(policy=POLICY,completePlayers=complete_people,
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
        graphCount=len(graphs),schedule=schedule,
        **({'metrics':metrics} if request.get('view')=='dashboard' else {'metric':metrics[0]}))
