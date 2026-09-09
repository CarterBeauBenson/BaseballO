import { readFile } from 'node:fs/promises';

const root = new URL('../../sparql/metrics/', import.meta.url);

export async function metricCatalog() {
  const [catalog, register] = await Promise.all([
    readFile(new URL('metric-catalog.json', root), 'utf8'),
    readFile(new URL('gap-register.json', root), 'utf8'),
  ]);
  return { ...JSON.parse(catalog), gapRegister: JSON.parse(register) };
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
