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
  byId('request-status').textContent = metric.requires.length ? 'Calculation implemented. Live values await the requirements below.' : 'Inspect the selected mapped review population.';
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
    button.append(node('small', metric.requires.length ? 'Awaiting shared requirements' : 'Resolved review evidence'));
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
    byId('score-value').textContent = result.status === 'available' ?
      (result.value ? displayFraction(result.value) : result.approximateValue.toFixed(3)) : 'Unavailable';
    byId('score-exact').textContent = result.value ? `Exact: ${result.value.numerator}/${result.value.denominator}` : '';
    byId('result-scope').textContent = result.scope ?? 'Selected evidence population';
    const coverage = result.coverage ?? {};
    const movement = coverage.runnerMovements;
    facts(byId('coverage'), [['Games', coverage.games ?? payload.graphCount ?? 0], ['Evidence rows', coverage.evidenceRows ?? 0],
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
    byId('request-status').textContent = result.status === 'available' ? 'Result ready for the stated population.' : 'No valid score can be produced from the current evidence. The unresolved requirements are listed below.';
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
