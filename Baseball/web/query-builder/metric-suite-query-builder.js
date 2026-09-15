import { readFile } from 'node:fs/promises';

const root = new URL('../../sparql/metrics/', import.meta.url);

const BATTING_LEADERBOARDS = new Set(['tfs', 'paq-2', 'paq-a', 'offensive-reach',
  'hidden-help-rate', 'rally-kill-rate', 'rally-kill-severity', 'opportunity-erosion',
  'empty-game-rate', 'empty-game-damage', 'recovery-quality', 'paq-2.1']);

export function automaticMinimumPA(teamGames) {
  if (!Number.isSafeInteger(teamGames) || teamGames < 1) throw new RangeError('Complete team-game exposure is required.');
  return Number((31n * BigInt(teamGames) + 5n) / 10n);
}

export function playerLeaderboard(result, metric, dateScope) {
  const batting = BATTING_LEADERBOARDS.has(metric.id);
  const qualification = batting ? { status: 'defined', kind: 'plate_appearances',
    rule: '3.1 PA per team game in the selected range, rounded to the nearest whole PA.' } :
    { status: 'pending', kind: 'role_participation', rule: 'A role-specific participation minimum is still required.' };
  const board = { status: 'unavailable', rows: [], qualification,
    order: metric.higherIs === 'worse' ? 'Lowest scores first' : 'Highest scores first' };
  if (!batting) return { ...board, gaps: ['ROLE_QUALIFICATION'],
    message: 'Player rankings await a defined participation minimum and complete player scores.' };
  // Only the trusted serving adapter can supply these aggregates. Award
  // consequences, individual runs and population-only scores are insufficient.
  if (result.playerPopulationComplete !== true || !Array.isArray(result.playerResults)) return {
    ...board, gaps: ['COMPLETE_PLAYER_SCORES'], message: 'Complete player scores are not yet available for this period.' };
  const seen = new Set(), rows = [];
  let belowMinimum = 0;
  for (const row of result.playerResults) {
    const sameScope = dateScope && ['startDate', 'endDate', 'gameSet'].every(key =>
      typeof dateScope[key] === 'string' && row.dateScope?.[key] === dateScope[key]);
    if (!sameScope || row.metricId !== metric.id || row.status !== 'available' || row.completeParticipation !== true ||
        !/^https:\/\/baseballontology\.org\/data\/player\/\d+$/u.test(row.player ?? '') || seen.has(row.player) ||
        !Number.isSafeInteger(row.plateAppearances) || row.plateAppearances < 0 ||
        !Number.isSafeInteger(row.teamGames) || row.teamGames < 1 ||
        !/^-?\d+$/u.test(row.value?.numerator ?? '') || !/^\d+$/u.test(row.value?.denominator ?? '') ||
        BigInt(row.value.denominator) < 1n) return { ...board, gaps: ['PLAYER_SCORE_COVERAGE'],
      message: 'Player scores or participation evidence are incomplete for this period.' };
    seen.add(row.player);
    const minimumPA = automaticMinimumPA(row.teamGames);
    if (row.plateAppearances < minimumPA) { belowMinimum++; continue; }
    rows.push({ player: row.player, name: row.playerLabel?.trim() || `Player #${row.player.split('/').at(-1)}`,
      value: row.value, plateAppearances: row.plateAppearances, teamGames: row.teamGames, minimumPA });
  }
  const compare = (a, b) => {
    const difference = BigInt(a.value.numerator) * BigInt(b.value.denominator) - BigInt(b.value.numerator) * BigInt(a.value.denominator);
    return difference < 0n ? -1 : difference > 0n ? 1 : 0;
  };
  rows.sort((a, b) => (metric.higherIs === 'worse' ? 1 : -1) * compare(a, b) || a.player.localeCompare(b.player));
  rows.forEach((row, index) => { row.rank = index && compare(row, rows[index - 1]) === 0 ? rows[index - 1].rank : index + 1; });
  return { ...board, status: rows.length ? 'available' : 'empty', rows, belowMinimum, gaps: [],
    message: rows.length ? `${rows.length} qualified players` : 'No players meet the automatic PA minimum for this period.' };
}

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
  const metrics = source.metrics.filter(metric => display.metrics[metric.id].visibility !== 'backend')
    .map(metric => ({ ...metric, technicalLabel: metric.label,
      technicalDefinition: metric.userDefinition, label: display.metrics[metric.id].label,
      userDefinition: display.metrics[metric.id].summary, presentation: display.metrics[metric.id] }));
  const requirements = new Set(metrics.flatMap(metric => metric.requires));
  return { ...source, gapRegister: { ...JSON.parse(register),
    gaps: JSON.parse(register).gaps.filter(gap => requirements.has(gap.id)) },
    presentationVersion: display.version, playerPresentationDecision: display.playerPresentationDecision,
    groups: display.groups, metrics };
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
