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
PREVIOUS_DAMAGE_VERSION = '8412c64bdfcb34b4f464e4f96e2850bedfd6d1846918882314b52658ca91ebb0'
PREVIOUS_ZERO_PA_VERSION = '498a19c02d51b88a7418616934719d37808ab7c5100c7bfd5cfda29d9ccb0518'
PREVIOUS_RESOLUTION_VERSION = 'b47cf2b52df6240514ef87cd795ba953881f4af7a7393f849757bd685a4655eb'
PREVIOUS_SCOPED_RESOLUTION_VERSION = 'ec4104bc6b33774dd4a5a2d1b6700300c31efb054d49a1fa2a28320fd89c63e6'
PREVIOUS_HELP_VERSION = 'e0f455baeae669e3cb5f99e0e26e3b7c0ff885e4208b7f2282d7ab4ff8500275'
PREVIOUS_CHANNEL_VERSION = '7397a2cc83659359efe7a99dee4f6eafc9c7b86ae9a7fa620c20677c4474021b'
PREVIOUS_SHARED_OUT_VERSION = 'cf63597341de4a503f8f8002c5e421ae755d555d49f00dd8593966532894d13a'
PREVIOUS_PA_CONTRIBUTION_VERSION = '9a1f3425fd08919dcf0730dcb6466eae61534b4eeb1e8fa9f5076e04c0067273'
PREVIOUS_AMBIGUOUS_PROGRESS_VERSION = 'ab2fac95e7153c1c3ddc19595463ccb1c283c722b6a7e28e66a711d76fa7ed4c'
PREVIOUS_EMPTY_ELIGIBILITY_VERSION = '91af6cc2428dda5b7a12091e0ee3fb4daa7c5bfbf18db2d8fff4d99638ddfe35'
PREVIOUS_EMPTY_CACHE_VERSION = 'afc2871933b1e0351790c7314c6a4857e743104128c2a8b387c125ae6db75932'
PREVIOUS_EMPTY_SCOPE_VERSION = '29d43818e44894f2a762e129f073b74ebc76ecd01b70eb91c4c28b5e3a07cc95'
PREVIOUS_AMBIGUOUS_OUT_VERSION = '8424ddd239ef03d03da073ae26d398e04e20bd00eb9f40db1c339f9ac9172bdf'
PREVIOUS_AMBIGUOUS_ERROR_VERSION = '7769850a6c7343d4f4daf69d072f2fd809427e331611eae165d334c9736893eb'


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


def zero_independent_damage_players(rows, contribution, resolution):
    """Isolate uncertainty using the admitted complete runner population.

    A completed contribution accounts for every out; any separately retained
    nonzero running damage is excluded from this zero-only set. An unresolved PA or
    interrupted turn blocks every runner it could affect, not the whole roster.
    This certifies only zero independent damage; it never scores unknown acts.
    """
    if not admitted(resolution):return set()
    roster={r['player'] for r in rows if r['kind']=='player_team_game' and r.get('player')}
    completed={r['plateAppearance']:r for r in contribution.get('plateAppearances',[])}
    uncertain=set()
    # Nonzero, known independent damage is retained on its own channel. It
    # cannot be advertised as zero merely because its containing PA resolved.
    uncertain.update(r['player'] for p in completed.values() for r in p.get('independentRunningScores',[]))
    for row in rows:
        if row['kind'] not in {'runner_movement','runner_location'}:continue
        runner=row.get('runner');pa=row.get('plateAppearance')
        if not runner or runner not in roster or not pa:return set()
        result=completed.get(pa)
        if result is None or result.get('unattributedNonbattingEpisodes'):
            uncertain.add(runner)
    return roster-uncertain


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
        credited=m.officially_credited_player(row) if row['kind']=='plate_appearance' else row.get('player')
        if credited not in valid:continue
        if row['kind']=='player_team_game':exposures[row['player']].add((row['game'],row['team']))
        if row['kind']=='plate_appearance' and row.get('recognizedBattingResult') in ('true','1'):
            if not all(row.get(k) for k in ('player','act','paResult','paResultType','paResultJudgment','paResultDecision','paResultRecord')):
                raise m.EvidenceError('Individually admitted PA lacks RDF result bindings')
            value=dict(graph=graph,plateAppearance=row['entity'],player=credited)
            if row['entity'] in members and members[row['entity']]!=value:
                raise m.EvidenceError('Individually admitted PA has conflicting ownership')
            members[row['entity']]=value
    if set(exposures)!=valid:raise m.EvidenceError('Individually admitted player lacks RDF participation')
    counts=Counter(r['player'] for r in members.values())
    return dict(officialPlateAppearanceCreditVerified=bool(valid),teamGameExposureVerified=bool(valid),
        selectedGamesComplete=True,expectedObservations=sorted(members.values(),key=m._json),
        participation=[dict(player=p,plateAppearances=counts[p],completeParticipation=True,dateScope=scope,
            teamGameExposure=[dict(game=g,team=t) for g,t in sorted(exposures[p])]) for p in sorted(valid)])


def binary_help_inputs(m, rows, progress):
    """Resolve only Help's eligibility and yes/no answer, using the same reducer.

    Keep every segment and history member of each selected runner. Other
    runners cannot change a known batter positive (ineligible), or a known
    positive teammate contribution when the batter's own progress is zero.
    The caller still requires the full PA resolution census and B1 membership.
    No complete reach, contribution amount or running channel is asserted.
    """
    turns=defaultdict(list);movements=defaultdict(list);histories=defaultdict(list)
    current=defaultdict(set)
    for row in rows:
        if row['kind']=='plate_appearance':turns[row['entity']].append(row)
        elif row['kind']=='runner_movement':
            movements[row.get('runner')].append(row)
            current[row['plateAppearance']].add(row.get('runner'))
        elif row['kind']=='runner_history':histories[row['player']].append(row)
    output={}
    for item in progress.get('unresolvedPlateAppearances',[]):
        if not item.get('officialResult') or not item.get('player'):continue
        pa,player=item['plateAppearance'],item['player']
        def selected(people):
            evidence=[*turns[pa],*(r for p in people for r in movements[p]),
                      *(r for p in people for r in histories[p])]
            result=m.batting_progress_evidence(evidence)
            return next((r for r in result['plateAppearances'] if r['plateAppearance']==pa),None)
        own=selected({player})
        if own is None:continue
        if own['batterPositive']:
            output[pa]=dict(player=player,eligible=False,positive=True)
            continue
        complete=True;helped=False
        for runner in sorted(current[pa]-{player},key=lambda p:p or ''):
            other=selected({player,runner}) if runner else None
            if other is not None and runner in other['otherPositivePlayers']:
                helped=True;break
            if other is None:complete=False
        if helped or complete:
            output[pa]=dict(player=player,eligible=True,value=int(helped),positive=helped)
    return output


def channel_gap_players(rows, progress):
    """Bound a completed PA's running uncertainty to its actual participants.

    The caller requires the admitted full resolution census. Include its batter
    as well as every runner, preserving the failed-hit-and-run uncertainty.
    No attribution, channel, or episode count is supplied for those people.
    """
    runners=defaultdict(set)
    for row in rows:
        if row['kind']=='runner_movement':runners[row['plateAppearance']].add(row.get('runner'))
    return {pa['plateAppearance']:sorted({pa['player'],*runners[pa['plateAppearance']]})
            for pa in progress.get('plateAppearances',[]) if pa.get('independentEpisodeGaps')
            and pa.get('player') and runners[pa['plateAppearance']] and None not in runners[pa['plateAppearance']]}


def ambiguous_progress_players(rows, progress, *, positive_only=False, excluded_result_types=()):
    """Keep unknown batting credit with every observed candidate and runner.

    The retained RDF can identify the participants even when it cannot choose
    the credited batter. This supplies no attribution or score. Missing actor
    bindings retain the whole-roster fallback; the caller still requires the
    admitted resolution census before declaring an Empty Game.
    """
    turns={p['plateAppearance'] for p in progress.get('unresolvedPlateAppearances',[])
           if p.get('gaps')==['AMBIGUOUS_BATTING_CONTRIBUTOR'] and p.get('possiblePositivePlayers') is None}
    actors=defaultdict(set);runners=defaultdict(set);result_types=defaultdict(set)
    batters=set();movements=set();out_only={pa:True for pa in turns}
    for row in rows:
        if row['kind']=='plate_appearance' and row['entity'] in turns:
            pa=row['entity'];actors[pa].add(row.get('player'));batters.add(pa)
            if row.get('recognizedBattingResult') in ('true','1'):
                result_types[pa].add(row.get('paResultType'))
        elif row['kind']=='runner_movement' and row['plateAppearance'] in turns:
            pa=row['plateAppearance'];actors[pa].add(row.get('runner'));movements.add(pa)
            runners[pa].add(row.get('runner'))
            out_only[pa] &= (row.get('hasOutType')=='true' and row.get('hasSafeType')=='false'
                             and row.get('hasRunType')=='false')
    # Unknown official batting credit cannot create a positive contribution
    # when the admitted complete resolution population contains only outs.
    # Keep eligibility and all nonbinary metrics unresolved for those batters.
    # The settled Error/FC/interference exclusion applies to every batting
    # contributor, even if official PA credit is ambiguous. Keep running
    # uncertainty with the actual runners and leave other metrics unchanged.
    return {pa:[] if positive_only and out_only[pa] else sorted(
                runners[pa] if positive_only and len(result_types[pa])==1
                and result_types[pa]<=set(excluded_result_types) else actors[pa])
            for pa in batters & movements if actors[pa] and None not in actors[pa]}


def empty_running_entries(m, rows, progress):
    """EG3's binary running credit; existing weighted channels stay unchanged."""
    turns={p['plateAppearance'] for p in progress.get('unresolvedPlateAppearances',[])}
    types=defaultdict(set); movements=defaultdict(list); histories=defaultdict(list); whole_rows=defaultdict(list)
    for row in rows:
        if row['kind']=='plate_appearance' and row.get('recognizedBattingResult') in ('true','1'):
            types[row['entity']].add(row.get('paResultType'))
        elif row['kind']=='runner_history':histories[(row['graph'],row['trajectory'])].append(row)
        elif row['kind']=='runner_movement':
            movements[row['plateAppearance']].append(row)
            if row.get('trajectory'):whole_rows[(row['graph'],row['trajectory'])].append(row)
    result={}
    for pa in turns:
        if types[pa]!={'https://baseballontology.org/StrikeoutProcess'}:continue
        groups=defaultdict(list)
        for row in movements[pa]:groups[row.get('runner')].append(row)
        positive=[]
        for runner,states in groups.items():
            if not runner:continue
            # Duplicate identical bindings are harmless; conflicting states for
            # one resolution must never pass as a complete personal path.
            unique={m._json(r):r for r in states};states=list(unique.values())
            if len({r.get('resolution') for r in states})!=len(states):continue
            entry=[r for r in states if r.get('batter')==runner and m.segment_origin(r)==0
                and r.get('destinationCode')=='1B' and r.get('hasSafeType')=='true'
                and r.get('hasOutType')=='false' and r.get('hasRunType')=='false'
                and all(r.get(k) for k in (*m.INDEPENDENT_RUNNING_FIELDS,'record','act','episode','resolution',
                                         'safeJudgment','safeDecision','destinationBase'))
                and r['independentRunningType'] in {'https://baseballontology.org/WildPitchProcess',
                                                    'https://baseballontology.org/PassedBallProcess'}
                and not r.get('contactPlay') and not r.get('award')]
            if len(entry)!=1:continue
            if len(states)>1:
                path=m.runner_progress_path(states,histories,whole_rows)
                if path['status']!='available' or path['end'] is None or not path['positive']:continue
            positive.append(runner)
        if positive:result[pa]=sorted(positive)
    return result


def empty_scoring_inputs(m, rows, progress):
    """EG5 binary attribution from promoted scoring decisions and actual paths.

    A mixed contact/error record remains uncertain; its error label alone
    cannot exclude all progress. Explicit RBI credit can establish a batter
    positive without supplying a numeric advance or transferring running credit.
    """
    turns={p['plateAppearance'] for p in progress.get('unresolvedPlateAppearances',[])}
    actors=defaultdict(set);types=defaultdict(set);moves=defaultdict(list)
    histories=defaultdict(list);whole_rows=defaultdict(list)
    for row in rows:
        if row['kind']=='plate_appearance':
            actors[row['entity']].add(row.get('player'))
            if row.get('recognizedBattingResult') in ('true','1'):types[row['entity']].add(row.get('paResultType'))
        elif row['kind']=='runner_history':histories[(row['graph'],row['trajectory'])].append(row)
        elif row['kind']=='runner_movement':
            moves[row['plateAppearance']].append(row)
            if row.get('trajectory'):whole_rows[(row['graph'],row['trajectory'])].append(row)
    output={};excluded=set(m.policies()['batterProgressExcludedResultTypes'])
    for pa in turns:
        if (not actors[pa] or None in actors[pa] or len(types[pa])!=1
                or not any(r.get('secondaryError') or r.get('rbiDecision') for r in moves[pa])):continue
        batting=set() if types[pa]<=excluded else actors[pa]
        possible=set();positive=set();groups=defaultdict(list)
        for row in moves[pa]:groups[row.get('runner')].append(row)
        if None in groups:continue
        for runner,states in groups.items():
            states=list({m._json(r):r for r in states}.values())
            if len({r['resolution'] for r in states})!=len(states):
                possible.update(batting|{runner});continue
            if len(states)>1:
                path=m.runner_progress_path(states,histories,whole_rows)
                if path['status']!='available':possible.update(batting|{runner});continue
                if path['end'] is None:continue
            for row in states:
                outcome=(row.get('hasSafeType'),row.get('hasOutType'),row.get('hasRunType'))
                if outcome==('false','true','false'):continue
                start=m.segment_origin(row)
                end=4 if outcome==('false','false','true') else int(row['destinationCode'][0]) if outcome==('true','false','false') and row.get('destinationCode') in {'1B','2B','3B'} else None
                if start is None or end is None or end<start:
                    possible.update(batting|{runner});continue
                if start==end:continue
                rbi=(end==4 and row.get('rbiPlayer') in batting and all(row.get(k)
                     for k in ('rbiPlayer','rbiJudgment','rbiDecision','rbiRecord')))
                if rbi:positive.add(row['rbiPlayer'])
                contact=bool(row.get('contactPlay'));award=bool(row.get('award') and row.get('awardRule'))
                running=bool(m.independent_running_act(row))
                error=all(row.get(k) for k in ('secondaryError','errorJudgment','errorDecision','record'))
                if sum((contact,award,running))>1:
                    possible.update(batting|{runner});continue
                if running:positive.add(runner)
                elif contact or award:
                    if len(batting)==1:positive.update(batting)
                    else:possible.update(batting)
                elif error and not row.get('errorContactPlay'):
                    pass  # A separately scored, noncontact error-only advance.
                else:
                    possible.update(batting|{runner})
        output[pa]=dict(positivePlayers=sorted(positive),possiblePositivePlayers=sorted(possible))
    return output


def resolution_census_players(rows, roster, resolution, individual):
    """Reuse admitted PA censuses for a team's entire offensive inventory.

    Every turn counts, including interrupted turns without an official PA.
    A player can run during a teammate's turn, so checking only their own PAs
    would be insufficient. Missing ownership or inventory still blocks this
    fallback; this does not establish any contribution or repair a proof.
    """
    if admitted(resolution):return set(roster)
    if not (individual.get('rosterComplete') is True and
            individual.get('plateAppearanceInventoryComplete') is True):return set()
    resolved={p['plateAppearance'] for p in (individual.get('paResolutions') or {}).get('plateAppearances',[])
              if p['status']=='admitted'}
    owners=defaultdict(set)
    for row in rows:
        if row['kind']!='plate_appearance':continue
        teams=roster.get(row.get('player'),set())
        if len(teams)!=1:return set()
        owners[row['entity']].update(teams)
    if not owners or any(len(teams)!=1 for teams in owners.values()):return set()
    incomplete={next(iter(teams)) for pa,teams in owners.items() if pa not in resolved}
    return {player for player,teams in roster.items() if not teams & incomplete}


def project(m, *, graph, scope, rows, proofs, inputs, runs, run_people, metric_ids=None):
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
    selected=PREPARED if metric_ids is None else PREPARED & set(metric_ids)
    contrib=inputs['contribution'];progress=inputs['progress'];defense=inputs.get('defense',{})
    by_pa={p['plateAppearance']:p for p in contrib.get('plateAppearances',[])}
    progress_pa={p['plateAppearance']:p for p in progress.get('plateAppearances',[]) if p['officialResult']}
    resolved={p['plateAppearance'] for p in (individual.get('paResolutions') or {}).get('plateAppearances',[])
              if p['status']=='admitted'}
    help_inputs=inputs.get('binaryHelp',{})
    certain_positive=set()
    positive=set();uncertain=set();mix_uncertain=set();channels=defaultdict(set);episodes=defaultdict(set)
    for pa in progress.get('plateAppearances',[]):
        if pa['reach']:positive.add(pa['player'])
        positive.update(r['player'] for r in pa['independentPositive'])
        if pa['plateAppearance'] in resolved:
            if pa['reach']:certain_positive.add(pa['player'])
            certain_positive.update(r['player'] for r in pa['independentPositive'])
        uncertain.update(pa.get('unresolvedRunningPositivePlayers',[]))
        if pa.get('independentPositiveGaps') and not pa.get('unresolvedRunningPositivePlayers'):
            uncertain.update(roster)
        for r in pa['positiveChannels']:channels[r['player']].add((r['play'],r['channel']))
        for r in pa['independentEpisodes']:episodes[r['player']].add(r['episode'])
        if pa['independentEpisodeGaps']:
            # An unresolved attempt affects its batter and runners. Retain the
            # whole-roster fallback when the retained census cannot bound them.
            mix_uncertain.update(inputs.get('channelGapPlayers',{}).get(pa['plateAppearance'],roster))
    for pa in progress.get('unresolvedPlateAppearances',[]):
        affected=pa.get('possiblePositivePlayers')
        if affected is None:
            affected=inputs.get('ambiguousProgressPlayers',{}).get(pa['plateAppearance'],roster)
        mix_uncertain.update(affected)
        if pa.get('possiblePositivePlayers') is None:
            affected=inputs.get('ambiguousEmptyPositivePlayers',{}).get(pa['plateAppearance'],affected)
        affected=set(affected)
        scoring=inputs.get('emptyScoring',{}).get(pa['plateAppearance'])
        if scoring is not None and (admitted(proofs['resolution']) or pa['plateAppearance'] in resolved):
            affected=set(scoring['possiblePositivePlayers'])
            positive.update(scoring['positivePlayers']);certain_positive.update(scoring['positivePlayers'])
        positive.update(pa.get('confirmedPositivePlayers',[]))
        if pa['plateAppearance'] in resolved:certain_positive.update(pa.get('confirmedPositivePlayers',[]))
        uncertain.update(affected)
    for pa,players in inputs.get('emptyRunningEntries',{}).items():
        if admitted(proofs['resolution']) or pa in resolved:
            positive.update(players);certain_positive.update(players)
    for pa,item in help_inputs.items():
        if item['positive'] and (admitted(proofs['resolution']) or pa in resolved):
            positive.add(item['player']);certain_positive.add(item['player'])
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
    empty_population=((admitted(proofs['batting']) or individual.get('plateAppearanceInventoryComplete') is True)
        and {r['entity'] for r in rows if r['kind']=='plate_appearance'}==
            {p['plateAppearance'] for p in [*progress.get('plateAppearances',[]),*progress.get('unresolvedPlateAppearances',[])]})
    resolution_players=resolution_census_players(rows,roster,proofs['resolution'],individual)
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
    for metric in DEFENSE & selected:
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
        # Batting progress averages have no observations in a verified zero-PA
        # game. Unrelated running uncertainty cannot turn that known absence
        # into a missing batting record. Unknown official PA counts stay blocked.
        progress_ok=person is not None and (admitted(proofs['resolution']) or own<=resolved) and len(own_progress)==len(own)
        own_help={p['plateAppearance']:dict(eligible=not p['batterPositive'],value=int(bool(p['otherPositivePlayers'])))
                  for p in own_progress}
        own_help.update({pa:item for pa,item in help_inputs.items() if pa in own and item['player']==player})
        help_ok=person is not None and (admitted(proofs['resolution']) or own<=resolved) and set(own_help)==own
        empty_eligible=(bool(pa_count) if person is not None else
                        True if player in individual.get('eligiblePlayers',[]) else None)
        empty_known=(empty_eligible is not None and (player in certain_positive or
                     (player in resolution_players and empty_population
                      and (player in positive or empty_population and player not in uncertain))))
        for metric in sorted(selected):
            complete=False;aggregate=zero();reason='OFFICIAL_PA_POPULATION'
            if metric in RUNS:
                complete=player not in run_unknown[metric]
                aggregate=mean(m,run_values[metric][player]);reason='COMPLETE_SCORING_HISTORIES'
            elif metric in DEFENSE:
                complete,values=defensive[metric]
                aggregate=values.get(player,zero());reason='DEFENSIVE_POPULATION'
            elif metric=='empty-game-rate':
                complete=empty_eligible is False or (empty_eligible is True and empty_known)
                aggregate=dict(kind='count',count=int(empty_eligible is True and player not in positive),
                               eligibleGames=int(empty_eligible is True))
                reason='OFFENSIVE_ELIGIBILITY' if empty_eligible is None else 'COMPLETE_EMPTY_GAME_CLASSIFICATION'
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
                    if metric=='offensive-reach':aggregate=mean(m,[Fraction(p['reach']) for p in own_progress])
                    else:
                        complete=help_ok
                        aggregate=mean(m,[Fraction(p['value']) for p in own_help.values() if p['eligible']])
                elif metric=='contribution-path-diversity':
                    complete=(admitted(proofs['resolution']) and progress_census and player not in mix_uncertain
                              and progress_ok)
                    reason='COMPLETE_CONTRIBUTION_CHANNELS'
                    counts=Counter(c for _,c in channels[player])
                    aggregate=dict(kind='channel_entropy',channelCounts=[counts[c] for c in ('batter_self','batter_other','runner_self')],
                                   independentRunningEpisodes=len(episodes[player]))
                elif metric=='empty-game-damage':
                    complete=not own or (empty_known and player in positive)
                    damage_known=(contrib.get('independentDamageComplete') is True
                                  or player in contrib.get('zeroIndependentDamagePlayers',[]))
                    if own and empty_known and player not in positive and contrib_ok and damage_known:
                        running=[r['score'] for pa in contrib.get('plateAppearances',[])
                                 for r in pa.get('independentRunningScores',[]) if r['player']==player]
                        score=m.empty_game_damage([r['score'] for r in own_contrib],running,empty=True,complete=True)
                        complete=score['status']=='available'
                        if complete:aggregate=mean(m,[m.fraction(score['value'])])
                    reason='INDEPENDENT_DAMAGE_COVERAGE'
            complete=complete and roster_ok
            records.append((graph,player,metric,int(complete),m._json(aggregate),None if complete else reason))
    return participation,records


def prepare(m, db, checkpoint=None, player_admissions=None, metric_ids=None):
    initialize(db);version=fingerprint();changed=0;zero_pa_repairs=0
    # The player dashboard serves only these game sets. Exhibition/WBC roster
    # patterns must not participate in, or block, MLB dashboard preparation.
    inventory=db.execute('SELECT g.graph_iri,g.official_date,g.game_set,c.input_sha256 '
        "FROM game_dimension g JOIN dashboard_checkpoint c USING(graph_iri) "
        "WHERE g.game_set IN ('regular_season','all_star') ORDER BY g.graph_iri").fetchall()
    inventory_keys={graph:key for graph,_,_,key in inventory}
    saved=dict(db.execute('SELECT graph_iri,input_sha256 FROM dashboard_player_partition'))
    # Older no-op migrations advanced a partition key while retaining the
    # retired rate-denominator refusal for this count. Reproject those exact
    # partitions from their existing inputs even if their key says current.
    for graph, in db.execute("SELECT DISTINCT graph_iri FROM dashboard_player_metric "
            "WHERE metric_id='empty-game-rate' AND complete=0 AND reason='OFFICIAL_PA_POPULATION'"):
        saved.pop(graph,None)
    player_admissions=player_admissions or {}
    channel_candidates=set();ambiguity_candidates=set()
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    pending=[graph for graph,_,_,key in inventory if saved.get(graph)!=m._hash(key+version+
             (m._hash(m._json(player_admissions[graph])) if player_admissions.get(graph) else ''))]
    if 'metric_suite_input_state' in tables:
        ambiguity_candidates={r[0] for r in db.execute("SELECT graph_iri FROM metric_suite_input_state "
            "WHERE family='progress' AND json_array_length(state_json,'$.unresolvedPlateAppearances')>0")}
    if {'metric_suite_input_row','metric_suite_runner_resolution_admission'}<=tables:
        for offset in range(0,len(pending),400):
            group=pending[offset:offset+400];marks=','.join('?' for _ in group)
            channel_candidates.update(r[0] for r in db.execute(f"""SELECT DISTINCT i.graph_iri
                FROM metric_suite_input_row i JOIN metric_suite_runner_resolution_admission a USING(graph_iri)
                WHERE i.graph_iri IN ({marks}) AND i.family='progress'
                AND json_array_length(i.record_json,'$.independentEpisodeGaps')>0
                AND json_extract(a.proof_json,'$.status')='admitted'""",group))
    if 'metric_suite_runner_resolution_admission' in tables:
        for graph,text,sha in db.execute('SELECT graph_iri,proof_json,proof_sha256 FROM metric_suite_runner_resolution_admission'):
            individual=player_admissions.get(graph) or {}
            if (individual.get('rosterComplete') is True and individual.get('plateAppearanceInventoryComplete') is True
                    and any(p['status']=='admitted' for p in (individual.get('paResolutions') or {}).get('plateAppearances',[]))
                    and not admitted(m._blocks.decode(m._block_api(),text,sha))):
                # Only these games can gain the scoped negative classification.
                # Preserve current products; older compatible products need the
                # projection once, without recalculating their metric inputs.
                current=inventory_keys.get(graph)
                if current and saved.get(graph)!=m._hash(current+version+m._hash(m._json(individual))):
                    saved.pop(graph,None)
    for graph,day,game_set,key in inventory:
        individual=player_admissions.get(graph) or {}
        individual_text=m._json(individual);proof_sha=m._hash(individual_text) if individual else ''
        identity=m._hash(key+version+proof_sha)
        if saved.get(graph)==identity:continue
        ambiguity_upgrade=graph in ambiguity_candidates
        if not ambiguity_upgrade and saved.get(graph) in {m._hash(key+v+proof_sha) for v in
                (PREVIOUS_EMPTY_ELIGIBILITY_VERSION,PREVIOUS_EMPTY_CACHE_VERSION,PREVIOUS_EMPTY_SCOPE_VERSION,
                 PREVIOUS_AMBIGUOUS_OUT_VERSION,PREVIOUS_AMBIGUOUS_ERROR_VERSION)}:
            # Scoped resolution candidates were removed above. Otherwise an
            # unchanged proof retains the same eligibility and classification.
            with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        if not ambiguity_upgrade and saved.get(graph)==m._hash(key+PREVIOUS_AMBIGUOUS_PROGRESS_VERSION+proof_sha):
            with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        channel_upgrade=graph in channel_candidates or ambiguity_upgrade
        if not ambiguity_upgrade and saved.get(graph)==m._hash(key+PREVIOUS_PA_CONTRIBUTION_VERSION+proof_sha):
            scoped=any(p['status']=='admitted' for p in (individual.get('paResolutions') or {}).get('plateAppearances',[]))
            resolution=db.execute('SELECT proof_json,proof_sha256 FROM metric_suite_runner_resolution_admission WHERE graph_iri=?',
                (graph,)).fetchone() if scoped else None
            if not scoped or (resolution and admitted(m._blocks.decode(m._block_api(),*resolution))):
                with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
                continue
        if not channel_upgrade and saved.get(graph)==m._hash(key+PREVIOUS_SHARED_OUT_VERSION+proof_sha):
            # The checkpoint key changes for repaired compound games. With
            # unchanged inputs, earlier products have no shared-out scores.
            with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        if not channel_upgrade and saved.get(graph)==m._hash(key+PREVIOUS_CHANNEL_VERSION+proof_sha):
            with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        if not channel_upgrade and saved.get(graph)==m._hash(key+PREVIOUS_HELP_VERSION+proof_sha):
            row=db.execute("SELECT state_json,state_sha256 FROM metric_suite_input_state WHERE graph_iri=? AND family='progress'",(graph,)).fetchone()
            state=m._blocks.decode(m._block_api(),*row) if row else {}
            unresolved=state.get('unresolvedPlateAppearances',[])
            resolution=db.execute('SELECT proof_json,proof_sha256 FROM metric_suite_runner_resolution_admission WHERE graph_iri=?',(graph,)).fetchone() if unresolved else None
            resolution=m._blocks.decode(m._block_api(),*resolution) if resolution else {}
            scoped={p['plateAppearance'] for p in (individual.get('paResolutions') or {}).get('plateAppearances',[]) if p['status']=='admitted'}
            if row and not any(p.get('officialResult') and (admitted(resolution) or p['plateAppearance'] in scoped) for p in unresolved):
                with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
                continue
        if not channel_upgrade and not individual.get('paResolutions') and saved.get(graph) in {
                m._hash(key+v+proof_sha) for v in (PREVIOUS_RESOLUTION_VERSION,PREVIOUS_SCOPED_RESOLUTION_VERSION)}:
            with db:db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        # Repair this projection directly from verified SQL participation.
        # All unchanged calculations and other player aggregates stay intact.
        if not channel_upgrade and (saved.get(graph)==m._hash(key+PREVIOUS_ZERO_PA_VERSION+proof_sha) or
                (not individual and (saved.get(graph) in
                {m._hash(key+v+proof_sha) for v in (PREVIOUS_INDIVIDUAL_VERSION,PREVIOUS_BOUNDARY_VERSION,PREVIOUS_DAMAGE_VERSION)}
                or saved.get(graph)==m._hash(key+PREVIOUS_VERSION)))):
            with db:
                zero_pa_repairs+=db.execute('''UPDATE dashboard_player_metric SET complete=1,aggregate_json=?,reason=NULL
                    WHERE graph_iri=? AND complete=0 AND metric_id IN ('offensive-reach','hidden-help-rate')
                    AND player IN (SELECT player FROM dashboard_player_game
                        WHERE graph_iri=? AND roster_complete=1 AND plate_appearances=0)''',
                    (m._json(zero()),graph,graph)).rowcount
                db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',(identity,graph))
            continue
        rows=m._blocks.read_scope(m._block_api(),db,[graph])
        proofs={}
        for kind,table in [('batting','metric_suite_admission'),('run','metric_suite_run_admission'),
                           ('resolution','metric_suite_runner_resolution_admission'),
                           ('boundary','metric_suite_boundary_admission')]:
            row=db.execute(f'SELECT proof_json,proof_sha256 FROM {table} WHERE graph_iri=?',(graph,)).fetchone()
            proofs[kind]=m._blocks.decode(m._block_api(),*row) if row else {}
        proofs['players']=individual
        input_families=('contribution','progress','defense') if metric_ids is None or DEFENSE & set(metric_ids) else ('contribution','progress')
        inputs={f:m._blocks.read_inputs(m._block_api(),db,f,[graph])[graph] for f in input_families}
        resolved={p['plateAppearance'] for p in (individual.get('paResolutions') or {}).get('plateAppearances',[]) if p['status']=='admitted'}
        help_progress=dict(unresolvedPlateAppearances=[p for p in inputs['progress'].get('unresolvedPlateAppearances',[])
            if admitted(proofs['resolution']) or p['plateAppearance'] in resolved])
        needs_contribution=individual.get('paBoundaries') and not inputs['contribution'].get('complete')
        needs_channels=admitted(proofs['resolution']) and any(p.get('independentEpisodeGaps') for p in inputs['progress'].get('plateAppearances',[]))
        needs_ambiguity=any(p.get('gaps')==['AMBIGUOUS_BATTING_CONTRIBUTOR']
                            for p in inputs['progress'].get('unresolvedPlateAppearances',[]))
        if needs_contribution or needs_channels or needs_ambiguity or help_progress['unresolvedPlateAppearances']:
            evidence=[m._blocks.decode(m._block_api(),text,sha) for text,sha in db.execute(
                'SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,))]
            saved_proof=json.loads(db.execute('SELECT proof_json FROM dashboard_checkpoint WHERE graph_iri=?',(graph,)).fetchone()[0])
            if len(evidence)!=saved_proof['evidenceRows']:raise m.EvidenceError('Stored dashboard evidence is incomplete')
            evidence.sort(key=m._json)
            if help_progress['unresolvedPlateAppearances']:
                inputs['binaryHelp']=binary_help_inputs(m,evidence,help_progress)
                inputs['emptyRunningEntries']=empty_running_entries(m,evidence,help_progress)
                inputs['emptyScoring']=empty_scoring_inputs(m,evidence,help_progress)
            if needs_channels:
                inputs['channelGapPlayers']=channel_gap_players(evidence,inputs['progress'])
            if needs_ambiguity:
                inputs['ambiguousProgressPlayers']=ambiguous_progress_players(evidence,inputs['progress'])
                inputs['ambiguousEmptyPositivePlayers']=ambiguous_progress_players(evidence,inputs['progress'],positive_only=True,
                    excluded_result_types=m.policies()['batterProgressExcludedResultTypes'])
        if needs_contribution:
            inputs['contribution']=m.contribution_game_inputs(evidence,graph=graph,batting_admission=proofs['batting'],
                runner_resolution_admission=proofs['resolution'],runner_boundary_admission=proofs['boundary'],player_admission=individual)
            inputs['contribution']['zeroIndependentDamagePlayers']=sorted(
                zero_independent_damage_players(evidence,inputs['contribution'],proofs['resolution']))
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
            rows=rows,proofs=proofs,inputs=inputs,runs=runs,run_people=run_people,metric_ids=metric_ids)
        with db:
            db.execute('DELETE FROM dashboard_player_admission WHERE graph_iri=?',(graph,))
            if individual:db.execute('INSERT INTO dashboard_player_admission VALUES (?,?,?)',(graph,individual_text,proof_sha))
            db.execute('DELETE FROM dashboard_player_game WHERE graph_iri=?',(graph,))
            if metric_ids is None:db.execute('DELETE FROM dashboard_player_metric WHERE graph_iri=?',(graph,))
            else:
                db.executemany('DELETE FROM dashboard_player_metric WHERE graph_iri=? AND metric_id=?',
                    [(graph,metric) for metric in metric_ids])
            db.executemany('INSERT INTO dashboard_player_game VALUES (?,?,?,?,?)',people)
            db.executemany('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',records)
            db.execute('INSERT OR REPLACE INTO dashboard_player_partition VALUES (?,?)',(graph,identity))
        changed+=1
        if checkpoint and changed%100==0:checkpoint(preparedPlayerGames=changed)
    return dict(preparedGames=changed,reusedGames=len(inventory)-changed,repairedZeroPARows=zero_pa_repairs,version=version)


def prepare_family(m, db, family, metric_ids, player_admissions, checkpoint=None):
    """Nonoffensive projections never execute offensive scoring or histories."""
    if family=='offense':
        return prepare(m,db,checkpoint=checkpoint,player_admissions=player_admissions,metric_ids=metric_ids)
    changed=0;version=fingerprint()
    inventory=db.execute('SELECT g.graph_iri,g.official_date,g.game_set,c.input_sha256 '
        'FROM game_dimension g JOIN dashboard_family_checkpoint c USING(graph_iri) '
        "WHERE c.family=? AND g.game_set IN ('regular_season','all_star') ORDER BY g.graph_iri",(family,)).fetchall()
    saved=dict(db.execute('SELECT graph_iri,input_sha256 FROM dashboard_family_player_partition WHERE family=?',(family,)))
    for graph,day,game_set,key in inventory:
        identity=m._hash(key+version)
        if saved.get(graph)==identity:continue
        rows=m._blocks.read_scope(m._block_api(),db,[graph]);proofs={}
        for kind,table in [('batting','metric_suite_admission'),('run','metric_suite_run_admission')]:
            row=db.execute(f'SELECT proof_json,proof_sha256 FROM {table} WHERE graph_iri=?',(graph,)).fetchone()
            proofs[kind]=m._blocks.decode(m._block_api(),*row) if row else {}
        roster=defaultdict(set)
        for row in rows:
            if row['kind']=='player_team_game' and all(row.get(k) for k in ('player','team','teamRole')):
                roster[row['player']].add(row['team'])
        if any(len(teams)!=1 for teams in roster.values()):raise m.EvidenceError('Player has conflicting game-team exposure')
        roster_ok=bool(roster) and (admitted(proofs['batting']) or admitted(proofs['run']) or
            (player_admissions.get(graph) or {}).get('rosterComplete') is True)
        records=[]
        if family=='defense':
            defense=m._blocks.read_inputs(m._block_api(),db,'defense',[graph])[graph]
            for metric in sorted(DEFENSE & set(metric_ids)):
                result=m.defensive_players(metric,[defense],rows,graphs=[graph],
                    date_scope=dict(gameSet=game_set,startDate=day,endDate=day),schedule={'complete':True},
                    roster_admissions={graph:[proofs['batting'],proofs['run']]})
                complete=roster_ok and result.get('playerPopulationComplete') is True
                values={p['player']:p['aggregate'] for p in result.get('playerResults',[])}
                records.extend((graph,p,metric,int(complete),m._json(values.get(p,zero())),
                    None if complete else 'DEFENSIVE_POPULATION') for p in sorted(roster))
        with db:
            db.execute('DELETE FROM dashboard_family_player_game WHERE family=? AND graph_iri=?',(family,graph))
            db.executemany('INSERT INTO dashboard_family_player_game VALUES (?,?,?,?,?,?)',
                [(family,graph,p,next(iter(teams)),None,int(roster_ok)) for p,teams in sorted(roster.items())])
            db.executemany('DELETE FROM dashboard_player_metric WHERE graph_iri=? AND metric_id=?',
                [(graph,metric) for metric in metric_ids])
            db.executemany('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',records)
            db.execute('INSERT OR REPLACE INTO dashboard_family_player_partition VALUES (?,?,?)',(family,graph,identity))
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
