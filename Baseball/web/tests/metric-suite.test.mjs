import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createBaseballServer } from '../server.mjs';
import { metricCatalog, validateMetricRequest, validateDashboardRequest, compileMetricEvidenceQuery, metricDisplayTargets, compileMetricDisplayQuery, normalizeMetricDisplayLabels, automaticMinimumPA, playerLeaderboard, playerSummaryValue, publicMetricResult } from '../query-builder/metric-suite-query-builder.js';
import { displayFraction, resultHeadline, movementEvidenceLabel, consequencePresentation, formatMetricValue, resultPresentation, resultDateLabel, selectionFromUrl, displayPlayer, exampleAnswer, dashboardSummary, matchesMetric, metricRanking, dashboardLoadStatus, unresolvedRunRows } from '../metrics.js';

test('unresolved runs keep their identities and explain the actual evidence problem', () => {
  const evidence = { graph: 'https://w3id.org/baseball/graph/game/566279',
    run: 'https://baseballontology.org/data/game/566279/runner-resolution/23/0',
    status: 'unavailable', value: null, gaps: ['CONFLICTING_SEGMENT_STATE'] };
  const [row] = unresolvedRunRows([evidence]);
  assert.equal(row.game, '566279'); assert.equal(row.run, '23/0');
  assert.match(row.reason, /conflicting base states/);
  assert.deepEqual(row.evidence, evidence);
  assert.match(unresolvedRunRows([{ ...evidence, gaps: ['MISSING_PERSONAL_SCORING_HISTORY'] }])[0].reason, /complete history/);
  assert.match(unresolvedRunRows([{ ...evidence, gaps: ['NEW_GAP'] }])[0].reason, /Additional history evidence/);
  assert.deepEqual(unresolvedRunRows(), []);
});

test('loaded game evidence does not report that player leaderboards are ready', () => {
  const missing = { graphCount: 14, metrics: [{status:'available',value:{numerator:'1',denominator:'2'}}] };
  assert.match(dashboardLoadStatus(missing), /no player leaderboards are available/);
  assert.match(dashboardLoadStatus(missing), /Refreshing will not create those scores/);
  assert.match(dashboardLoadStatus({ graphCount: 0, metrics: [] }), /No games/);
  assert.match(dashboardLoadStatus({ graphCount: 14, metrics: [{leaderboard:{status:'available',rows:[{player:'1'}]}}] }), /^1 player leaderboard loaded/);
  assert.match(dashboardLoadStatus({ graphCount: 14, metrics: [{leaderboard:{status:'available',rows:[]}}] }), /no player leaderboards/);
});

const leaderboardScope = { startDate: '2026-09-01', endDate: '2026-09-07', gameSet: 'regular_season' };
const leaderboardMetric = { id: 'tfs', higherIs: 'better' };
function playerScore(id, numerator, extras = {}) {
  const row = { player: `https://baseballontology.org/data/player/${id}`, playerLabel: `Player ${id}`,
    metricId: 'tfs', status: 'available', dateScope: leaderboardScope, completeParticipation: true,
    plateAppearances: 25, teamGames: 7, value: { numerator: String(numerator), denominator: '1' }, ...extras };
  if (!('aggregate' in extras)) row.aggregate={kind:'mean',count:25,
    sum:{numerator:String(BigInt(row.value.numerator)*25n),denominator:row.value.denominator}};
  return row;
}

test('selected-range means use exact sums and counts, never a supplied total or mean of daily means', () => {
  assert.deepEqual(playerSummaryValue({kind:'mean',sum:{numerator:'7',denominator:'3'},count:2},'tfs'),
    {numerator:'7',denominator:'6'});
  assert.deepEqual(playerSummaryValue({kind:'mean',sum:{numerator:'0',denominator:'3'},count:2},'tfs'),
    {numerator:'0',denominator:'1'});
  const row=playerScore(1,999,{aggregate:{kind:'mean',sum:{numerator:'25',denominator:'12'},count:25}});
  assert.deepEqual(playerLeaderboard({playerPopulationComplete:true,playerResults:[row]},leaderboardMetric,leaderboardScope).rows[0].value,
    {numerator:'1',denominator:'12'});
  for (const aggregate of [undefined,{kind:'total',count:25},{kind:'mean',count:0,sum:{numerator:'1',denominator:'1'}}])
    assert.equal(playerSummaryValue(aggregate,'tfs'),null);
});

test('Empty Games uses the retained count rather than the reduced rate numerator', () => {
  const metric={id:'empty-game-rate',higherIs:'worse',unit:'games'};
  const row=playerScore(1,1,{metricId:metric.id,aggregate:{kind:'count',count:4,eligibleGames:6}});
  const board=playerLeaderboard({playerPopulationComplete:true,playerResults:[row]},metric,leaderboardScope);
  assert.deepEqual(board.rows[0].value,{numerator:'4',denominator:'1'});
  assert.equal(board.summaryKind,'count'); assert.equal(board.unit,'games');
  const raw={metricId:metric.id,status:'available',value:{numerator:'1',denominator:'2'},components:{emptyGames:4,eligibleGames:8}};
  assert.deepEqual(publicMetricResult(raw).value,{numerator:'4',denominator:'1'});
  assert.equal(exampleAnswer({status:'available',value:{numerator:'1',denominator:'1'}},'games'),'Example result: 1 game. Exact: 1/1.');
  assert.deepEqual(raw.value,{numerator:'1',denominator:'2'});
  assert.equal(publicMetricResult({...raw,components:{}}).status,'unavailable');
  assert.equal(playerSummaryValue({kind:'count',count:5,eligibleGames:4},metric.id),null);
});

test('automatic PA minimum follows the approved rule across selected team-game counts', () => {
  assert.deepEqual([1, 5, 7, 30, 162].map(automaticMinimumPA), [3, 16, 22, 93, 502]);
  for (const games of [0, -1, 1.5, NaN]) assert.throws(() => automaticMinimumPA(games));
});

test('player rankings exclude a one-PA high score and adapt to each team exposure', () => {
  const result = { playerPopulationComplete: true, playerResults: [
    playerScore(1, 999, { plateAppearances: 1 }), playerScore(2, 3),
    playerScore(3, 4, { teamGames: 5, plateAppearances: 16 }), playerScore(4, 5, { plateAppearances: 21 }),
  ] };
  const board = playerLeaderboard(result, leaderboardMetric, leaderboardScope);
  assert.deepEqual(board.rows.map(row => [row.name, row.minimumPA]), [['Player 3', 16], ['Player 2', 22]]);
  assert.equal(board.belowMinimum, 2);
  const day = playerLeaderboard({ ...result, playerResults: [playerScore(1, 999, { plateAppearances: 1, teamGames: 1 })] }, leaderboardMetric, leaderboardScope);
  assert.equal(day.status, 'empty');
});

test('player rankings sort exact scores, share tie ranks, and preserve all detail rows', () => {
  const result = { playerPopulationComplete: true, playerResults: [
    playerScore(1, '9007199254740992'), playerScore(2, '9007199254740993'),
    playerScore(3, '18014398509481986', { value: { numerator: '18014398509481986', denominator: '2' } }),
    ...[4, 5, 6, 7, 8].map(id => playerScore(id, 10 - id)),
  ] };
  const board = playerLeaderboard(result, leaderboardMetric, leaderboardScope);
  assert.deepEqual(board.rows.slice(0, 3).map(row => row.rank), [1, 1, 3]);
  assert.equal(board.rows[0].name, 'Player 2');
  const displayed = metricRanking({ metric: { ...result, leaderboard: board } }, leaderboardMetric);
  assert.equal(displayed.rows.length, 8);
  assert.equal(displayed.rows[0].context, '25 PA · minimum 22 PA');
  const worse = playerLeaderboard(result, { ...leaderboardMetric, higherIs: 'worse' }, leaderboardScope);
  assert.equal(worse.rows[0].name, 'Player 8');
});

test('incomplete scores, mismatched dates, duplicate players and partial plays cannot become leaders', () => {
  for (const result of [
    { status: 'available', value: { numerator: '99', denominator: '1' } },
    { consequences: [playerScore(1, 99)], runs: [playerScore(1, 99)] },
    { playerPopulationComplete: false, playerResults: [playerScore(1, 99)] },
    { playerPopulationComplete: true, playerResults: [playerScore(1, 99, { completeParticipation: false })] },
    { playerPopulationComplete: true, playerResults: [playerScore(1, 99, { dateScope: { ...leaderboardScope, startDate: '2025-09-01' } })] },
    { playerPopulationComplete: true, playerResults: [playerScore(1, 99), playerScore(1, 99)] },
  ]) {
    const board = playerLeaderboard(result, leaderboardMetric, leaderboardScope);
    assert.equal(board.status, 'unavailable'); assert.deepEqual(board.rows, []);
  }
});

test('non-batting leaderboards do not silently apply a PA minimum', () => {
  const board = playerLeaderboard({ playerPopulationComplete: true, playerResults: [playerScore(1, 99)] },
    { id: 'defender-breadth', higherIs: 'descriptive' }, leaderboardScope);
  assert.equal(board.qualification.kind, 'role_participation');
  assert.equal(board.qualification.status, 'pending'); assert.deepEqual(board.rows, []);
});

test('dashboard applies qualification server-side to trusted player aggregates', async () => {
  await withServer({ servingExecutor: async () => ({ execution: 'materialized-sql', dateScope: leaderboardScope,
    metrics: [{ metricId: 'tfs', playerPopulationComplete: true, playerResults: [
      playerScore(1, 999, { plateAppearances: 1 }), playerScore(2, 3),
    ] }] }) }, async url => {
    const response = await fetch(url + '/api/metrics/dashboard', { method: 'POST', body: JSON.stringify({ dateScope: { preset: 'one_day' } }) });
    const body = await response.json(); assert.equal(response.status, 200);
    assert.deepEqual(body.metrics[0].leaderboard.rows.map(row => row.name), ['Player 2']);
    const injected = await fetch(url + '/api/metrics/dashboard', { method: 'POST', body: JSON.stringify({ playerResults: [playerScore(1, 999)] }) });
    assert.equal(injected.status, 400);
  });
});

async function withServer(options, work) {
  const server = createBaseballServer(options);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { await work(`http://127.0.0.1:${server.address().port}`); }
  finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
}

test('nineteen public metrics expose definitions while role breadth stays in the backend', async () => {
  const catalog = await metricCatalog();
  assert.equal(catalog.metrics.length, 19);
  assert.ok(!catalog.metrics.some(metric => metric.id === 'role-realization-breadth'));
  assert.throws(() => validateMetricRequest({metricId:'role-realization-breadth'}, catalog), /Unknown metric/);
  const backend = JSON.parse(await readFile(new URL('../../sparql/metrics/metric-catalog.json', import.meta.url), 'utf8'));
  assert.equal(backend.metrics.length,20);
  assert.ok(backend.metrics.some(metric => metric.id === 'role-realization-breadth'));
  const ids = new Set(catalog.gapRegister.gaps.map(g => g.id));
  for (const metric of catalog.metrics) {
    assert.ok(metric.userDefinition); assert.ok(metric.version);
    assert.ok(metric.requires.every(id => ids.has(id)));
  }
});

test('public presentation entries preserve the settled calculation contracts and old names', async () => {
  const source = JSON.parse(await readFile(new URL('../../sparql/metrics/metric-catalog.json', import.meta.url), 'utf8'));
  const display = await metricCatalog();
  assert.equal(display.groups.length, 6);
  for (const metric of display.metrics) {
    const original = source.metrics.find(m => m.id === metric.id);
    const {label,userDefinition,technicalLabel,technicalDefinition,technicalUnit,unit,presentation,...contract}=metric;
    const {label:oldLabel,userDefinition:oldDefinition,unit:oldUnit,...expected}=original;
    assert.deepEqual(contract,expected,'Presentation altered the calculation contract: '+metric.id);
    assert.equal(technicalLabel,oldLabel); assert.equal(technicalDefinition,oldDefinition);
    assert.equal(technicalUnit,oldUnit);
    assert.equal(unit,metric.id==='empty-game-rate'?'games':oldUnit);
    for (const key of ['label','question','summary','reading','unitLabel','scopeLabel','reference']) assert.ok(presentation[key]);
    assert.ok(display.groups.some(group=>group.id===presentation.group));
    assert.ok(matchesMetric(metric,oldLabel)); assert.ok(matchesMetric(metric,metric.id));
    assert.ok(matchesMetric(metric,label,presentation.group));
    assert.equal(matchesMetric(metric,label,'unknown'),false);
  }
  assert.equal(display.metrics.find(m=>m.id==='tfs').label,'Plate Appearance Contribution');
  assert.equal(display.metrics.find(m=>m.id==='adjudication-volatility').label,'Replay Overturn Rate');
});

test('worked examples cover every metric and match independently specified kernel answers', async () => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const result = spawnSync(process.env.BASEBALLO_PYTHON ?? 'python', [root + '/scripts/generate_metric_examples.py', '--check'], {
    encoding: 'utf8', timeout: 30000, windowsHide: true,
  });
  assert.equal(result.status, 0, result.stderr || result.stdout || result.error?.message);
  const examples = JSON.parse(await readFile(new URL('../metric-examples.json', import.meta.url), 'utf8'));
  const catalog = await metricCatalog();
  assert.ok(catalog.metrics.every(metric => examples.metrics[metric.id]));
  assert.equal(Object.keys(examples.metrics).length,20,'Backend examples retain every calculation');
  for (const metric of catalog.metrics) for (const item of examples.metrics[metric.id].cases) {
    assert.ok(item.explanation && item.equation);
    assert.match(exampleAnswer(item.result, metric.unit), /^Example result:/);
  }
  assert.equal(exampleAnswer(examples.metrics['hidden-help-rate'].cases[0].result, 'proportion'),
    'Example result: 50.0%. Exact: 1/2.');
  assert.match(exampleAnswer(examples.metrics['paq-2'].cases[1].result, 'percentile'), /unavailable/);
  assert.match(exampleAnswer(examples.metrics['contribution-path-diversity'].cases[0].result, 'normalized entropy'), /approximately 1.000/);
});

test('illustrations are served as a separate static artifact, without reading game evidence', async () => {
  await withServer({ fetchImpl: async () => { throw Error('Static examples must not query RDF'); } }, async base => {
    const response = await fetch(base + '/metric-examples.json');
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /^application\/json/);
    const payload = await response.json();
    assert.equal(payload.artifactType, 'baseballo-illustrative-metric-examples');
    assert.equal(Object.keys(payload.metrics).length,19);
    assert.equal(payload.metrics['role-realization-breadth'],undefined);
    assert.deepEqual(payload.metrics['empty-game-rate'].cases[0].result.value,{numerator:'1',denominator:'1'});
    assert.doesNotMatch(payload.metrics['empty-game-rate'].formula, /\//);
    assert.match(payload.notice, /not results from the selected games/);
    assert.equal(payload.metrics.tfs.cases[2].result.value.numerator, '-1');
    assert.equal(payload.metrics.tfs.cases[2].result.value.denominator, '4');
  });
});

test('public requests cannot submit graph facts, admission flags or query text', async () => {
  const catalog = await metricCatalog();
  for (const key of ['bindings', 'graphs', 'completePopulation', 'approved', 'query', 'filters']) {
    assert.throws(() => validateMetricRequest({ metricId: 'tfs', [key]: [] }, catalog));
  }
  for (const input of [null, [], { metricId: 'unknown' }, { metricId: 'tfs', gameSet: 'fixture' },
    { metricId: 'tfs', dateScope: { preset: 'custom', startDate: '2026-02-31', endDate: '2026-03-10' } },
    { metricId: 'tfs', dateScope: { preset: 'custom', startDate: '2026-03-10', endDate: '2026-03-01' } }]) {
    assert.throws(() => validateMetricRequest(input, catalog));
  }
  assert.equal(validateMetricRequest({ metricId: 'paq-2' }, catalog).dateScope.preset, 'season_to_date');
});

test('evidence query is restricted to the exact authoritative graph selection', async () => {
  const graph = 'https://w3id.org/baseball/graph/game/101';
  const query = await compileMetricEvidenceQuery([graph]);
  assert.ok(query.includes(`VALUES ?graph { <${graph}> }`));
  const empty = await compileMetricEvidenceQuery([]);
  assert.ok(empty.includes('FILTER(?emptyScope = 1)'));
  assert.ok(!empty.includes('GRAPH ?graph'), 'an empty scope must not scan any named graph');
  await assert.rejects(compileMetricEvidenceQuery([graph + '> } SERVICE <https://example.com> { ?s ?p ?o } #']));
});

test('live fallback and SQL extraction compile identical evidence for every scope', async () => {
  const script = `import json,sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(sys.argv[1])/'serving'))\nimport metric_suite\nprint(json.dumps(metric_suite.evidence_query(json.load(sys.stdin))))`;
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const graph = 'https://w3id.org/baseball/graph/game/101';
  for (const graphs of [[], [graph], [graph, graph, graph.replace('101', '102')]]) {
    const result = spawnSync(process.env.BASEBALLO_PYTHON ?? 'python', ['-c', script, root], {
      input: JSON.stringify(graphs), encoding: 'utf8', timeout: 15000, windowsHide: true,
    });
    assert.equal(result.status, 0, result.stderr || result.error?.message);
    assert.equal(await compileMetricEvidenceQuery(graphs), JSON.parse(result.stdout));
  }
});

test('Python player means feed qualification without reducing missed-game exposure', () => {
  const script = `import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'serving'))
import metric_suite as m
scope=json.load(sys.stdin)
members=[]; scores=[]; people=[]
for p in range(1,7):
    player='https://baseballontology.org/data/player/'+str(p)
    for i in range(3):
        member=dict(graph='https://w3id.org/baseball/graph/game/101',plateAppearance='https://example.org/pa/'+str(p)+'/'+str(i),player=player)
        members.append(member)
        scores.append(dict(member,metricId='offensive-reach',status='available',completePlateAppearance=True,dateScope=scope,value=m.exact(p)))
    exposure=[dict(game='https://example.org/game/'+str(i),team='https://example.org/team/1') for i in range(7 if p==6 else 1)]
    people.append(dict(player=player,dateScope=scope,completeParticipation=True,plateAppearances=3,teamGameExposure=exposure))
print(json.dumps(m.summarize_batting_players('offensive-reach',scores,expected_observations=members,participation=people,date_scope=scope,population_complete=True)))`;
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const result = spawnSync(process.env.BASEBALLO_PYTHON ?? 'python', ['-c', script, root], {
    input: JSON.stringify(leaderboardScope), encoding: 'utf8', timeout: 15000, windowsHide: true,
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  const board = playerLeaderboard(JSON.parse(result.stdout), {id:'offensive-reach',higherIs:'better'}, leaderboardScope);
  assert.equal(board.status, 'available');
  assert.equal(board.rows.length, 5);
  assert.equal(board.belowMinimum, 1); // The largest mean belongs to an unqualified player.
  assert.equal(board.rows[0].player, 'https://baseballontology.org/data/player/5');
  assert.deepEqual(board.rows[0].value, {numerator:'5',denominator:'1'});
});

test('display rounding retains arbitrarily large exact rational arithmetic', () => {
  assert.equal(displayFraction({ numerator: '1', denominator: '3' }), '0.33');
  assert.equal(displayFraction({ numerator: '-5', denominator: '4' }), '-1.25');
  assert.equal(displayFraction({ numerator: '1999', denominator: '2000' }), '1.00');
  assert.equal(displayFraction({ numerator: '100000000000000000000000000000001', denominator: '100000000000000000000000000000000' }), '1.00');
  assert.equal(displayFraction(null), 'Unavailable');
});

test('rate displays scale exact fractions only for percentages, and counts keep their unit', () => {
  const rate = { numerator: '13', denominator: '23' };
  assert.equal(formatMetricValue(rate, 'proportion'), '56.5%');
  assert.deepEqual(rate, { numerator: '13', denominator: '23' });
  assert.equal(formatMetricValue({ numerator: '0', denominator: '1' }, 'proportion'), '0.0%');
  assert.equal(formatMetricValue({ numerator: '4', denominator: '1' }, 'trajectories'), '4');
  assert.equal(formatMetricValue({ numerator: '75', denominator: '1' }, 'percentile'), '75.00');
  assert.equal(resultHeadline({ status: 'available', value: null }), 'Unavailable');
});

test('empty selections, incomplete evidence and partial play results have distinct presentation', () => {
  const metric = { unit: 'trajectory fraction' };
  const payload = { metric: { status: 'unavailable', value: null, coverage: { games: 1 } } };
  assert.equal(resultPresentation(payload, metric).state, 'unavailable');
  payload.metric.consequences = [{ value: { numerator: '25', denominator: '12' } }];
  assert.equal(resultPresentation(payload, metric).state, 'partial');
  assert.equal(resultPresentation(payload, metric).headline, '2.08');
  payload.metric.consequences.push({ value: { numerator:'1',denominator:'4' } });
  assert.equal(resultPresentation(payload, metric).headline, '2 supported award consequences');
  payload.metric.coverage.games = 0;
  assert.equal(resultPresentation(payload, metric).state, 'empty');
  assert.equal(resultDateLabel({ dateScope: { gameSet:'all_star',startDate:'2026-07-16',endDate:'2026-07-16' } }), 'All-Star · 2026-07-16 to 2026-07-16');
});

test('complete individual runs display their own depth without implying full population coverage', () => {
  const metric = { unit: 'episodes' };
  const payload = { metric: { status: 'unavailable', value: null, coverage: { games: 1 },
    runs: [{ value: { numerator: '3', denominator: '1' }, completeTrajectory: true }] } };
  assert.equal(resultPresentation(payload, metric).headline, '3');
  assert.equal(resultPresentation(payload, metric).badge, 'Complete individual run results');
  payload.metric.runs.push({ value: { numerator: '1', denominator: '1' }, completeTrajectory: true });
  assert.equal(resultPresentation(payload, metric).headline, '2 run results');
  assert.equal(resultPresentation(payload, metric).state, 'partial');
});

test('bookmarked selections validate dates and preserve supported scopes', () => {
  assert.deepEqual(selectionFromUrl('http://localhost/metrics?preset=custom&startDate=2026-08-25&endDate=2026-08-25&gameSet=all_star#tfs'),
    { preset:'custom',gameSet:'all_star',startDate:'2026-08-25',endDate:'2026-08-25' });
  for (const dates of ['startDate=2026-02-31&endDate=2026-03-10','startDate=2026-09-01&endDate=2026-08-01','startDate=2026-08-01']) {
    assert.equal(selectionFromUrl('http://localhost/?preset=custom&'+dates).preset, 'one_day');
  }
});

test('display labels are graph-scoped, optional, and never choose a conflicting name', async () => {
  const graph = 'https://w3id.org/baseball/graph/game/823016', player = 'https://baseballontology.org/data/player/687637';
  const targets = metricDisplayTargets([{ graph, batter:player, movements:[{runner:player}] }]);
  assert.equal(targets.length, 1);
  const query = await compileMetricDisplayQuery(targets);
  assert.ok(query.includes(`FROM NAMED <${graph}>`));
  assert.ok(query.includes(`(<${graph}> <${player}>)`));
  assert.equal(await compileMetricDisplayQuery([]), null);
  await assert.rejects(compileMetricDisplayQuery([{ graph:graph+'>',entity:player }]));
  const row = { graph:{type:'uri',value:graph},entity:{type:'uri',value:player},label:{type:'literal',value:'Dylan Beavers'} };
  const labels = normalizeMetricDisplayLabels([row,row],targets);
  assert.equal(displayPlayer(labels,graph,player),'Dylan Beavers');
  assert.equal(displayPlayer(labels,graph+'0',player),'Player #687637');
  assert.deepEqual(normalizeMetricDisplayLabels([row,{...row,label:{type:'literal',value:'Conflicting name'}}],targets),[]);
  assert.deepEqual(normalizeMetricDisplayLabels([{...row,graph:{type:'uri',value:graph+'0'}}],targets),[]);
});

test('optional label lookup failure preserves a successful SQL metric response', async () => {
  const result = { execution:'materialized-sql',metric:{ status:'unavailable',value:null,
    consequences:[{graph:'https://w3id.org/baseball/graph/game/823016',batter:'https://baseballontology.org/data/player/687637',movements:[]}] } };
  await withServer({ servingExecutor:async()=>result,fetchImpl:async()=>{throw new Error('labels offline');} },async url=>{
    const response = await fetch(url+'/api/metrics/query',{method:'POST',body:JSON.stringify({metricId:'tfs'})});
    assert.equal(response.status,200);
    const payload = await response.json();
    assert.deepEqual(payload.metric,result.metric);
    assert.equal(payload.execution,'materialized-sql');
    assert.deepEqual(payload.display,{source:'identifier-fallback',labels:[]});
  });
});

test('runner boundary labels remain optional and do not manufacture a metric score', async () => {
  const graph = 'https://w3id.org/baseball/graph/game/566279', runner = 'https://baseballontology.org/data/player/444482';
  const result = { execution:'materialized-sql', metric:{ metricId:'tfs', status:'unavailable', value:null,
    runnerBoundaryStates:[{graph,runner,basePosition:2,completePlateAppearance:false,populationComplete:false}] } };
  let labelQueries = 0;
  await withServer({ servingExecutor:async()=>result, fetchImpl:async(_url, options)=>{
    assert.ok(options.body.get('query').includes(runner)); labelQueries++;
    return new Response(JSON.stringify({results:{bindings:[{
      graph:{type:'uri',value:graph},entity:{type:'uri',value:runner},label:{type:'literal',value:'Test name'}
    }]}}));
  } }, async url=>{
    const response = await fetch(url+'/api/metrics/query',{method:'POST',body:JSON.stringify({metricId:'tfs'})});
    assert.equal(response.status,200);
    const payload = await response.json();
    assert.equal(labelQueries,1);
    assert.equal(displayPlayer(payload.display.labels,graph,runner),'Test name');
    assert.deepEqual(payload.metric.runnerBoundaryStates,result.metric.runnerBoundaryStates);
    assert.equal(payload.metric.status,'unavailable');
    assert.equal(payload.metric.value,null);
    assert.equal(payload.metric.leaderboard.status,'unavailable');
  });
});

test('consequence results remain visible without presenting a whole-population score', () => {
  assert.equal(resultHeadline({ status: 'unavailable', value: null, consequences: [{ value: { numerator: '25', denominator: '12' } }] }), '1 supported award consequence');
  assert.equal(resultHeadline({ status: 'unavailable', value: null, consequences: [] }), 'Unavailable');
  assert.equal(resultHeadline({ status: 'available', value: { numerator: '1', denominator: '3' } }), '0.33');
});

test('Offensive Reach displays a trajectory count with its own math and unit', () => {
  const reach = consequencePresentation('offensive-reach'), tfs = consequencePresentation('tfs');
  assert.equal(reach.label, 'Consequence Offensive Reach');
  assert.equal(displayFraction({ numerator: '4', denominator: '1' }, reach.places), '4');
  assert.ok(reach.math.includes('positive attributed progress'));
  assert.ok(!reach.math.includes('25/12'));
  assert.equal(displayFraction({ numerator: '25', denominator: '12' }, tfs.places), '2.08');
});

test('movement coverage reports observed bindings without claiming source completeness', () => {
  assert.equal(movementEvidenceLabel({ withRunnerEpisodeRecordBinding: 0, observedPairs: 0 }), '0/0 movements have runner, episode and record bindings');
  assert.equal(movementEvidenceLabel({ withRunnerEpisodeRecordBinding: 4, observedPairs: 4 }), '4/4 movements have runner, episode and record bindings');
  assert.equal(movementEvidenceLabel({ withRunnerEpisodeRecordBinding: 0, observedPairs: 118 }), '0/118 movements have runner, episode and record bindings');
});

test('API returns SQL results and rejects caller supplied evidence before execution', async () => {
  let calls = 0;
  const result = { metric: { metricId: 'tfs', status: 'unavailable', value: null, gaps: ['BOUNDARY_STATE'] }, execution: 'materialized-sql' };
  await withServer({ servingExecutor: async input => { calls++; assert.equal(input.route, 'metric-suite'); return result; } }, async url => {
    const catalog = await (await fetch(url + '/api/metrics/catalog')).json(); assert.equal(catalog.metrics.length, 19);
    let response = await fetch(url + '/api/metrics/query', { method: 'POST', body: JSON.stringify({ metricId: 'tfs' }) });
    assert.equal(response.status, 200);
    const payload = await response.json();
    const { leaderboard, ...scoredMetric } = payload.metric;
    assert.deepEqual({ ...payload, metric: scoredMetric }, result);
    assert.equal(leaderboard.status, 'unavailable');
    assert.deepEqual(leaderboard.gaps, ['COMPLETE_PLAYER_SCORES']);
    response = await fetch(url + '/api/metrics/query', { method: 'POST', body: JSON.stringify({ metricId: 'tfs', bindings: [] }) });
    assert.equal(response.status, 400); assert.equal(calls, 1);
    response = await fetch(url + '/api/metrics/query', { method: 'POST', body: JSON.stringify({ metricId: 'role-realization-breadth' }) });
    assert.equal(response.status, 400); assert.equal(calls, 1);
    for (const path of ['/metrics', '/metrics.js', '/metrics.css']) {
      const page = await fetch(url + path); assert.equal(page.status, 200);
      assert.ok(page.headers.get('content-security-policy').includes("script-src 'self'"));
    }
  });
});

test('stale SQL falls back to authoritative evidence, and SQL-required requests fail clearly', async () => {
  let reduced = 0;
  await withServer({ servingExecutor: async () => { throw new Error('stale'); },
    fetchImpl: async () => new Response(JSON.stringify({ head: { vars: [] }, results: { bindings: [] } }), { status: 200 }),
    metricReducer: async input => { reduced++; assert.deepEqual(input.graphs, []); assert.deepEqual(input.bindings, []);
      return { metric: { status: 'unavailable', value: null, gaps: ['EMPTY_DENOMINATOR'] }, execution: 'authoritative-rdf' }; }
  }, async url => {
    const options = { method: 'POST', body: JSON.stringify({ metricId: 'adjudication-volatility' }) };
    const response = await fetch(url + '/api/metrics/query', options);
    assert.equal(response.status, 200); assert.equal((await response.json()).execution, 'authoritative-rdf');
    const required = await fetch(url + '/api/metrics/query', { ...options, headers: { 'x-baseballo-require-materialized': 'true' } });
    assert.equal(required.status, 503); assert.equal(reduced, 1);
  });
});

test('page includes accessible selectors, evidence downloads and no inline execution', async () => {
  const html = await readFile(new URL('../metrics.html', import.meta.url), 'utf8');
  const script = await readFile(new URL('../metrics.js', import.meta.url), 'utf8');
  for (const id of ['metric-search','metric-list','metric-title','metric-form','result-evidence','download-result','download-gaps','all-gaps']) {
    assert.ok(html.includes(`id="${id}"`));
  }
  assert.ok(html.includes('aria-live="polite"'));
  assert.ok(!/\son\w+=/.test(html)); assert.ok(!script.includes('innerHTML'));
  assert.ok(script.includes('activeRequest !== controller'));
});

test('dashboard only accepts shared dates and game selection', async () => {
  const catalog = await metricCatalog();
  for (const key of ['metricId','view','bindings','graphs','completePopulation','query','filters']) {
    assert.throws(() => validateDashboardRequest({ [key]: 'tfs' }, catalog));
  }
  assert.throws(() => validateDashboardRequest({ dateScope: { preset:'custom',startDate:'2026-09-12',endDate:'2026-09-01' } }, catalog));
  assert.deepEqual(validateDashboardRequest({ dateScope: { preset:'one_day' } }, catalog),
    { route:'metric-suite', view:'dashboard', gameSet:'regular_season', dateScope:{preset:'one_day'} });
});

test('dashboard distinguishes scoped zero, individual results, absent scores and empty selections', () => {
  const metrics = [
    {status:'available',value:{numerator:'0',denominator:'1'}},
    {status:'unavailable',value:null,consequences:[{value:{numerator:'25',denominator:'12'}}]},
    {status:'unavailable',value:null,runs:[{value:{numerator:'3',denominator:'1'}}]},
    {status:'unavailable',value:null},
  ];
  assert.deepEqual(dashboardSummary({graphCount:15,metrics}), {games:15,available:1,partial:2,unavailable:1,empty:0});
  assert.deepEqual(dashboardSummary({graphCount:0,metrics}), {games:0,available:0,partial:0,unavailable:0,empty:4});
});

test('dashboard executes once through SQL and rejects injected facts before execution', async () => {
  let calls=0;
  await withServer({servingExecutor:async input=>{ calls++; assert.equal(input.view,'dashboard'); assert.equal(input.metricId,undefined);
    return {metrics:[],execution:'materialized-sql'}; }}, async url=>{
    const response=await fetch(url+'/api/metrics/dashboard',{method:'POST',body:JSON.stringify({dateScope:{preset:'one_day'}})});
    assert.equal(response.status,200); assert.equal((await response.json()).execution,'materialized-sql');
    const invalid=await fetch(url+'/api/metrics/dashboard',{method:'POST',body:JSON.stringify({bindings:[]})});
    assert.equal(invalid.status,400); assert.equal(calls,1);
  });
});

test('SQL and RDF dashboard responses hide backend roles and retain the input evidence unchanged', async () => {
  const backend = {metrics:[{metricId:'tfs',status:'unavailable',value:null},
    {metricId:'role-realization-breadth',status:'available',value:{numerator:'4',denominator:'1'}}]};
  for (const mode of ['sql','rdf']) {
    await withServer({servingExecutor:async()=>{if(mode==='rdf')throw Error('stale'); return backend;},
      fetchImpl:async()=>new Response(JSON.stringify({results:{bindings:[]}})),
      metricReducer:async()=>backend},async url=>{
      const response=await fetch(url+'/api/metrics/dashboard',{method:'POST',body:'{}'});
      assert.equal(response.status,200);
      assert.deepEqual((await response.json()).metrics.map(metric=>metric.metricId),['tfs']);
      assert.equal(backend.metrics.length,2);
    });
  }
});

test('dashboard fallback reduces one common RDF selection and respects SQL-required requests', async () => {
  let reductions=0;
  await withServer({servingExecutor:async()=>{throw Error('stale');},
    fetchImpl:async()=>new Response(JSON.stringify({head:{vars:[]},results:{bindings:[]}})),
    metricReducer:async input=>{reductions++; assert.equal(input.view,'dashboard'); assert.deepEqual(input.graphs,[]);
      return {metrics:[],execution:'authoritative-rdf'};}
  },async url=>{
    const options={method:'POST',body:JSON.stringify({dateScope:{preset:'one_day'}})};
    const response=await fetch(url+'/api/metrics/dashboard',options);
    assert.equal(response.status,200); assert.equal((await response.json()).execution,'authoritative-rdf');
    const required=await fetch(url+'/api/metrics/dashboard',{...options,headers:{'x-baseballo-require-materialized':'true'}});
    assert.equal(required.status,503); assert.equal(reductions,1);
  });
});
