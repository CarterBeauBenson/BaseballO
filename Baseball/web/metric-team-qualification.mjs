import { DatabaseSync } from 'node:sqlite';
import { resolve } from 'node:path';

// Lightweight qualification over the exact immutable SQL snapshot already
// verified by the serving worker. No graph access or metric recalculation.
export function selectedTeamMinimums(result, stateRoot) {
  if (result.serving?.publication !== 'dashboard') return result;
  const id = result.serving.buildId;
  if (!stateRoot || !/^\d{8}T\d{6}Z-dashboard-[a-f0-9]{12}$/.test(id ?? ''))
    throw new Error('Missing dashboard publication for participation minimums.');
  const db = new DatabaseSync(resolve(stateRoot, 'serving/dashboard/builds', id + '.sqlite'), {readOnly:true});
  try {
    const build = db.prepare('SELECT build_id,corpus_fingerprint,status FROM dashboard_build').get();
    if (build?.build_id !== id || build.corpus_fingerprint !== result.serving.corpusFingerprint || build.status !== 'validated')
      throw new Error('Participation minimums must use the same published dashboard.');
    const scope = result.dateScope;
    const counts = new Map(db.prepare(`WITH selected AS (
        SELECT p.graph_iri,p.player,p.team FROM dashboard_player_game p
        JOIN game_dimension g USING(graph_iri)
        WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?
      ), team_games AS (
        SELECT team,COUNT(DISTINCT graph_iri) AS games FROM selected GROUP BY team
      ) SELECT p.player,MAX(t.games) AS games FROM selected p
        JOIN team_games t USING(team) GROUP BY p.player`)
      .all(scope.gameSet, scope.startDate, scope.endDate).map(row => [row.player, row.games]));
    const qualify = metric => ({...metric,
      ...(metric.playerResults ? {playerResults:metric.playerResults.map(row => {
        const games = counts.get(row.player);
        if (!Number.isSafeInteger(games) || games < 1) throw new Error('Player team schedule is unavailable.');
        // A trade must not lower the threshold. Retain the larger team total
        // and never reduce the player's already evidenced game exposure.
        return {...row, qualificationTeamGames:Math.max(games, row.teamGames)};
      })} : {}),
      ...(metric.byMechanism ? {byMechanism:Object.fromEntries(Object.entries(metric.byMechanism)
        .map(([key, group]) => [key, qualify(group)]))} : {})});
    return {...result,
      ...(result.metrics ? {metrics:result.metrics.map(qualify)} : {metric:qualify(result.metric)})};
  } finally { db.close(); }
}
