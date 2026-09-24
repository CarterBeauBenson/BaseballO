import { readFile } from 'node:fs/promises';

const root = new URL('../../sparql/metrics/', import.meta.url);
const participationPolicies = JSON.parse(await readFile(new URL('../leaderboard-qualification.json', import.meta.url), 'utf8'));
const REVIEW_MECHANISMS = [['traditional-replay', 'Traditional replay'], ['ball-strike-challenge', 'Ball/strike challenges']];

export function automaticMinimumObservations(policyId, teamGames) {
  const policy = participationPolicies.policies[policyId];
  if (!policy || !Number.isSafeInteger(teamGames) || teamGames < 1) throw new RangeError('A defined policy and complete team-game exposure are required.');
  return Math.max(policy.floor, Number((BigInt(teamGames) + BigInt(policy.teamGamesDivisor) - 1n) / BigInt(policy.teamGamesDivisor)));
}

const BATTING_LEADERBOARDS = new Set(['tfs', 'paq-2', 'paq-a', 'offensive-reach',
  'hidden-help-rate', 'rally-kill-rate', 'rally-kill-severity', 'opportunity-erosion',
  'empty-game-rate', 'empty-game-damage', 'recovery-quality', 'paq-2.1']);

export function automaticMinimumPA(teamGames) {
  if (!Number.isSafeInteger(teamGames) || teamGames < 1) throw new RangeError('Complete team-game exposure is required.');
  return Number((31n * BigInt(teamGames) + 5n) / 10n);
}

export function playerSummaryValue(aggregate, metricId) {
  // CPD is the entropy of the pooled positive channels, not a mean of daily
  // entropy scores and not an exact fraction. It has its own summary below.
  if (metricId === 'contribution-path-diversity') return null;
  if (metricId === 'empty-game-rate') {
    if (aggregate?.kind !== 'count' || !Number.isSafeInteger(aggregate.count) || aggregate.count < 0 ||
        !Number.isSafeInteger(aggregate.eligibleGames) || aggregate.eligibleGames < aggregate.count) return null;
    return {numerator:String(aggregate.count),denominator:'1'};
  }
  if (aggregate?.kind !== 'mean' || !Number.isSafeInteger(aggregate.count) || aggregate.count < 1 ||
      typeof aggregate.sum?.numerator !== 'string' || typeof aggregate.sum?.denominator !== 'string' ||
      !/^-?\d+$/u.test(aggregate.sum?.numerator ?? '') || !/^\d+$/u.test(aggregate.sum?.denominator ?? '') ||
      BigInt(aggregate.sum.denominator) < 1n) return null;
  let numerator=BigInt(aggregate.sum.numerator), denominator=BigInt(aggregate.sum.denominator)*BigInt(aggregate.count);
  let a=numerator<0n?-numerator:numerator, b=denominator;
  while(b) [a,b]=[b,a%b];
  return {numerator:String(numerator/a),denominator:String(denominator/a)};
}

export function playerChannelSummary(aggregate) {
  if (aggregate?.kind !== 'channel_entropy' || !Array.isArray(aggregate.channelCounts) ||
      aggregate.channelCounts.length !== 3 || aggregate.channelCounts.some(c => !Number.isSafeInteger(c) || c < 0)) return null;
  const count = aggregate.channelCounts.reduce((a, b) => a + b, 0);
  if (!Number.isSafeInteger(count) || count < 1) return null;
  // Sort only the arithmetic terms, retaining the named channel order in the
  // result. Permuting channels must not introduce floating-point tie noise.
  const terms = aggregate.channelCounts.filter(c => c > 0).map(c => c / count).sort((a, b) => a - b);
  const approximateValue = Math.min(1, Math.max(0, -terms.reduce((sum, p) => sum + p * Math.log(p), 0) / Math.log(3)));
  return {value:null, approximateValue, channelCounts:[...aggregate.channelCounts], count};
}

export function publicMetricResult(result) {
  if (result.metricId !== 'empty-game-rate' || result.status !== 'available') return result;
  const value=playerSummaryValue({kind:'count',count:result.components?.emptyGames,
    eligibleGames:result.components?.eligibleGames},result.metricId);
  return value ? {...result,value,summaryKind:'count'} :
    {...result,status:'unavailable',value:null,gaps:[...(result.gaps ?? []),'OFFENSIVE_ELIGIBILITY']};
}

export function playerLeaderboard(result, metric, dateScope, mechanism = null) {
  if (['adjudication-volatility', 'review-dependence-rate'].includes(metric.id) && mechanism === null) {
    // Distinct denominator populations and qualifications; never pool reviews.
    if (result.playerResults !== undefined && (!Array.isArray(result.playerResults) ||
        result.playerResults.some(row => !REVIEW_MECHANISMS.some(([id]) => row?.mechanism === id))))
      return {status:'unavailable', rows:[], gaps:['REVIEW_MECHANISM_UNKNOWN'], message:'Review mechanisms must be established before ranking players.'};
    const groups = REVIEW_MECHANISMS.map(([id, label]) => ({mechanism:id, label,
      ...playerLeaderboard(result.byMechanism?.[id] ?? {...result,
        playerResults:result.playerResults?.filter(row => row.mechanism === id)}, metric, dateScope, id)}));
    const rows = groups.flatMap(group => group.rows.map(row => ({...row, mechanism:group.mechanism, mechanismLabel:group.label})));
    return {status:rows.length ? 'available' : groups.every(group => group.status === 'empty') ? 'empty' : 'unavailable',
      rows, groups, summaryKind:'mean', unit:metric.unit, order:'Highest scores first',
      qualification:{status:'defined', rule:'Each review mechanism has its own population and automatic minimum.'},
      gaps:[...new Set(groups.flatMap(group => group.gaps ?? []))],
      message:rows.length ? `${rows.length} qualified player entries across separate review mechanisms` : 'No qualified review leaderboard is available for this period.'};
  }
  const batting = BATTING_LEADERBOARDS.has(metric.id);
  const either = participationPolicies.eitherBattingOrRunning.includes(metric.id);
  const policyId = metric.id === 'review-dependence-rate' ?
    (mechanism === 'traditional-replay' ? 'traditional-review-dependence' : 'ball-strike-review-dependence') : participationPolicies.metrics[metric.id];
  const policy = participationPolicies.policies[policyId];
  const paRule = '3.1 PA per team game in the selected range, rounded to the nearest whole PA.';
  const participationRule = policy ? `At least ${policy.floor} ${policy.unit}, or one per ${policy.teamGamesDivisor} team game${policy.teamGamesDivisor === 1 ? '' : 's'} in the selected range, whichever is greater; round upward.` : '';
  const qualification = {status:batting || policy ? 'defined' : 'pending',
    kind:either ? 'either_batting_or_running' : batting ? 'plate_appearances' : 'role_participation', policyId:policyId ?? 'batting',
    rule:either ? `Meet either the batting minimum (${paRule}) or the running minimum (${participationRule})` :
      [batting ? paRule : '', participationRule].filter(Boolean).join(' ')};
  const board = { status: 'unavailable', rows: [], qualification,
    summaryKind: metric.id === 'empty-game-rate' ? 'count' : 'mean',
    unit: metric.id === 'empty-game-rate' ? 'games' : metric.unit,
    order: metric.higherIs === 'worse' ? 'Lowest scores first' : 'Highest scores first' };
  if (!batting && !policy) return { ...board, gaps: ['ROLE_QUALIFICATION'],
    message: 'Player rankings await a defined participation minimum and complete player scores.' };
  // Only the trusted serving adapter can supply these aggregates. Award
  // consequences, individual runs and population-only scores are insufficient.
  if (result.playerPopulationComplete !== true || !Array.isArray(result.playerResults)) return {
    ...board, gaps: ['COMPLETE_PLAYER_SCORES'], message: 'Complete player scores are not yet available for this period.' };
  const seen = new Set(), rows = [];
  let belowMinimum = 0;
  for (const row of result.playerResults) {
    const channelSummary = metric.id === 'contribution-path-diversity' ? playerChannelSummary(row.aggregate) : null;
    const value = playerSummaryValue(row.aggregate, metric.id);
    const sameScope = dateScope && ['startDate', 'endDate', 'gameSet'].every(key =>
      typeof dateScope[key] === 'string' && row.dateScope?.[key] === dateScope[key]);
    if (!sameScope || row.metricId !== metric.id || row.status !== 'available' || row.completeParticipation !== true ||
        !/^https:\/\/baseballontology\.org\/data\/player\/\d+$/u.test(row.player ?? '') || seen.has(row.player) ||
        ((batting || either) && (!Number.isSafeInteger(row.plateAppearances) || row.plateAppearances < 0)) ||
        (either && (!Number.isSafeInteger(row.independentRunningEpisodes) || row.independentRunningEpisodes < 0)) ||
        (mechanism && row.mechanism !== mechanism) ||
        !Number.isSafeInteger(row.teamGames) || row.teamGames < 1 ||
        !(channelSummary || value)) return { ...board, gaps: ['PLAYER_SCORE_COVERAGE'],
      message: 'Player scores or participation evidence are incomplete for this period.' };
    seen.add(row.player);
    const minimumPA = batting || either ? automaticMinimumPA(row.teamGames) : null;
    const minimumObservations = policy ? automaticMinimumObservations(policyId, row.teamGames) : null;
    const participationCount = either ? row.independentRunningEpisodes : row.aggregate.count;
    const battingQualified = (batting || either) && row.plateAppearances >= minimumPA;
    const observationsQualified = policy && participationCount >= minimumObservations;
    if (either ? !(battingQualified || observationsQualified) :
        ((batting && !battingQualified) || (policy && !observationsQualified))) { belowMinimum++; continue; }
    rows.push({ player: row.player, name: row.playerLabel?.trim() || `Player #${row.player.split('/').at(-1)}`,
      value, ...(channelSummary ? {approximateValue:channelSummary.approximateValue, channelCounts:channelSummary.channelCounts} : {}),
      observationCount: channelSummary?.count ?? row.aggregate.count, plateAppearances: row.plateAppearances, teamGames: row.teamGames, minimumPA,
      ...(either ? {independentRunningEpisodes:row.independentRunningEpisodes,
        qualifiedThrough:[battingQualified ? 'batting' : '', observationsQualified ? 'running' : ''].filter(Boolean)} : {}),
      minimumObservations, minimumObservationUnit:policy?.unit,
      observationUnit:channelSummary ? 'positive channel occurrences' : policy?.unit,
      qualificationLabel:either ? [battingQualified ? `${row.plateAppearances} PA · minimum ${minimumPA} PA` : '',
        observationsQualified ? `${participationCount} ${policy.unit} · minimum ${minimumObservations}` : ''].filter(Boolean).join('; ') :
        [batting ? `${row.plateAppearances} PA · minimum ${minimumPA} PA` : '',
        policy ? `${participationCount} ${policy.unit} · minimum ${minimumObservations}` : ''].filter(Boolean).join('; ') });
  }
  const compare = (a, b) => {
    // Logarithmic scores retain exact input counts, but their numerical
    // evaluation and ordering are approximate. Never sort rounded display text.
    if (metric.id === 'contribution-path-diversity') return Math.sign(a.approximateValue - b.approximateValue);
    const difference = BigInt(a.value.numerator) * BigInt(b.value.denominator) - BigInt(b.value.numerator) * BigInt(a.value.denominator);
    return difference < 0n ? -1 : difference > 0n ? 1 : 0;
  };
  rows.sort((a, b) => (metric.higherIs === 'worse' ? 1 : -1) * compare(a, b) || a.player.localeCompare(b.player));
  rows.forEach((row, index) => { row.rank = index && compare(row, rows[index - 1]) === 0 ? rows[index - 1].rank : index + 1; });
  return { ...board, status: rows.length ? 'available' : 'empty', rows, belowMinimum, gaps: [],
    message: rows.length ? `${rows.length} qualified players` : 'No players meet the automatic participation minimum for this period.' };
}

export function dashboardReadiness(metrics, expectedIds) {
  // Consume the same qualified boards shown by the UI. Aggregate scores and
  // successful SQL delivery alone are not evidence of populated player cards.
  const cards = expectedIds.map(metricId => {
    const matches = metrics.filter(metric => metric.metricId === metricId);
    const metric = matches.length === 1 ? matches[0] : null;
    const board = metric?.leaderboard;
    const groups = board?.groups ?? [board];
    const populationComplete = groups.length > 0 && groups.every(group =>
      ['available', 'empty'].includes(group?.status));
    const qualifiedRows = board?.status === 'available' ? board.rows?.length ?? 0 : 0;
    return {metricId, status:qualifiedRows ? 'populated' : populationComplete ? 'no-qualifiers' : 'unavailable',
      populationComplete, qualifiedRows,
      gaps:[...new Set([...(metric?.playerSummaryGaps ?? []), ...(board?.gaps ?? []),
        ...(metric ? [] : [matches.length ? 'DUPLICATE_METRIC_RESULT' : 'MISSING_METRIC_RESULT'])])],
      ...(board?.groups ? {mechanisms:board.groups.map(group => ({mechanism:group.mechanism,
        status:group.status, qualifiedRows:group.rows?.length ?? 0, gaps:group.gaps ?? []}))} : {})};
  });
  const populatedLeaderboards = cards.filter(card => card.status === 'populated').length;
  const completePopulations = cards.filter(card => card.populationComplete).length;
  return {expectedLeaderboards:expectedIds.length, populatedLeaderboards, completePopulations,
    emptyLeaderboards:cards.filter(card => card.status === 'no-qualifiers').length,
    unavailableLeaderboards:cards.filter(card => card.status === 'unavailable').length,
    ready:expectedIds.length > 0 && populatedLeaderboards === expectedIds.length && completePopulations === expectedIds.length,
    cards};
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

export function metricLabelIndex(labels) {
  const index = new Map();
  for (const {entity, graph, label} of labels) {
    if (!index.has(entity)) index.set(entity, new Map());
    const graphs = index.get(entity);
    if (!graphs.has(graph)) graphs.set(graph, new Set());
    graphs.get(graph).add(label);
  }
  return index;
}

export function labelMetricPlayers(metric, labels) {
  const index = labels instanceof Map ? labels : metricLabelIndex(labels);
  const named = row => {
    const graphs = new Set(row.graphs ?? (metric.runs ?? []).filter(run => run.runner === row.player).map(run => run.graph));
    const playerNames = index.get(row.player), names = new Set();
    for (const graph of graphs) for (const name of playerNames?.get(graph) ?? []) names.add(name);
    if (names.size === 1) return { ...row, playerLabel: [...names][0] };
    if (names.size > 1) { const { playerLabel, ...unnamed } = row; return unnamed; }
    return row;
  };
  return { ...metric,
    ...(Array.isArray(metric.playerResults) ? {playerResults:metric.playerResults.map(named)} : {}),
    ...(metric.byMechanism ? {byMechanism:Object.fromEntries(Object.entries(metric.byMechanism)
      .map(([id, result]) => [id, labelMetricPlayers(result, index)]))} : {}) };
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
    .map(metric => ({ ...metric, technicalLabel: metric.label, technicalUnit: metric.unit,
      unit: display.metrics[metric.id].displayUnit ?? metric.unit,
      technicalDefinition: metric.userDefinition, label: display.metrics[metric.id].label,
      userDefinition: display.metrics[metric.id].summary, presentation: {...display.metrics[metric.id],
        playerSummary:display.metrics[metric.id].playerSummary ?? display.defaultPlayerSummary} }));
  const requirements = new Set(metrics.flatMap(metric => metric.requires));
  return { ...source, gapRegister: { ...JSON.parse(register),
    gaps: JSON.parse(register).gaps.filter(gap => requirements.has(gap.id)) },
    presentationVersion: display.version, playerPresentationDecision: display.playerPresentationDecision,
    selectedRangeDecision: display.selectedRangeDecision,
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
  const sources = await Promise.all(['suite-evidence.rq', 'runner-movement-evidence.rq', 'pitch-count-evidence.rq', 'runner-location-evidence.rq'].map(async name => {
    const source = (await readFile(new URL(name, root), 'utf8')).replace(/\r\n/g, '\n').replaceAll('bfo:', 'obo:');
    for (const prefix of source.match(/^PREFIX .+$/gm) ?? []) prefixes.add(prefix);
    return source.replace(/^PREFIX .+\n/gm, '').replace('WHERE {', `WHERE {\n  ${values}`);
  }));
  // Keep the authoritative fallback and Python SQL extractor equivalent.
  // A cross-runtime regression compares the complete compiled query text.
  const dataset = selected.map(g => `\nFROM NAMED <${g}>`).join('');
  return [...prefixes].sort().join('\n') + '\nSELECT *' + dataset + '\nWHERE {\n{ {\n' + sources[0]
    + '\n} } UNION { {\n' + sources[1]
    + '\n} BIND("runner_movement" AS ?kind) BIND(?resolution AS ?entity) }'
    + '\nUNION { {\n' + sources[2] + '\n} BIND("pitch_count" AS ?kind) }'
    + '\nUNION { {\n' + sources[3] + '\n} BIND("runner_location" AS ?kind) BIND(?stasis AS ?entity) }\n}';
}
