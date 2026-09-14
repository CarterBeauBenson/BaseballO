"""Build worked UI examples with the existing metric calculations.

Developer documentation generation, not source admission or materialization.
All populations and attribution inputs here are explicitly hypothetical. The
published examples never enter SQL, RDF, live responses, or result downloads.
"""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('metric_suite', ROOT / 'serving/metric_suite.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
DEST = ROOT / 'web/metric-examples.json'
GUIDE = ROOT / 'web/metric-worked-examples.md'
PRESENTATION = ROOT / 'web/metric-presentation.json'


def build():
    examples = {}

    def add(metric, formula, title, explanation, equation, result, expected):
        # Independent expected answers protect the worked explanation from
        # silently changing when the implementation changes.
        if expected is None:
            assert result['status'] == 'unavailable', (metric, title, result)
        elif isinstance(expected, float):
            assert result['status'] == 'available' and abs(result['approximateValue'] - expected) < 1e-12
        else:
            assert result['status'] == 'available' and M.fraction(result['value']) == Fraction(expected), (metric, title, result)
        entry = examples.setdefault(metric, dict(formula=formula, cases=[]))
        assert entry['formula'] == formula
        entry['cases'].append(dict(title=title, explanation=explanation, equation=equation, result=result))

    def calc(metric, rows):
        return M.calculate(metric, [dict(key='illustration', **row) for row in rows])

    tfs_formula = 'TFS = attributed progress − trajectory destruction − opportunity erosion.'
    batter = dict(participant='batter', start=0, end=None, terminal='out', creditProgress=False, creditOut=True)
    for title, outs, terminal, end, explanation, equation, expected in [
        ('Strikeout; runner stays on third', 1, 'safe', 3,
         'One out before the PA. The batter strikes out and the runner remains on third. The batter loses 1/4; the runner loses 1/2 of remaining opportunity.',
         '0 − 1/4 − 1/2 = −3/4', '-3/4'),
        ('Third out strands the runner', 2, 'stranded', 3,
         'Two outs before the PA. The strikeout ends the inning. Charge 1/4 for the batter and 1 for the stranded runner; stranding is not an extra out.',
         '0 − 1/4 − 1 = −5/4', '-5/4'),
        ('Strikeout; runner scores on a passed ball', 1, 'scored', 4,
         'One out before the PA. The batter is out; the runner on third scores independently on a passed ball. The hitter gets no progress credit. The actual scored runner has no remaining opportunity to erode.',
         '0 − 1/4 − 0 = −1/4', '-1/4'),
    ]:
        result = M.trajectories([batter, dict(participant='runner', start=3, end=end,
                               terminal=terminal, creditProgress=False, creditOut=False)], outs, 1)
        add('tfs', tfs_formula, title, explanation, equation, result, expected)

    rank_formula = 'Percentile = 100 × (2 × lower scores + tied scores − 1) / (2 × (population size − 1)).'
    peers = [dict(key=k, score=s) for k, s in [('A', '-1/4'), ('B', '1/3'), ('C', '2/6'), ('D', '1/2')]]
    add('paq-2', rank_formula, 'Two PAs tie exactly',
        'Assume a complete illustrative reference population of four PAs: −1/4, 1/3, 2/6 and 1/2. The middle two tie exactly. Real PAQ uses the eligible selected-season population through the reporting cutoff.',
        'For either middle PA: 100 × (2 × 1 + 2 − 1) / (2 × 3) = 50',
        M.percentiles(peers, complete_population=True)['B'], 50)
    add('paq-2', rank_formula, 'Only one eligible PA',
        'A reference population with one PA cannot define this percentile. An unavailable result is not a zero percentile.',
        'Population size − 1 = 0; the percentile is unavailable.',
        M.percentiles(peers[:1], complete_population=True)['A'], None)
    adjusted = [dict(key=k, score=s, referencePopulation='illustrative-season', comparisonState=dict(
        boundary=M.policies()['paqAComparisonBoundary'], evidence=['illustrative-boundary'], occupiedBases=b, outs=o))
        for k, s, b, o in [('A', '-3/4', [3], 1), ('B', '-1/4', [3], 1), ('C', '1/2', [], 0)]]
    add('paq-a', rank_formula, 'Compare the same base and out state',
        'The target PA has TFS −1/4, with a runner on third and one out immediately before the consequence. Its only illustrative peer in that state has −3/4. A bases-empty PA with no outs is in a different cohort.',
        'Within the two-PA cohort: 100 × (2 × 1 + 1 − 1) / (2 × 1) = 100',
        M.paq_a_population(adjusted, complete_population=True)['B'], 100)
    add('offensive-reach', 'Count distinct trajectories with positive batter-attributed progress.',
        'Two trajectories advance', 'The batter and one existing runner make positive attributed progress. A third runner has no progress. Count each advancing trajectory once, regardless of how far it advances.',
        '1 batter trajectory + 1 runner trajectory = 2',
        calc('offensive-reach', [dict(participant=p, progress36=v) for p, v in [('batter', 18), ('runner', 36), ('held', 0)]]), 2)
    add('hidden-help-rate', 'PAs helping another runner with no batter progress / PAs with no batter progress.',
        'Help in one of two qualifying PAs', 'Across three PAs, two produce no batter progress; one of those helps another runner. The PA with batter progress is outside this denominator.', '1 / 2 = 50%',
        calc('hidden-help-rate', [dict(pa=p, batterProgress36=b, otherProgress36=r) for p, b, r in [('A', 0, 18), ('B', 0, 0), ('C', 9, 0)]]), '1/2')
    add('rally-kill-rate', 'Runner-on-base PAs directly putting an existing runner out / runner-on-base PAs.',
        'One of two opportunities ends a runner’s path', 'One of two runner-on-base PAs directly puts an existing runner out. A third PA starts with empty bases and does not enter the denominator.', '1 / 2 = 50%',
        calc('rally-kill-rate', [dict(pa=p, runnerOnBase=b, existingRunnerOuts=o) for p, b, o in [('A', True, 1), ('B', True, 0), ('C', False, 0)]]), '1/2')
    add('rally-kill-severity', 'Existing-runner destruction / runner-on-base PAs.',
        'A runner from first is put out', 'One of two runner-on-base PAs directly destroys a trajectory beginning at first, costing 1/3. The other costs zero. This isolates destruction from erosion.', '(1/3 + 0) / 2 = 1/6',
        calc('rally-kill-severity', [dict(pa=p, runnerOnBase=True, existingDestruction36=d) for p, d in [('A', 12), ('B', 0)]]), '1/6')
    add('opportunity-erosion', 'Sum of PA opportunity erosion / number of PAs.',
        'Average two erosion amounts', 'Two fully accounted-for PAs have erosion amounts of 1/2 and 1/3. This reports their mean loss of opportunity.', '(1/2 + 1/3) / 2 = 5/12',
        calc('opportunity-erosion', [dict(pa=p, erosion36=e) for p, e in [('A', 18), ('B', 12)]]), '5/12')
    add('empty-game-rate', 'Eligible games with no qualifying positive contribution / games with at least one PA.',
        'A running-only appearance is outside the denominator', 'One game has a PA and no positive contribution; another has a PA and two positive contributions. A third has no PA, so it is ineligible here even though the player can have running statistics.', '1 empty game / 2 eligible games = 50%',
        calc('empty-game-rate', [dict(game=g, plateAppearances=p, positiveEpisodes=e) for g, p, e in [('A', 1, 0), ('B', 1, 2), ('C', 0, 0)]]), '1/2')
    add('empty-game-damage', 'Magnitude of negative TFS + independent runner damage during an Empty Game.',
        'Batting and running damage in one eligible Empty Game', 'Assume the game is completely observed and qualifies as empty. One PA has TFS −1/4; an independent running episode contributes −1/3. Damage reports their positive loss magnitude.', '1/4 + 1/3 = 7/12',
        M.empty_game_damage([M.available(Fraction(-1, 4))], [M.available(Fraction(-1, 3))], empty=True, complete=True), '7/12')
    diversity_formula = '−Σ(channel share × ln(channel share)) / ln(3); each positive play counts once per channel.'
    for title, rows, explanation, equation, expected in [
        ('All three channels used equally', [dict(play='hit', channel='batter_self'), dict(play='hit', channel='batter_other'), dict(play='steal', channel='runner_self')],
         'One hit helps the batter and another runner, so it counts once in each of those channels. A steal adds one runner-to-self play. Diversity describes the mix, not total offensive value.',
         'Shares = 1/3, 1/3, 1/3; normalized diversity = 1', 1.0),
        ('Only one channel used', [dict(play='hit', channel='batter_self')],
         'All positive plays are in the batter-to-self channel. Concentration in one channel gives diversity zero; it does not mean no contribution occurred.',
         'Shares = 1, 0, 0; normalized diversity = 0', 0.0),
    ]:
        add('contribution-path-diversity', diversity_formula, title, explanation, equation, calc('contribution-path-diversity', rows), expected)
    pitches = [dict(pitch=f'illustrative-pitch-{i}', strikesAfter=s, terminal=i == 5) for i, s in enumerate([0, 1, 2, 2, 2, 3])]
    steps = M.recovery_steps(pitches)
    assert M.fraction(steps['value']) == 2
    add('recovery-quality', 'Count later nonterminal pitches after the first two-strike state, then take their reference-population percentile.',
        'Two extra nonterminal pitches', 'Post-pitch strike counts are 0, 1, 2, 2, 2, 3. The pitch reaching two strikes and the terminal pitch are excluded from the extra-pitch count. Assume the complete illustrative two-strike population has counts 0, 2 and 4.',
        '2 extra pitches; the middle of counts 0, 2, 4 has percentile 50.',
        M.percentiles([dict(key=k, score=s) for k, s in [('A', 0), ('B', 2), ('C', 4)]], metric_id='recovery-quality', complete_population=True)['B'], 50)
    defense = [dict(act=a, next=n, agent=p) for a, n, p in [('field', 'throw', 'A'), ('throw', 'catch', 'A'), ('catch', 'tag', 'B'), ('tag', None, 'B')]]
    add('resolution-depth', 'Number of intentional acts on the longest supported precedence path.',
        'Field, throw, catch, tag', 'Assume four distinct intentional acts with supported order: field → throw → catch → tag. Depth counts acts; a single act would have depth one.', '4 acts along the path = depth 4', calc('resolution-depth', defense), 4)
    add('defender-breadth', 'Count distinct defensive agents in the supported resolution structure.',
        'Four acts by two defenders', 'Defender A fields and throws. Defender B catches and tags. Repeated acts by the same player do not add another defender.', 'Distinct defenders {A, B} = 2',
        calc('defender-breadth', [dict(act=r['act'], agent=r['agent']) for r in defense]), 2)
    add('run-construction-depth', 'Count distinct state-changing episodes along the scoring runner’s admitted continuous trajectory.',
        'Single, steal, then score on a double', 'Assume complete continuity for the same runner: a single reaches first, a steal reaches second, and a teammate’s double brings the runner home. These are three separate state-changing episodes.', '1 single + 1 steal + 1 scoring advance = 3 episodes',
        calc('run-construction-depth', [dict(episode=e, changesState=True) for e in ['single', 'steal', 'double']]), 3)
    add('run-construction-breadth', 'Count distinct offensive players whose supported contributions advance the scoring trajectory.',
        'The scorer contributes twice', 'The scorer singles and steals, then a teammate doubles the scorer home. The scorer counts once despite two contributions; the teammate adds one.', 'Distinct contributors {scorer, teammate} = 2',
        calc('run-construction-breadth', [dict(episode=e, supporter=p) for e, p in [('single', 'scorer'), ('steal', 'scorer'), ('double', 'teammate')]]), 2)
    add('adjudication-volatility', 'Overturning dispositions / explicitly resolved mapped reviews.',
        'An unresolved review stays outside the denominator', 'Of three mapped reviews, one overturns, one resolves without overturning, and one remains unresolved. This describes resolved mapped reviews, not all decisions or umpire accuracy.', '1 overturn / 2 resolved reviews = 50%',
        calc('adjudication-volatility', [dict(review=r, resolved=s, reversed=v) for r, s, v in [('A', True, True), ('B', True, False), ('C', False, False)]]), '1/2')
    mechanisms = M.policies()['reviewDependenceMechanisms']
    outcomes = [dict(outcome=f'{m}-{i}', mechanism=m, eligible=True, reviewDependent=i == 0) for m, n in zip(mechanisms, [4, 2]) for i in range(n)]
    dependence = M.review_dependence_by_mechanism(outcomes, complete_populations=dict.fromkeys(mechanisms, True))
    for mechanism, title, size in zip(mechanisms, ['Traditional replay', 'Ball/strike challenges'], [4, 2]):
        add('review-dependence-rate', 'Review-dependent operative outcomes / all review-eligible decisions, separately for each mechanism.',
            title, f'Assume the complete illustrative {title.lower()} population contains {size} eligible decisions and one operative outcome that depends on review. Merely being reviewed does not establish dependence. The two mechanisms are not pooled.',
            f'1 review-dependent outcome / {size} eligible decisions = {100 // size}%', dependence[mechanism], f'1/{size}')
    add('role-realization-breadth', 'Count the distinct realized kinds among Batter, Baserunner, Pitcher and Fielder.',
        'Batting twice and running once', 'Assume a complete player-game role population: two acts realize Batter Role and one realizes Baserunner Role. Count realized kinds once; generic parent roles do not add kinds.', 'Distinct realized kinds {Batter, Baserunner} = 2',
        calc('role-realization-breadth', [dict(act=a, roleType='https://baseballontology.org/' + r) for a, r in [('PA1', 'BatterRole'), ('PA2', 'BatterRole'), ('run', 'BaserunnerRole')]]), 2)
    lexicographic = [dict(key=k, score=s, recovery=r, depth=d, twoStrikeEligible=True, defensiveApplicable=True)
                     for k, s, r, d in [('A', '-3/4', 100, 20), ('B', '3/2', 0, 1), ('C', '3/2', 0, 2)]]
    add('paq-2.1', 'Rank TFS first, Recovery Quality second, and Resolution Depth third; convert that ordering to a percentile.',
        'Process quality breaks a TFS tie', 'Assume all three PAs are eligible: A has (−3/4, 100, 20), B has (3/2, 0, 1), and C has (3/2, 0, 2). A ranks last despite stronger process scores. C beats B only at the third comparison.',
        'Order A < B < C; B receives percentile 50.',
        M.paq21_population(lexicographic, complete_population=True)['B'], 50)
    assert set(examples) == {e['id'] for e in M.catalog()['metrics']}
    # Editorial text is independent of calculation IDs, inputs and answers.
    display = json.loads(PRESENTATION.read_text(encoding='utf-8'))['metrics']
    replacements = [(m['label'], display[m['id']]['label']) for m in M.catalog()['metrics']]
    replacements += [('TFS', display['tfs']['label']), ('trajectory destruction', 'direct loss'),
                     ('opportunity erosion', 'lost opportunity')]
    for entry in examples.values():
        for original, replacement in replacements:
            entry['formula'] = entry['formula'].replace(original, replacement)
            for case in entry['cases']:
                for field in ('title', 'explanation', 'equation'):
                    case[field] = case[field].replace(original, replacement)
    return dict(artifactType='baseballo-illustrative-metric-examples',
                generator='scripts/generate_metric_examples.py',
                notice='Hypothetical inputs checked with the metric calculation code. These are not results from the selected games.',
                metrics=examples)


def guide(payload):
    lines = ['# Worked metric examples', '',
             'Generated by `scripts/generate_metric_examples.py` using the existing metric calculation code.', '',
             payload['notice'], '',
             'In the [local metric page](http://127.0.0.1:4173/metrics), choose a metric and open **How this metric works**. '
             'The scenario selector compares the available examples without changing the selected-game result.', '',
             'These examples assume the stated attribution, continuity and complete illustrative populations. '
             'They do not close the [live evidence gaps](../proposals/graph-native-metric-suite-batch-review/current-release-review.md). '
             'Real season percentiles require the accepted eligible season population, not these small demonstration populations.', '']
    display = json.loads(PRESENTATION.read_text(encoding='utf-8'))['metrics']
    for metric in M.catalog()['metrics']:
        presentation = display[metric['id']]
        entry = payload['metrics'][metric['id']]
        lines.extend([f'## {presentation["label"]}', '', presentation['question'], '',
                      presentation['summary'], '', presentation['reading'], '', entry['formula'], '',
                      f'Reported as: {presentation["unitLabel"]}; {presentation["scopeLabel"]}.', '',
                      f'Technical reference: {metric["label"]} (`{metric["id"]}`). [Calculation kernel](../{metric["authoritativeQuery"]}).', ''])
        for case in entry['cases']:
            lines.extend([f'### {case["title"]}', '', case['explanation'], '', case['equation'], ''])
            if case['result']['status'] == 'unavailable':
                lines.extend(['Result: unavailable; the denominator is zero.', ''])
            elif case['result'].get('value') is None:
                lines.extend([f'Approximate result: {case["result"]["approximateValue"]:.3f}. '
                              'Logarithmic values are approximate; channel counts remain exact.', ''])
    lines.extend(['## Developer verification', '', 'From the Git root:', '',
                  '```powershell', 'python Baseball/scripts/generate_metric_examples.py --check', '```', '',
                  'The check compares every example with an independently specified expected answer and verifies '
                  'that this guide and the browser artifact match the calculations. Regenerate both by omitting `--check`.', ''])
    return '\n'.join(lines).encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    payload = build()
    outputs = {DEST: (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8'), GUIDE: guide(payload)}
    if args.check:
        if any(not path.exists() or path.read_bytes() != content for path, content in outputs.items()):
            raise SystemExit('Metric examples are stale; run scripts/generate_metric_examples.py')
        print('Worked examples for all 20 metrics match their calculations and expected answers.')
    else:
        for path, content in outputs.items():
            path.write_bytes(content)
            print(path)


if __name__ == '__main__':
    main()
