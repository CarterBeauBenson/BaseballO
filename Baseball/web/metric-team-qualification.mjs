import { DatabaseSync } from 'node:sqlite';
import { resolve } from 'node:path';

// Lightweight qualification over the exact immutable SQL snapshot already
// verified by the serving worker. No graph access or metric recalculation.
export function selectedTeamMinimums(result, stateRoot) {
  if (result.serving?.publication !== 'dashboard') return result;
  const cached = new Map();
  const countsFor = publication => {
    const id = publication?.buildId ?? result.serving.buildId;
    const identity = /^\d{8}T\d{6}Z-dashboard-(?:([a-f0-9]{12})|(offense|defense|combined|other)-[a-f0-9]{8})$/.exec(id ?? '');
    if (!stateRoot || !identity) throw new Error('Missing dashboard publication for participation minimums.');
    const family = identity[2];
    if (family && publication?.family && publication.family !== family)
      throw new Error('Participation minimums must use their own metric family.');
    const corpus = publication?.corpusFingerprint ?? (id === result.serving.buildId ? result.serving.corpusFingerprint : null);
    const key = JSON.stringify([id,corpus]);
    if (cached.has(key)) return cached.get(key);
    const db = new DatabaseSync(resolve(stateRoot, 'serving/dashboard/builds', id + '.sqlite'), {readOnly:true});
    try {
      const build = db.prepare('SELECT build_id,corpus_fingerprint,status FROM dashboard_build').get();
      // Initial split readers supplied the exact verified build ID before they
      // exposed the family corpus hash. Never substitute the offense hash for
      // a retained defensive snapshot. New readers supply both identifiers.
      if (build?.build_id !== id || (corpus && build.corpus_fingerprint !== corpus) || build.status !== 'validated')
        throw new Error('Participation minimums must use the same published dashboard.');
      const table = family && family !== 'offense' ?
        `(SELECT * FROM dashboard_family_player_game WHERE family='${family}')` : 'dashboard_player_game';
      const scope = result.dateScope;
      const counts = new Map(db.prepare(`WITH selected AS (
        SELECT p.graph_iri,p.player,p.team FROM ${table} p
        JOIN game_dimension g USING(graph_iri)
        WHERE g.game_set=? AND g.official_date BETWEEN ? AND ?
      ), team_games AS (
        SELECT team,COUNT(DISTINCT graph_iri) AS games FROM selected GROUP BY team
      ) SELECT p.player,MAX(t.games) AS games FROM selected p
        JOIN team_games t USING(team) GROUP BY p.player`)
        .all(scope.gameSet, scope.startDate, scope.endDate).map(row => [row.player, row.games]));
      cached.set(key,counts);return counts;
    } finally { db.close(); }
  };
  const qualify = (metric, inherited) => {
    // Empty Games is a count. Its admitted eligibility is already in SQL and
    // must not acquire a participation minimum from this rate-only step.
    if (metric.metricId === 'empty-game-rate') return metric;
    const publication = metric.freshness ?? inherited;
    const counts = metric.playerResults?.length ? countsFor(publication) : null;
    return {...metric,
      ...(metric.playerResults ? {playerResults:metric.playerResults.map(row => {
        const games = counts.get(row.player);
        if (!Number.isSafeInteger(games) || games < 1) throw new Error('Player team schedule is unavailable.');
        // A trade must not lower the threshold. Retain the larger team total
        // and never reduce the player's already evidenced game exposure.
        return {...row, qualificationTeamGames:Math.max(games, row.teamGames)};
      })} : {}),
      ...(metric.byMechanism ? {byMechanism:Object.fromEntries(Object.entries(metric.byMechanism)
        .map(([key, group]) => [key, qualify(group,publication)]))} : {})};
  };
  const isolated = metric => {
    try { return qualify(metric); }
    catch (error) {
      if (!result.serving.families) throw error;
      const gap = 'QUALIFICATION_PUBLICATION_UNAVAILABLE';
      return {...metric,status:'unavailable',value:null,playerPopulationComplete:false,playerRecordsComplete:false,
        playerResults:[],byMechanism:{},gaps:[gap],playerSummaryGaps:[gap],
        freshness:{...metric.freshness,status:'unavailable',reason:error.message}};
    }
  };
  return {...result,
    ...(result.metrics ? {metrics:result.metrics.map(isolated)} : {metric:isolated(result.metric)})};
}
