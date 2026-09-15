import assert from 'node:assert/strict';
import {test} from 'node:test';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {playerChannelSummary, playerLeaderboard, playerSummaryValue} from '../query-builder/metric-suite-query-builder.js';
import {metricRanking, rankingScore} from '../metrics.js';
import {createBaseballServer} from '../server.mjs';

const metric = {id:'contribution-path-diversity', higherIs:'better', unit:'normalized entropy'};
const scope = {startDate:'2026-09-01', endDate:'2026-09-07', gameSet:'regular_season'};
function row(id, extras = {}) {
  return {player:`https://baseballontology.org/data/player/${id}`, playerLabel:`Player ${id}`,
    metricId:metric.id, status:'available', dateScope:scope, completeParticipation:true,
    teamGames:7, plateAppearances:0, independentRunningEpisodes:3,
    aggregate:{kind:'channel_entropy', channelCounts:[0, 0, 1]}, ...extras};
}
function board(rows, extras = {}) {
  return playerLeaderboard({playerPopulationComplete:true, playerResults:rows, ...extras}, metric, scope);
}

test('either participation minimum qualifies, including zero-PA runners', () => {
  const result = board([row(1), row(2, {plateAppearances:22, independentRunningEpisodes:0,
    aggregate:{kind:'channel_entropy', channelCounts:[2, 1, 0]}}),
  row(3, {plateAppearances:22}), row(4, {plateAppearances:21, independentRunningEpisodes:2})]);
  assert.equal(result.status, 'available');
  assert.equal(result.belowMinimum, 1);
  const byId = Object.fromEntries(result.rows.map(r => [r.player.split('/').at(-1), r]));
  assert.deepEqual(byId[1].qualifiedThrough, ['running']);
  assert.deepEqual(byId[2].qualifiedThrough, ['batting']);
  assert.deepEqual(byId[3].qualifiedThrough, ['batting', 'running']);
  assert.match(byId[1].qualificationLabel, /3 running episodes/);
  assert.doesNotMatch(byId[1].qualificationLabel, /minimum 22 PA/);
  assert.match(result.qualification.rule, /either/);
});

test('channel counts do not substitute for eligible running episodes', () => {
  assert.equal(board([row(1, {independentRunningEpisodes:2,
    aggregate:{kind:'channel_entropy', channelCounts:[100, 100, 100]}})]).status, 'empty');
  const result = board([row(1)]);
  assert.equal(result.rows[0].observationCount, 1);
  assert.equal(result.rows[0].independentRunningEpisodes, 3);
  assert.equal(result.rows[0].minimumObservations, 3);
  assert.equal(result.rows[0].observationUnit, 'positive channel occurrences');
  assert.equal(result.rows[0].minimumObservationUnit, 'running episodes');
});

test('season exposure changes each branch without relaxing thresholds', () => {
  const rows = [row(1, {teamGames:162, independentRunningEpisodes:16}),
    row(2, {teamGames:162, independentRunningEpisodes:17}),
    row(3, {teamGames:162, plateAppearances:501, independentRunningEpisodes:0}),
    row(4, {teamGames:162, plateAppearances:502, independentRunningEpisodes:0})];
  const result = board(rows);
  assert.equal(result.rows.length, 2);
  assert.ok(result.rows.every(r => r.minimumPA === 502 && r.minimumObservations === 17));
});

test('unknown participation or score coverage cannot silently lower qualification', () => {
  for (const extras of [{independentRunningEpisodes:undefined}, {independentRunningEpisodes:-1},
    {independentRunningEpisodes:1.5}, {plateAppearances:undefined}, {teamGames:0},
    {completeParticipation:false}, {dateScope:{...scope, endDate:'2026-09-06'}}])
    assert.equal(board([row(1, extras)]).status, 'unavailable');
  assert.equal(board([row(1)], {playerPopulationComplete:false}).status, 'unavailable');
  assert.equal(board([row(1), row(1)]).status, 'unavailable');
});

test('the pooled entropy formula retains exact counts and does not average daily scores', () => {
  assert.equal(playerChannelSummary({kind:'channel_entropy', channelCounts:[3,3,3]}).approximateValue, 1);
  assert.equal(playerChannelSummary({kind:'channel_entropy', channelCounts:[0,0,9]}).approximateValue, 0);
  // Two days with one distinct channel each have daily entropy zero. Pooling
  // them gives a nonzero period-wide entropy under the settled formula.
  assert.ok(playerChannelSummary({kind:'channel_entropy', channelCounts:[1,1,0]}).approximateValue > 0.63);
  assert.equal(playerSummaryValue({kind:'mean', count:2, sum:{numerator:'0', denominator:'1'}}, metric.id), null);
  for (const channelCounts of [[0,0,0], [1,2], [1,2,3,4], [-1,2,3], [1.5,2,3], [Number.MAX_SAFE_INTEGER,1,0]])
    assert.equal(playerChannelSummary({kind:'channel_entropy', channelCounts}), null);
});

test('entropy ordering uses unrounded scores and preserves symmetric ties', () => {
  const result = board([[1,1,1], [4,0,0], [1,2,3], [3,1,2], [10,20,30]].map((channelCounts, i) =>
    row(i + 1, {aggregate:{kind:'channel_entropy', channelCounts}})));
  assert.deepEqual(result.rows.map(r => r.rank), [1,2,2,2,5]);
  assert.equal(result.rows[0].playerLabel, undefined);
  assert.equal(result.rows[0].name, 'Player 1');
  const close = board([[1000,1000,1001], [1000,1000,1000]].map((channelCounts, i) =>
    row(i + 1, {aggregate:{kind:'channel_entropy', channelCounts}})));
  assert.equal(close.rows[0].name, 'Player 2');
  assert.equal(rankingScore(close.rows[0], metric.unit).text, rankingScore(close.rows[1], metric.unit).text);
  assert.deepEqual(close.rows.map(r => r.rank), [1,2]);
});

test('cards and expanded rows can display logarithmic scores without a fake exact fraction', () => {
  const leaderboard = board([row(1)]);
  const [ranked] = metricRanking({metric:{leaderboard}}, metric).rows;
  assert.equal(ranked.value, null);
  const display = rankingScore(ranked, metric.unit);
  assert.equal(display.text, '≈ 0.000');
  assert.equal(display.evidence, '0 / 0 / 1');
  assert.match(display.title, /ordering are approximate/);
  assert.match(ranked.context, /running episodes/);
  assert.equal(rankingScore({value:{numerator:'1', denominator:'3'}}, 'score').evidence, '1/3');
});

test('presentation agrees with the canonical Python/SPARQL entropy kernel', () => {
  const source = `import importlib.util,json
from pathlib import Path
p=Path('Baseball/serving/metric_suite.py')
s=importlib.util.spec_from_file_location('m',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
rows=[dict(key='player',play=str(i),channel=c) for c,n in [('batter_self',2),('batter_other',3),('runner_self',4)] for i in range(n)]
print(json.dumps(m.calculate('contribution-path-diversity',rows)))`;
  const result = spawnSync('python', ['-c', source], {cwd:fileURLToPath(new URL('../../../', import.meta.url)), encoding:'utf8'});
  assert.equal(result.status, 0, result.stderr);
  const canonical = JSON.parse(result.stdout);
  const display = playerChannelSummary({kind:'channel_entropy', channelCounts:canonical.components.channelCounts});
  assert.ok(Math.abs(canonical.approximateValue - display.approximateValue) < 1e-14);
  assert.deepEqual(display.channelCounts, [2,3,4]);
});

test('the dashboard endpoint delivers both qualification routes from trusted serving results', async () => {
  const server = createBaseballServer({servingExecutor:async () => ({execution:'materialized-sql', dateScope:scope,
    metrics:[{metricId:metric.id, playerPopulationComplete:true, playerResults:[row(1),
      row(2, {plateAppearances:22, independentRunningEpisodes:0, aggregate:{kind:'channel_entropy', channelCounts:[2,1,0]}})]}]})});
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${server.address().port}/api/metrics/dashboard`;
    const response = await fetch(url, {method:'POST', body:JSON.stringify({dateScope:{preset:'seven_days'}})});
    const payload = await response.json();
    assert.equal(response.status, 200);
    assert.deepEqual(payload.metrics[0].leaderboard.rows.map(r => r.qualifiedThrough), [['batting'], ['running']]);
    assert.equal(payload.metrics[0].leaderboard.rows[0].value, null);
    assert.ok(payload.metrics[0].leaderboard.rows[0].approximateValue > 0);
    const injected = await fetch(url, {method:'POST', body:JSON.stringify({independentRunningEpisodes:1000})});
    assert.equal(injected.status, 400);
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});
