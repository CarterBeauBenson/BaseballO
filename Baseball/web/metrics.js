const byId = id => document.getElementById(id);
let catalog, selected, lastResult, activeRequest;
const node = (tag, text) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; return element; };

export function displayFraction(value, places = 2) {
  if (!value) return 'Unavailable';
  const numerator = BigInt(value.numerator), denominator = BigInt(value.denominator);
  if (denominator <= 0n) throw new Error('Invalid fraction');
  const negative = numerator < 0n, magnitude = negative ? -numerator : numerator;
  const scale = 10n ** BigInt(places);
  const rounded = (magnitude * scale * 2n + denominator) / (denominator * 2n);
  return `${negative && rounded ? '-' : ''}${rounded / scale}${places ? '.' + String(rounded % scale).padStart(places, '0') : ''}`;
}

export function resultHeadline(result) {
  if (result.status === 'available') return result.value ? displayFraction(result.value) : result.approximateValue.toFixed(3);
  const count = result.consequences?.length ?? 0;
  return count ? `${count} supported award consequence${count === 1 ? '' : 's'}` : 'Unavailable';
}

export function movementEvidenceLabel(coverage) {
  return `${coverage.withRunnerEpisodeRecordBinding}/${coverage.observedPairs} movements have runner, episode and record bindings`;
}

function renderGameCoverage(games = []) {
  byId('game-coverage').hidden = !games.length;
  const target = byId('game-coverage-table'); target.replaceChildren();
  if (!games.length) return;
  const table = node('table'), head = node('thead'), heading = node('tr'), body = node('tbody');
  for (const label of ['Game', 'Observed PAs', 'Movement evidence', 'Single origin value', 'Award evidence', 'Scored award consequences']) {
    const cell = node('th', label); cell.scope = 'col'; heading.append(cell);
  }
  head.append(heading);
  for (const game of games) {
    const row = node('tr'), movement = game.runnerMovements;
    for (const value of [game.graph.split('/').at(-1), game.observedPlateAppearances,
      movementEvidenceLabel(movement), movement.withOneMetricOriginBinding,
      movement.withCausalRequiredAwardBinding, game.supportedAwardConsequences]) row.append(node('td', String(value)));
    body.append(row);
  }
  table.append(head, body); target.append(table);
}

export function consequencePresentation(metricId) {
  if (metricId === 'offensive-reach') return {
    label: 'Consequence Offensive Reach',
    math: 'Offensive Reach counts distinct trajectories with positive attributed progress. The supported loaded Walk/HBP chain advances the batter and all three existing runners: 1 + 1 + 1 + 1 = 4 trajectories. Each trajectory counts once.',
    places: 0,
  };
  return {
    label: 'Consequence TFS',
    math: 'TFS = progress − destruction − erosion. For this four-runner force chain: HOME → 1B contributes 1/4; 1B → 2B contributes 1/3; 2B → 3B contributes 1/2; 3B → score contributes 1. All four resolve safely or score, so destruction and erosion are zero. Total: 25/12, displayed as 2.08.',
    places: 2,
  };
}

function renderConsequences(results = [], metricId = 'tfs') {
  const presentation = consequencePresentation(metricId);
  const target = byId('award-consequences');
  target.replaceChildren(); target.hidden = !results.length;
  if (!results.length) return;
  target.append(node('h3', 'Supported award consequences'),
    node('p', 'Each score covers a positively supported loaded Walk/HBP force chain. Complete plate-appearance and game scores still require the evidence listed below.'));
  const math = node('details');
  math.append(node('summary', 'Show math'), node('p', presentation.math));
  target.append(math);
  const table = node('table'), head = node('thead'), heading = node('tr'), body = node('tbody');
  for (const label of ['Game / PA source index', 'Batter', presentation.label, 'Evidence']) {
    const cell = node('th', label); cell.scope = 'col'; heading.append(cell);
  }
  head.append(heading);
  for (const result of results) {
    const row = node('tr');
    row.append(node('td', `${result.graph.split('/').at(-1)} / ${result.plateAppearance.split('/').at(-1)}`),
      node('td', result.batter.split('/').at(-1)),
      node('td', `${displayFraction(result.value, presentation.places)} (${result.value.numerator}/${result.value.denominator})`));
    const evidence = node('td'), detail = node('details');
    detail.append(node('summary', 'Trace four advances'));
    const advances = node('ul');
    for (const movement of result.movements) {
      advances.append(node('li', `${movement.runner === result.batter ? 'Batter' : 'Runner'} ${movement.runner.split('/').at(-1)}: ${movement.metricOrigin === '0' ? 'HOME' : movement.originCode} → ${movement.hasRunType === 'true' ? 'score' : movement.destinationCode}`));
    }
    detail.append(advances, node('pre', JSON.stringify({
      award: result.award, components: result.components, movements: result.movements,
    }, null, 2)));
    evidence.append(detail); row.append(evidence); body.append(row);
  }
  table.append(head, body); target.append(table);
}

function facts(target, entries) {
  target.replaceChildren(...entries.map(([label, value]) => { const item = node('div'); item.append(node('dt', label), node('dd', String(value))); return item; }));
}

function gapDetails(gap, affected = false) {
  const detail = node('details');
  detail.append(node('summary', gap.title), node('p', gap.question), node('p', gap.direction));
  const id = node('p', gap.id); id.className = 'gap-id'; detail.append(id);
  if (affected) detail.append(node('p', 'Used by: ' + catalog.metrics.filter(m => m.requires.includes(gap.id)).map(m => m.label).join(', ')));
  return detail;
}

function renderRequirements(ids) {
  const registered = new Map(catalog.gapRegister.gaps.map(g => [g.id, g]));
  byId('metric-gaps').replaceChildren(...(ids.length ? ids.map(id => registered.has(id) ? gapDetails(registered.get(id)) : node('p', id.replaceAll('_', ' '))) :
    [node('p', 'This calculation uses explicitly resolved mapped replay reviews. The result reports that population and any reviews lacking a supported disposition.')]));
}

function choose(metric) {
  activeRequest?.abort(); activeRequest = null;
  selected = metric; lastResult = null;
  byId('metric-title').textContent = metric.label;
  byId('metric-version').textContent = `Version ${metric.version} · ${metric.id}`;
  byId('metric-definition').textContent = metric.userDefinition;
  facts(byId('metric-facts'), [['Grain', metric.grain.replaceAll('_', ' ')], ['Unit', metric.unit], ['Interpretation', metric.higherIs], ['Reference population', metric.referencePopulation]]);
  byId('result').hidden = true;
  byId('request-status').textContent = metric.liveAdapter === 'loaded-award-consequences' ?
    'Inspect supported loaded Walk/HBP consequences and the remaining metric requirements.' :
    metric.requires.length ? 'Calculation implemented. Live values await the requirements below.' : 'Inspect the selected mapped review population.';
  byId('run-metric').disabled = false;
  renderRequirements(metric.requires);
  document.querySelectorAll('#metric-list button').forEach(button => button.setAttribute('aria-current', String(button.dataset.id === metric.id)));
  history.replaceState(null, '', '#' + metric.id);
}

function renderList() {
  const term = byId('metric-search').value.trim().toLowerCase();
  byId('metric-list').replaceChildren(...catalog.metrics.filter(m => (m.label + ' ' + m.id).toLowerCase().includes(term)).map(metric => {
    const button = node('button', metric.label); button.type = 'button'; button.dataset.id = metric.id;
    button.setAttribute('aria-current', String(selected?.id === metric.id));
    button.append(node('small', metric.liveAdapter === 'loaded-award-consequences' ? 'Supported award consequences' :
      metric.requires.length ? 'Awaiting shared requirements' : 'Resolved review evidence'));
    button.addEventListener('click', () => choose(metric)); return button;
  }));
}

function download(name, payload) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  const link = node('a'); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function inspect(event) {
  event.preventDefault();
  activeRequest?.abort(); const controller = new AbortController(); activeRequest = controller;
  byId('run-metric').disabled = true; byId('result').hidden = true; lastResult = null;
  byId('request-status').textContent = 'Reading metric evidence…';
  const dateScope = { preset: byId('date-preset').value };
  if (dateScope.preset === 'custom') { dateScope.startDate = byId('start-date').value; dateScope.endDate = byId('end-date').value; }
  try {
    const response = await fetch('/api/metrics/query', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metricId: selected.id, gameSet: byId('game-set').value, dateScope }), signal: controller.signal });
    const payload = await response.json(); if (!response.ok) throw new Error(payload.error ?? 'Metric request failed.');
    if (activeRequest !== controller) return;
    lastResult = payload;
    const result = payload.metric;
    byId('score-value').textContent = resultHeadline(result);
    byId('score-exact').textContent = result.value ? `Exact: ${result.value.numerator}/${result.value.denominator}` : '';
    byId('result-scope').textContent = result.scope ?? 'Selected evidence population';
    const coverage = result.coverage ?? {};
    const movement = coverage.runnerMovements;
    renderGameCoverage(coverage.byGame);
    renderConsequences(result.consequences, result.metricId);
    facts(byId('coverage'), [['Games', coverage.games ?? payload.graphCount ?? 0], ['Evidence rows', coverage.evidenceRows ?? 0],
      ...(coverage.supportedAwardConsequences !== undefined ? [
        ['Supported award consequences', coverage.supportedAwardConsequences],
        ['Other observed PAs', coverage.observedPAsWithoutSupportedAwardConsequence],
        ['Selected games with no evidence rows', coverage.selectedGraphsWithoutEvidence]] : []),
      ...(coverage.resolvedReviews !== undefined ? [['Resolved reviews', coverage.resolvedReviews], ['Unresolved reviews', coverage.unresolvedReviews]] : []),
      ...(movement ? [['Runner movements observed', movement.observedPairs],
        ['Movements with one origin value', movement.withOneMetricOriginBinding],
        ['Movements missing origin evidence', movement.withoutMetricOriginBinding],
        ['Movements with conflicting origin values', movement.withMultipleMetricOriginBindings]] : [])]);
    byId('result-evidence').textContent = JSON.stringify({ coverage, components: result.components ?? {}, evidence: result.evidence ?? [],
      implementation: payload.implementationSha256, corpus: payload.corpusFingerprint ?? payload.serving?.corpusFingerprint,
      dateScope: payload.dateScope, execution: payload.execution }, null, 2);
    renderRequirements(result.gaps ?? []);
    byId('result').hidden = false;
    byId('request-status').textContent = result.consequences?.length ?
      'Supported award-consequence scores are ready. Broader metric requirements remain listed below.' :
      result.status === 'available' ? 'Result ready for the stated population.' : 'No valid score can be produced from the current evidence. The unresolved requirements are listed below.';
  } catch (error) {
    if (error.name !== 'AbortError') byId('request-status').textContent = error.message;
  } finally {
    if (activeRequest === controller) { byId('run-metric').disabled = false; activeRequest = null; }
  }
}

async function start() {
  try {
    const response = await fetch('/api/metrics/catalog');
    if (!response.ok) throw new Error('The metric catalog could not be loaded.');
    catalog = await response.json();
    renderList(); choose(catalog.metrics.find(m => '#' + m.id === location.hash) ?? catalog.metrics[0]);
    byId('all-gaps').replaceChildren(...catalog.gapRegister.gaps.map(g => gapDetails(g, true)));
    byId('download-gaps').disabled = false;
    byId('download-gaps').addEventListener('click', () => download('baseballo-metric-gaps.json', catalog.gapRegister));
    byId('download-result').addEventListener('click', () => { if (lastResult) download(selected.id + '-result.json', lastResult); });
    byId('metric-search').addEventListener('input', renderList);
    byId('metric-form').addEventListener('submit', inspect);
    byId('date-preset').addEventListener('change', () => {
      const custom = byId('date-preset').value === 'custom';
      document.querySelectorAll('.custom-date').forEach(label => { label.hidden = !custom; label.querySelector('input').required = custom; });
    });
  } catch (error) { byId('metric-title').textContent = 'Metrics unavailable'; byId('request-status').textContent = error.message; }
}

if (typeof document !== 'undefined') start();
