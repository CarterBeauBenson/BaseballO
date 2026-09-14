import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createBaseballServer } from '../server.mjs';
import { metricCatalog, validateMetricRequest, compileMetricEvidenceQuery, metricDisplayTargets, compileMetricDisplayQuery, normalizeMetricDisplayLabels } from '../query-builder/metric-suite-query-builder.js';
import { displayFraction, resultHeadline, movementEvidenceLabel, consequencePresentation, formatMetricValue, resultPresentation, resultDateLabel, selectionFromUrl, displayPlayer, exampleAnswer } from '../metrics.js';

async function withServer(options, work) {
  const server = createBaseballServer(options);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { await work(`http://127.0.0.1:${server.address().port}`); }
  finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
}

test('all twenty metrics expose definitions and resolvable shared gaps', async () => {
  const catalog = await metricCatalog();
  assert.equal(catalog.metrics.length, 20);
  const ids = new Set(catalog.gapRegister.gaps.map(g => g.id));
  for (const metric of catalog.metrics) {
    assert.ok(metric.userDefinition); assert.ok(metric.version);
    assert.ok(metric.requires.every(id => ids.has(id)));
  }
});

test('worked examples cover every metric and match independently specified kernel answers', async () => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const result = spawnSync(process.env.BASEBALLO_PYTHON ?? 'python', [root + '/scripts/generate_metric_examples.py', '--check'], {
    encoding: 'utf8', timeout: 30000, windowsHide: true,
  });
  assert.equal(result.status, 0, result.stderr || result.stdout || result.error?.message);
  const examples = JSON.parse(await readFile(new URL('../metric-examples.json', import.meta.url), 'utf8'));
  const catalog = await metricCatalog();
  assert.deepEqual(Object.keys(examples.metrics).sort(), catalog.metrics.map(m => m.id).sort());
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
    const catalog = await (await fetch(url + '/api/metrics/catalog')).json(); assert.equal(catalog.metrics.length, 20);
    let response = await fetch(url + '/api/metrics/query', { method: 'POST', body: JSON.stringify({ metricId: 'tfs' }) });
    assert.equal(response.status, 200); assert.deepEqual(await response.json(), result);
    response = await fetch(url + '/api/metrics/query', { method: 'POST', body: JSON.stringify({ metricId: 'tfs', bindings: [] }) });
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
