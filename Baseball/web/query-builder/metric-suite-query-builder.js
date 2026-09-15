import { readFile } from 'node:fs/promises';

const root = new URL('../../sparql/metrics/', import.meta.url);

export function metricDisplayTargets(consequences = []) {
  const targets = new Map();
  for (const row of consequences) {
    if (!/^https:\/\/w3id\.org\/baseball\/graph\/game\/\d+$/.test(row.graph)) throw new TypeError('Invalid display graph.');
    for (const entity of [row.batter, ...(row.movements ?? []).map(m => m.runner)]) {
      if (!/^https:\/\/baseballontology\.org\/data\/player\/\d+$/.test(entity)) throw new TypeError('Invalid display player.');
      targets.set(JSON.stringify([row.graph, entity]), { graph: row.graph, entity });
    }
  }
  return [...targets.values()];
}

export async function compileMetricDisplayQuery(targets) {
  if (!targets.length) return null;
  // Validate even when called independently of metricDisplayTargets.
  metricDisplayTargets(targets.map(t => ({ graph: t.graph, batter: t.entity })));
  const source = await readFile(new URL('../options/metric-display-labels.rq', root), 'utf8');
  return source.replace('# DATASET', [...new Set(targets.map(t => t.graph))].sort().map(g => `FROM NAMED <${g}>`).join('\n'))
    .replace('# DISPLAY_ROWS', targets.map(t => `(<${t.graph}> <${t.entity}>)`).join('\n'));
}

export function normalizeMetricDisplayLabels(bindings, targets) {
  const allowed = new Set(targets.map(t => JSON.stringify([t.graph, t.entity]))), labels = new Map();
  for (const row of bindings) {
    const key = JSON.stringify([row.graph?.value, row.entity?.value]);
    if (!allowed.has(key) || row.graph?.type !== 'uri' || row.entity?.type !== 'uri'
      || row.label?.type !== 'literal' || typeof row.label.value !== 'string' || !row.label.value.trim()) continue;
    if (!labels.has(key)) labels.set(key, new Set());
    labels.get(key).add(row.label.value);
  }
  return targets.flatMap(t => {
    const values = labels.get(JSON.stringify([t.graph, t.entity]));
    return values?.size === 1 ? [{ ...t, label: [...values][0] }] : [];
  });
}

export async function metricCatalog() {
  const [catalog, register, presentation] = await Promise.all([
    readFile(new URL('metric-catalog.json', root), 'utf8'),
    readFile(new URL('gap-register.json', root), 'utf8'),
    readFile(new URL('../metric-presentation.json', import.meta.url), 'utf8'),
  ]);
  const source = JSON.parse(catalog), display = JSON.parse(presentation);
  return { ...source, gapRegister: JSON.parse(register), presentationVersion: display.version, groups: display.groups,
    metrics: source.metrics.map(metric => ({ ...metric, technicalLabel: metric.label,
      technicalDefinition: metric.userDefinition, label: display.metrics[metric.id].label,
      userDefinition: display.metrics[metric.id].summary, presentation: display.metrics[metric.id] })) };
}

export function validateMetricRequest(input, catalog) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected a metric request.');
  const allowed = new Set(['metricId', 'dateScope', 'gameSet']);
  if (Object.keys(input).some(key => !allowed.has(key))) throw new TypeError('Only metric, date scope and game set may be selected.');
  if (!catalog.metrics.some(metric => metric.id === input.metricId)) throw new RangeError('Unknown metric.');
  if (input.gameSet !== undefined && !['regular_season', 'all_star'].includes(input.gameSet)) throw new RangeError('Unsupported game set.');
  const dateScope = input.dateScope ?? { preset: 'season_to_date' };
  if (!dateScope || typeof dateScope !== 'object' || Array.isArray(dateScope)) throw new TypeError('Invalid date scope.');
  if (!['one_day', 'seven_days', 'thirty_days', 'season_to_date', 'custom'].includes(dateScope.preset)) throw new RangeError('Invalid date preset.');
  if (Object.keys(dateScope).some(k => !['preset', 'startDate', 'endDate'].includes(k))) throw new TypeError('Invalid date scope field.');
  for (const key of ['startDate', 'endDate']) {
    if (dateScope[key] !== undefined && (typeof dateScope[key] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(dateScope[key]) ||
      !Number.isFinite(Date.parse(dateScope[key])) || new Date(dateScope[key]).toISOString().slice(0, 10) !== dateScope[key])) {
      throw new TypeError('Dates must be valid YYYY-MM-DD values.');
    }
  }
  if (dateScope.preset === 'custom' && (!dateScope.startDate || !dateScope.endDate || dateScope.startDate > dateScope.endDate)) {
    throw new RangeError('Select an ordered custom date range.');
  }
  return { route: 'metric-suite', metricId: input.metricId, dateScope, gameSet: input.gameSet ?? 'regular_season' };
}

export function validateDashboardRequest(input, catalog) {
  if (!input || typeof input !== 'object' || Array.isArray(input) ||
      Object.keys(input).some(key => !['dateScope', 'gameSet'].includes(key))) {
    throw new TypeError('Only date scope and game set may be selected for the dashboard.');
  }
  const { metricId, ...validated } = validateMetricRequest({ ...input, metricId: catalog.metrics[0].id }, catalog);
  return { ...validated, view: 'dashboard' };
}

export async function compileMetricEvidenceQuery(graphs) {
  if (!Array.isArray(graphs) || graphs.some(g => typeof g !== 'string' || !/^https:\/\/w3id\.org\/baseball\/graph\/game\/\d+$/.test(g))) {
    throw new TypeError('Invalid authoritative graph scope.');
  }
  const selected = [...new Set(graphs)].sort();
  if (!selected.length) return 'SELECT ?graph ?game ?kind ?entity WHERE { BIND(0 AS ?emptyScope) FILTER(?emptyScope = 1) }';
  const values = selected.length ? `VALUES ?graph { ${selected.map(g => `<${g}>`).join(' ')} }` : 'FILTER(false)';
  const prefixes = new Set();
  const sources = await Promise.all(['suite-evidence.rq', 'runner-movement-evidence.rq'].map(async name => {
    const source = (await readFile(new URL(name, root), 'utf8')).replace(/\r\n/g, '\n').replaceAll('bfo:', 'obo:');
    for (const prefix of source.match(/^PREFIX .+$/gm) ?? []) prefixes.add(prefix);
    return source.replace(/^PREFIX .+\n/gm, '').replace('WHERE {', `WHERE {\n  ${values}`);
  }));
  // Keep the authoritative fallback and Python SQL extractor equivalent.
  // A cross-runtime regression compares the complete compiled query text.
  const dataset = selected.map(g => `\nFROM NAMED <${g}>`).join('');
  return [...prefixes].sort().join('\n') + '\nSELECT *' + dataset + '\nWHERE {\n{ {\n' + sources[0]
    + '\n} } UNION { {\n' + sources[1]
    + '\n} BIND("runner_movement" AS ?kind) BIND(?resolution AS ?entity) }\n}';
}
