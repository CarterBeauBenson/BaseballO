const byId = id => document.getElementById(id);
let catalog, selected, lastResult, activeRequest, examples;
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

export function formatMetricValue(value, unit) {
  if (!value) return 'Unavailable';
  if (unit === 'proportion') return displayFraction({ numerator: String(BigInt(value.numerator) * 100n), denominator: value.denominator }, 1) + '%';
  const counts = ['trajectories', 'acts', 'players', 'episodes', 'role types'];
  return displayFraction(value, counts.includes(unit) && value.denominator === '1' ? 0 : 2);
}

export function resultHeadline(result, unit) {
  if (result.status === 'available') return result.value ? formatMetricValue(result.value, unit) :
    Number.isFinite(result.approximateValue) ? result.approximateValue.toFixed(3) : 'Unavailable';
  const count = result.consequences?.length ?? 0;
  return count ? `${count} supported award consequence${count === 1 ? '' : 's'}` : 'Unavailable';
}

export function resultPresentation(payload, metric) {
  const result = payload.metric, coverage = result.coverage ?? {};
  if ((coverage.games ?? payload.graphCount) === 0) return { state: 'empty', badge: 'No games selected',
    headline: 'No games in this date range', message: 'Choose dates within the loaded range shown below.' };
  if (result.status === 'available') return { state: 'available', badge: 'Result available',
    headline: resultHeadline(result, metric.unit), message: 'Result ready for the stated evidence population.' };
  if (result.consequences?.length) return { state: 'partial', badge: 'Limited play results',
    headline: result.consequences.length === 1 ? formatMetricValue(result.consequences[0].value, metric.unit) : resultHeadline(result, metric.unit),
    message: `Showing ${result.consequences.length} supported award play${result.consequences.length === 1 ? '' : 's'}.` };
  return { state: 'unavailable', badge: 'Evidence incomplete', headline: 'Not yet calculable',
    message: result.gaps?.includes('EMPTY_DENOMINATOR') ? 'No eligible resolved evidence is available for this calculation in the selection.' :
      'The selected evidence does not support a score yet. The remaining requirements are listed below.' };
}

export function resultDateLabel(payload) {
  const scope = payload.dateScope ?? {};
  const period = scope.startDate && scope.endDate ? `${scope.startDate} to ${scope.endDate}` : 'Dates not reported';
  return `${scope.gameSet === 'all_star' ? 'All-Star' : scope.gameSet === 'regular_season' ? 'Regular season' : 'Selected games'} · ${period}`;
}

export function displayPlayer(labels, graph, player) {
  return labels?.find(row => row.graph === graph && row.entity === player)?.label ?? `Player #${player.split('/').at(-1)}`;
}

export function exampleAnswer(result, unit) {
  if (result.status !== 'available') return 'Example result: unavailable (no defined denominator).';
  if (result.value) return `Example result: ${formatMetricValue(result.value, unit)}${unit === 'proportion' ? '' : ' ' + unit}. Exact: ${result.value.numerator}/${result.value.denominator}.`;
  return `Example result: approximately ${result.approximateValue.toFixed(3)} ${unit}. Logarithmic results are approximate; channel counts remain exact.`;
}

function renderExampleCase() {
  const entry = examples?.metrics[selected.id], item = entry?.cases[Number(byId('example-choice').value)];
  byId('example-formula').textContent = entry?.formula ?? '';
  byId('example-title').textContent = item?.title ?? '';
  byId('example-explanation').textContent = item?.explanation ?? 'Worked examples are unavailable. You can still inspect selected-game evidence below.';
  byId('example-equation').textContent = item?.equation ?? '';
  byId('example-answer').textContent = item ? exampleAnswer(item.result, selected.unit) : '';
}

function renderExamples() {
  const cases = examples?.metrics[selected.id]?.cases ?? [];
  const choice = byId('example-choice');
  choice.replaceChildren(...cases.map((item, index) => {
    const option = node('option', item.title); option.value = String(index); return option;
  }));
  choice.value = '0';
  choice.hidden = byId('example-choice-label').hidden = cases.length < 2;
  renderExampleCase();
}

export function selectionFromUrl(url) {
  const p = new URL(url).searchParams, preset = p.get('preset'), gameSet = p.get('gameSet');
  const validDate = value => /^\d{4}-\d{2}-\d{2}$/.test(value ?? '') && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  const selection = { preset: ['one_day','seven_days','thirty_days','season_to_date'].includes(preset) ? preset : 'one_day',
    gameSet: gameSet === 'all_star' ? gameSet : 'regular_season' };
  if (preset === 'custom' && validDate(p.get('startDate')) && validDate(p.get('endDate')) && p.get('startDate') <= p.get('endDate')) {
    Object.assign(selection, { preset, startDate: p.get('startDate'), endDate: p.get('endDate') });
  }
  return selection;
}

function saveSelection() {
  const url = new URL(location.href); url.search = ''; url.hash = selected.id;
  url.searchParams.set('gameSet', byId('game-set').value);
  url.searchParams.set('preset', byId('date-preset').value);
  if (byId('date-preset').value === 'custom') for (const key of ['start', 'end']) url.searchParams.set(key + 'Date', byId(key + '-date').value);
  history.replaceState(null, '', url);
}

function invalidateSelection() {
  activeRequest?.abort(); activeRequest = null; lastResult = null;
  byId('result').hidden = true; byId('download-result').disabled = true;
  byId('run-metric').disabled = false;
  byId('request-status').textContent = 'Selection changed. Inspect the metric to load matching results.';
  renderRequirements(selected.requires); saveSelection();
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

function renderConsequences(results = [], metricId = 'tfs', labels = []) {
  const presentation = consequencePresentation(metricId);
  const target = byId('award-consequences');
  target.replaceChildren(); target.hidden = !results.length;
  if (!results.length) return;
  target.append(node('h3', 'Supported award consequences'),
    node('p', 'Scores for the batter and forced-runner advances caused by each listed Walk/HBP.'));
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
      node('td', displayPlayer(labels, result.graph, result.batter)),
      node('td', `${displayFraction(result.value, presentation.places)} (${result.value.numerator}/${result.value.denominator})`));
    const evidence = node('td'), detail = node('details');
    detail.append(node('summary', 'Trace four advances'));
    const advances = node('ul');
    for (const movement of result.movements) {
      advances.append(node('li', `${displayPlayer(labels, result.graph, movement.runner)}${movement.runner === result.batter ? ' (batter)' : ''}: ${movement.metricOrigin === '0' ? 'HOME' : movement.originCode} → ${movement.hasRunType === 'true' ? 'score' : movement.destinationCode}`));
    }
    const records = node('details'); records.append(node('summary', 'Technical evidence'), node('pre', JSON.stringify({
      award: result.award, components: result.components, movements: result.movements,
    }, null, 2)));
    detail.append(advances, records);
    evidence.append(detail); row.append(evidence);
    ['Game / PA index', 'Batter', presentation.label, 'Evidence'].forEach((label, index) => { row.children[index].dataset.label = label; });
    body.append(row);
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
    [node('p', selected.id === 'adjudication-volatility' ? 'This result covers explicitly resolved mapped replay reviews. Unresolved reviews are reported separately.' : 'No additional requirements were reported for this result.')]));
}

function choose(metric) {
  activeRequest?.abort(); activeRequest = null;
  selected = metric; lastResult = null;
  byId('download-result').disabled = true;
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
  renderExamples();
  document.querySelectorAll('#metric-list button').forEach(button => button.setAttribute('aria-current', String(button.dataset.id === metric.id)));
  saveSelection();
}

function renderList() {
  const term = byId('metric-search').value.trim().toLowerCase();
  byId('metric-list').replaceChildren(...catalog.metrics.filter(m => (m.label + ' ' + m.id).toLowerCase().includes(term)).map(metric => {
    const button = node('button', metric.label); button.type = 'button'; button.dataset.id = metric.id;
    button.setAttribute('aria-current', String(selected?.id === metric.id));
    button.append(node('small', metric.liveAdapter === 'loaded-award-consequences' ? 'Limited play results' :
      metric.requires.length ? 'Evidence pending' : 'Resolved review results'));
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
  byId('download-result').disabled = true;
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
    const presentation = resultPresentation(payload, selected);
    byId('result').dataset.state = presentation.state;
    byId('result-badge').textContent = presentation.badge;
    byId('result-dates').textContent = resultDateLabel(payload);
    const loaded = payload.dateScope ?? {};
    byId('loaded-dates').textContent = loaded.availableStartDate && loaded.availableEndDate ?
      `Loaded dates: ${loaded.availableStartDate} to ${loaded.availableEndDate}.` : '';
    byId('score-value').textContent = presentation.headline;
    const single = presentation.state === 'partial' && result.consequences.length === 1 ? result.consequences[0] : null;
    const displayed = result.value ?? single?.value;
    byId('score-exact').textContent = displayed ? `Exact: ${displayed.numerator}/${displayed.denominator}` : '';
    byId('result-subject').textContent = single ?
      `${displayPlayer(payload.display?.labels, single.graph, single.batter)} · Game ${single.graph.split('/').at(-1)} · PA source index ${single.plateAppearance.split('/').at(-1)}` : '';
    byId('result-scope').textContent = presentation.state === 'partial' ?
      'These scores cover the shown Walk/HBP advances only. Full plate-appearance and population results remain unavailable.' : result.scope ?? 'Selected evidence population';
    byId('coverage-details').open = presentation.state === 'empty' || selected.id === 'adjudication-volatility';
    const coverage = result.coverage ?? {};
    renderGameCoverage(coverage.byGame);
    renderConsequences(result.consequences, result.metricId, payload.display?.labels);
    facts(byId('coverage'), [['Games', coverage.games ?? payload.graphCount ?? 0],
      ...(coverage.supportedAwardConsequences !== undefined ? [
        ['Supported award consequences', coverage.supportedAwardConsequences],
        ['Observed PAs without a scored award result', coverage.observedPAsWithoutSupportedAwardConsequence],
        ['Selected games with no evidence rows', coverage.selectedGraphsWithoutEvidence]] : []),
      ...(coverage.resolvedReviews !== undefined ? [['Resolved reviews', coverage.resolvedReviews], ['Unresolved reviews', coverage.unresolvedReviews]] : [])]);
    byId('result-evidence').textContent = JSON.stringify({ coverage, components: result.components ?? {}, evidence: result.evidence ?? [],
      implementation: payload.implementationSha256, corpus: payload.corpusFingerprint ?? payload.serving?.corpusFingerprint,
      dateScope: payload.dateScope, execution: payload.execution, display: payload.display }, null, 2);
    renderRequirements(result.gaps ?? []);
    byId('result').hidden = false;
    byId('download-result').disabled = false;
    byId('request-status').textContent = presentation.message;
  } catch (error) {
    if (activeRequest === controller && error.name !== 'AbortError') byId('request-status').textContent = error.message;
  } finally {
    if (activeRequest === controller) { byId('run-metric').disabled = false; activeRequest = null; }
  }
}

async function start() {
  try {
    const response = await fetch('/api/metrics/catalog');
    if (!response.ok) throw new Error('The metric catalog could not be loaded.');
    catalog = await response.json();
    const initial = selectionFromUrl(location.href);
    byId('game-set').value = initial.gameSet; byId('date-preset').value = initial.preset;
    byId('start-date').value = initial.startDate ?? ''; byId('end-date').value = initial.endDate ?? '';
    const updateDates = () => document.querySelectorAll('.custom-date').forEach(label => {
      label.hidden = byId('date-preset').value !== 'custom'; label.querySelector('input').required = !label.hidden;
    });
    updateDates();
    renderList(); choose(catalog.metrics.find(m => '#' + m.id === location.hash) ?? catalog.metrics[0]);
    byId('all-gaps').replaceChildren(...catalog.gapRegister.gaps.map(g => gapDetails(g, true)));
    byId('download-gaps').disabled = false;
    byId('download-gaps').addEventListener('click', () => download('baseballo-metric-gaps.json', catalog.gapRegister));
    byId('download-result').addEventListener('click', () => { if (lastResult) download(selected.id + '-result.json', lastResult); });
    byId('metric-search').addEventListener('input', renderList);
    byId('metric-form').addEventListener('submit', inspect);
    byId('metric-form').addEventListener('input', invalidateSelection);
    byId('metric-form').addEventListener('change', invalidateSelection);
    byId('date-preset').addEventListener('change', updateDates);
    byId('example-choice').addEventListener('change', renderExampleCase);
    // Examples are presentation-only. Failure must not disable live inspection.
    fetch('/metric-examples.json').then(async response => {
      if (!response.ok) throw new Error('Examples unavailable');
      examples = await response.json(); renderExamples();
    }).catch(() => { examples = undefined; renderExamples(); });
  } catch (error) { byId('metric-title').textContent = 'Metrics unavailable'; byId('request-status').textContent = error.message; }
}

if (typeof document !== 'undefined') start();
