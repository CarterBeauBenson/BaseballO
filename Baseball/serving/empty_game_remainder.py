"""Group the published Empty Games remainder; never admit or score a record.

NiFi's existing dashboard builder writes this after publication. It reads its
prepared player records and retained diagnostics, without SPARQL, raw-source
recovery, another validation gate, or a new repair authority.
"""
from collections import defaultdict


def summarize(m, db, build_id):
    season, = db.execute("SELECT MAX(season) FROM game_dimension WHERE game_set='regular_season'").fetchone()
    records = db.execute("""SELECT p.graph_iri,p.player,p.reason
        FROM dashboard_player_metric p JOIN game_dimension g USING(graph_iri)
        WHERE p.metric_id='empty-game-rate' AND p.complete=0
          AND g.game_set='regular_season' AND g.season=? ORDER BY p.graph_iri,p.player""", (season,)).fetchall()
    by_game = defaultdict(list)
    for graph, player, reason in records: by_game[graph].append((player, reason))
    families = defaultdict(list)
    for graph, people in by_game.items():
        progress = m._blocks.read_inputs(m._block_api(), db, 'progress', [graph])[graph]
        row = db.execute('SELECT proof_json,proof_sha256 FROM dashboard_player_admission WHERE graph_iri=?', (graph,)).fetchone()
        individual = m._blocks.decode(m._block_api(), *row) if row else {}
        row = db.execute('SELECT proof_json,proof_sha256 FROM metric_suite_runner_resolution_admission WHERE graph_iri=?', (graph,)).fetchone()
        resolution = m._blocks.decode(m._block_api(), *row) if row else {}
        held_censuses = [p for p in (individual.get('paResolutions') or {}).get('plateAppearances', [])
                        if p.get('status') != 'admitted']
        for player, reason in people:
            held = [p for p in progress.get('unresolvedPlateAppearances', [])
                    if p.get('possiblePositivePlayers') is None or player in p['possiblePositivePlayers']]
            running = [p for p in progress.get('plateAppearances', [])
                       if player in p.get('unresolvedRunningPositivePlayers', [])
                       or p.get('independentPositiveGaps') and not p.get('unresolvedRunningPositivePlayers')]
            gaps = {gap for p in held for gap in p.get('gaps', [])}
            if running: gaps.add('UNRESOLVED_RUNNING_EPISODE_ATTRIBUTION')
            if reason == 'OFFENSIVE_ELIGIBILITY': family = reason
            elif gaps: family = '+'.join(sorted(gaps))
            elif resolution.get('status') != 'admitted': family = 'RUNNER_RESOLUTION_CENSUS'
            else: family = 'PLAYER_PROJECTION_DEPENDENCY'
            families[family].append(dict(graph=graph, player=player, reason=reason,
                plateAppearances=sorted({p['plateAppearance'] for p in [*held, *running]}),
                withheldCensuses=held_censuses,
                playerIssues=next((p.get('issues', []) for p in individual.get('players', [])
                                   if p.get('player') == player), [])))
    groups = [dict(family=family, playerGames=len(items), players=len({r['player'] for r in items}),
                   games=len({r['graph'] for r in items}), records=items)
              for family, items in families.items()]
    groups.sort(key=lambda group: (-group['players'], -group['playerGames'], group['family']))
    complete_players, = db.execute("""SELECT COUNT(*) FROM (
        SELECT p.player FROM dashboard_player_metric p JOIN game_dimension g USING(graph_iri)
        WHERE p.metric_id='empty-game-rate' AND g.game_set='regular_season' AND g.season=?
        GROUP BY p.player HAVING MIN(p.complete)=1
          AND SUM(json_extract(p.aggregate_json,'$.eligibleGames'))>0)""", (season,)).fetchone()
    summary = dict(season=season, completeEligiblePlayers=complete_players,
                   incompletePlayers=len({r[1] for r in records}), incompletePlayerGames=len(records),
                   affectedGames=len(by_game), families=[{k:v for k,v in g.items() if k!='records'} for g in groups])
    return dict(artifactType='baseballo-empty-game-remainder', publicationId=build_id,
                diagnosticOnly=True, summary=summary, families=groups)
