"""Generate the canonical admitted-binding SPARQL kernels and their catalog.

Developer code generation; routine evidence extraction/materialization belongs
to the existing NiFi serving consumer. Run with --check for a focused drift check.
"""
from pathlib import Path
import argparse
import json
from fractions import Fraction
from math import lcm

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'sparql/metrics'

DEFINITIONS = [
    ('tfs', 'Trajectory Fulfillment Score', 'trajectory-fulfillment-score', 'plate_appearance', 'better', 'trajectory fraction',
     'Attributed progress minus trajectory destruction and opportunity erosion.', ['ATTRIBUTION', 'BOUNDARY_STATE', 'PATH_IDENTITY', 'OPERATIVE_OUTS', 'COMPLETENESS']),
    ('paq-2', 'Plate Appearance Quality', 'paq-2-core', 'plate_appearance', 'better', 'percentile',
     'Season-relative percentile of exact TFS, with tied values receiving the same midrank.', ['TFS', 'REFERENCE_POPULATION']),
    ('paq-a', 'Opportunity-Adjusted PAQ', 'paq-a', 'plate_appearance', 'better', 'percentile',
     'PAQ compared with plate appearances having the same occupied bases and out count immediately before the batter consequence.', ['TFS', 'REFERENCE_POPULATION', 'PAQ_A_STATE']),
    ('offensive-reach', 'Offensive Reach', 'offensive-reach', 'plate_appearance', 'better', 'trajectories',
     'Distinct offensive trajectories receiving positive batter-attributed progress.', ['ATTRIBUTION', 'PATH_IDENTITY', 'COMPLETENESS']),
    ('hidden-help-rate', 'Hidden Help Rate', 'hidden-help-rate', 'player', 'better', 'proportion',
     'Among PAs with no batter progress, the proportion producing positive progress for another runner.', ['ATTRIBUTION', 'PATH_IDENTITY', 'COMPLETENESS']),
    ('rally-kill-rate', 'Rally Kill Rate', 'rally-kill-rate', 'player', 'worse', 'proportion',
     'Among runner-on-base PAs, the proportion directly putting an existing runner out.', ['ATTRIBUTION', 'BOUNDARY_STATE', 'OPERATIVE_OUTS', 'COMPLETENESS']),
    ('rally-kill-severity', 'Rally Kill Severity', 'rally-kill-severity', 'player', 'worse', 'trajectory fraction',
     'Existing-runner trajectory destruction per runner-on-base plate appearance.', ['ATTRIBUTION', 'BOUNDARY_STATE', 'PATH_IDENTITY', 'OPERATIVE_OUTS', 'COMPLETENESS']),
    ('opportunity-erosion', 'Opportunity Erosion', 'opportunity-erosion', 'player', 'worse', 'trajectory fraction',
     'Mean loss of remaining offensive opportunity from attributed outs; also exposed per PA within TFS.', ['BOUNDARY_STATE', 'OPERATIVE_OUTS', 'COMPLETENESS']),
    ('empty-game-rate', 'Empty Game Rate', 'empty-game-rate', 'player', 'worse', 'proportion',
     'Games with at least one PA and no qualifying positive contribution, divided by games with at least one PA.', ['OFFENSIVE_ELIGIBILITY', 'INDEPENDENT_EPISODES', 'COMPLETENESS']),
    ('empty-game-damage', 'Empty Game Damage', 'empty-game-damage', 'player_game', 'worse', 'trajectory fraction',
     'Sum of negative TFS and approved independent trajectory damage during an Empty Game.', ['TFS', 'OFFENSIVE_ELIGIBILITY', 'INDEPENDENT_EPISODES', 'INDEPENDENT_SCORE', 'COMPLETENESS']),
    ('contribution-path-diversity', 'Contribution Path Diversity', 'contribution-path-diversity', 'player', 'descriptive', 'normalized entropy',
     'Normalized Shannon diversity across batter-to-self, batter-to-other and independent runner-to-self channels, counting each positive play once per channel.', ['ATTRIBUTION', 'INDEPENDENT_EPISODES', 'CHANNEL_EPISODES', 'COMPLETENESS']),
    ('recovery-quality', 'Recovery Quality', 'recovery-quality', 'plate_appearance', 'better process quality', 'percentile',
     'Percentile of nonterminal pitches after the first two-strike state, among two-strike PAs.', ['EXACT_PITCH_COUNTS', 'REFERENCE_POPULATION']),
    ('resolution-depth', 'Defensive Resolution Depth', 'resolution-depth', 'batted_play', 'descriptive', 'acts',
     'Longest precedence path measured in intentional defensive acts; a single act has depth one.', ['DEFENSIVE_ACTS', 'DEFENSIVE_ORDER']),
    ('defender-breadth', 'Defender Breadth', 'defender-breadth', 'batted_play', 'descriptive', 'players',
     'Distinct defensive agents in the admitted defensive resolution structure.', ['DEFENSIVE_ACTS']),
    ('run-construction-depth', 'Run Construction Depth', 'run-construction-depth', 'run', 'descriptive', 'episodes',
     'Distinct state-changing episodes on the scoring runner\'s admitted continuous trajectory.', ['RUN_CONTINUITY', 'PATH_IDENTITY']),
    ('run-construction-breadth', 'Run Construction Breadth', 'run-construction-breadth', 'run', 'descriptive', 'players',
     'Distinct offensive players whose admitted contributions advance the scoring trajectory, including the scoring runner.', ['RUN_CONTINUITY', 'SUPPORT_ATTRIBUTION']),
    ('adjudication-volatility', 'Adjudication Volatility', 'adjudication-volatility', 'review_population', 'descriptive', 'proportion',
     'Overturning dispositions divided by explicitly resolved replay reviews in the selected mapped population.', []),
    ('review-dependence-rate', 'Review Dependence Rate', 'review-dependence-rate', 'outcome_population', 'descriptive', 'proportion',
     'Review-dependent operative outcomes divided by all review-eligible decisions in the declared population, with traditional replay and ball/strike challenges reported separately.', ['OPERATIVE_REVIEW', 'OUTCOME_POPULATION']),
    ('role-realization-breadth', 'Role Realization Breadth', 'role-realization-breadth', 'player_game', 'descriptive', 'role types',
     'Distinct Batter, Baserunner, Pitcher and Fielder role kinds actually realized in the player-game, without counting generic parent roles again.', ['DEFENSIVE_ACTS', 'ROLE_POPULATION']),
    ('paq-2.1', 'PAQ with Process Tie-Breakers', 'paq-2-1', 'plate_appearance', 'better', 'percentile',
     'Lexicographic percentile: TFS, then Recovery Quality, then Resolution Depth; only PAs with applicable recovery and defensive resolution enter this reference population.', ['TFS', 'EXACT_PITCH_COUNTS', 'DEFENSIVE_ACTS', 'DEFENSIVE_ORDER', 'REFERENCE_POPULATION', 'PAQ21_ELIGIBILITY']),
]


def query(columns, projection, body='', group='GROUP BY ?key', peer=False):
    values = '  VALUES (' + ' '.join('?' + c for c in columns) + ') {\n    # INPUT_ROWS\n  }\n'
    if peer:
        values += '  VALUES (' + ' '.join('?peer' + c[0].upper() + c[1:] for c in columns) + ') {\n    # PEER_ROWS\n  }\n'
    return ('# Generated by scripts/generate_metric_suite.py.\n'
            '# Calculation on admitted SPARQL bindings; not a source-evidence admission rule.\n'
            'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n'
            f'SELECT {projection}\nWHERE {{\n{values}{body}\n}}\n{group}\n').rstrip() + '\n'


def kernels():
    result = {}
    def add(id, columns, identity, projection, body='', group='GROUP BY ?key', **kw):
        result[id] = dict(inputColumns=columns.split(), rowIdentity=identity.split(),
                          source=query(columns.split(), projection, body, group, **kw))
    add('tfs', 'key participant start end terminal creditProgress creditOut outsBefore attributedOuts', 'key participant',
        '?key (SUM(?p36) AS ?progress) (SUM(?d36) AS ?destruction) (SUM(?e36) AS ?erosion) '
        '(SUM(?p36-?d36-?e36) AS ?numerator) (36 AS ?denominator)',
        '''  BIND(IF((?terminal="safe" || ?terminal="scored") && ?creditProgress && ?end>?start,
    xsd:integer(36*(?end-?start)/(4-?start)),0) AS ?p36)
  BIND(IF(?terminal="out" && ?creditOut,xsd:integer(36/(4-?start)),0) AS ?d36)
  BIND(IF(?terminal="safe" || ?terminal="stranded",
    xsd:integer(36*?attributedOuts/((4-?end)*(3-?outsBefore))),0) AS ?e36)''')
    for id in ['paq-2', 'paq-a', 'recovery-quality', 'paq-2.1']:
        columns = 'key cohort scoreN scoreD'
        equal = '?scoreN*?peerScoreD=?peerScoreN*?scoreD'
        less = '?peerScoreN*?scoreD<?scoreN*?peerScoreD'
        if id == 'paq-2.1':
            columns += ' recoveryN recoveryD depth'
            rec_equal = '?recoveryN*?peerRecoveryD=?peerRecoveryN*?recoveryD'
            rec_less = '?peerRecoveryN*?recoveryD<?recoveryN*?peerRecoveryD'
            less = f'({less}) || (({equal}) && (({rec_less}) || (({rec_equal}) && ?peerDepth<?depth)))'
            equal = f'({equal}) && ({rec_equal}) && ?depth=?peerDepth'
        add(id, columns, 'key', '?key (SUM(?lower) AS ?lower) (SUM(?tie) AS ?ties) '
            '(COUNT(?peerKey) AS ?population) '
            '(100*(2*SUM(?lower)+SUM(?tie)-1) AS ?numerator) '
            '(2*(COUNT(?peerKey)-1) AS ?denominator)',
            f'  FILTER(?cohort=?peerCohort)\n  BIND(IF({less},1,0) AS ?lower)\n  BIND(IF({equal},1,0) AS ?tie)', peer=True)
    add('offensive-reach', 'key participant progress36', 'key participant',
        '?key (SUM(IF(?progress36>0,1,0)) AS ?numerator) (1 AS ?denominator)')
    add('hidden-help-rate', 'key pa batterProgress36 otherProgress36', 'key pa',
        '?key (SUM(IF(?batterProgress36=0 && ?otherProgress36>0,1,0)) AS ?numerator) '
        '(SUM(IF(?batterProgress36=0,1,0)) AS ?denominator)')
    add('rally-kill-rate', 'key pa runnerOnBase existingRunnerOuts', 'key pa',
        '?key (SUM(IF(?runnerOnBase && ?existingRunnerOuts>0,1,0)) AS ?numerator) '
        '(SUM(IF(?runnerOnBase,1,0)) AS ?denominator)')
    add('rally-kill-severity', 'key pa runnerOnBase existingDestruction36', 'key pa',
        '?key (SUM(IF(?runnerOnBase,?existingDestruction36,0)) AS ?numerator) '
        '(36*SUM(IF(?runnerOnBase,1,0)) AS ?denominator)')
    add('opportunity-erosion', 'key pa erosion36', 'key pa',
        '?key (SUM(?erosion36) AS ?numerator) (36*COUNT(?pa) AS ?denominator)')
    add('empty-game-rate', 'key game plateAppearances positiveEpisodes', 'key game',
        '?key (SUM(IF(?plateAppearances>0 && ?positiveEpisodes=0,1,0)) AS ?numerator) '
        '(SUM(IF(?plateAppearances>0,1,0)) AS ?denominator)')
    add('empty-game-damage', 'key game episode empty score36', 'key episode',
        '?key (SUM(IF(?score36<0,-?score36,0)) AS ?numerator) (36 AS ?denominator)',
        '  FILTER(?empty)')
    add('contribution-path-diversity', 'key play channel', 'key play channel',
        '?key (SUM(IF(?channel="batter_self",1,0)) AS ?self) '
        '(SUM(IF(?channel="batter_other",1,0)) AS ?other) '
        '(SUM(IF(?channel="runner_self",1,0)) AS ?running)')
    add('resolution-depth', 'key act next agent', 'key act next',
        'DISTINCT ?key ?act ?next ?agent', group='')
    add('defender-breadth', 'key act agent', 'key act agent',
        '?key (COUNT(DISTINCT ?agent) AS ?numerator) (1 AS ?denominator)')
    add('run-construction-depth', 'key episode changesState', 'key episode',
        '?key (SUM(IF(?changesState,1,0)) AS ?numerator) (1 AS ?denominator)')
    add('run-construction-breadth', 'key episode supporter', 'key episode supporter',
        '?key (COUNT(DISTINCT ?supporter) AS ?numerator) (1 AS ?denominator)')
    add('adjudication-volatility', 'key review resolved reversed', 'key review',
        '?key (SUM(IF(?resolved && ?reversed,1,0)) AS ?numerator) '
        '(SUM(IF(?resolved,1,0)) AS ?denominator)')
    add('review-dependence-rate', 'key outcome eligible reviewed', 'key outcome',
        '?key (SUM(IF(?eligible && ?reviewed,1,0)) AS ?numerator) '
        '(SUM(IF(?eligible,1,0)) AS ?denominator)')
    roles = json.loads((DEST / 'batch-release-policy.json').read_text(encoding='utf-8'))['countedRoleTypes']
    add('role-realization-breadth', 'key act roleType', 'key act roleType',
        '?key (COUNT(DISTINCT ?roleType) AS ?numerator) (1 AS ?denominator)',
        '  FILTER(?roleType IN (' + ','.join(json.dumps(role) for role in roles) + '))')
    return result


def artifacts():
    outputs, entries = {}, []
    all_kernels = kernels()
    for id, label, filename, grain, higher, unit, definition, requires in DEFINITIONS:
        kernel = all_kernels[id]
        path = f'sparql/serving/metric-kernels/{filename}.rq'
        outputs[ROOT / path] = kernel['source']
        entries.append(dict(id=id, label=label, version='2.1.1' if id=='paq-2.1' else '2.0.2' if id in {'paq-a','review-dependence-rate'} else '2.0.1' if id in {'empty-game-rate','contribution-path-diversity','run-construction-breadth','role-realization-breadth'} else '2.0.0',
                            grain=grain, higherIs=higher, unit=unit, userDefinition=definition,
                            semanticMode='completeness-gated', authoritativeQuery=path,
                            executionMode='admitted-binding-kernel', sourceScopeVersion=1,
                            completenessProfileVersion='pending-batch-review', contributionProfileVersion='2026-09-08',
                            requires=requires, implementationStatus='implemented',
                            liveAdapter='resolved-review-dispositions' if id=='adjudication-volatility' else 'blocked-by-gap-register',
                            referencePopulation=('eligible MLB regular-season two-strike PAs in selected season through reporting cutoff' if id=='recovery-quality' else 'eligible MLB regular-season PAs with applicable recovery and defensive resolution through reporting cutoff' if id=='paq-2.1' else 'eligible MLB regular-season PAs in selected season through reporting cutoff' if id.startswith('paq') else 'declared selected evidence population'),
                            nullableColumns=['end'] if id=='tfs' else ['next'] if id=='resolution-depth' else [],
                            inputColumns=kernel['inputColumns'], rowIdentity=kernel['rowIdentity']))
    weights = json.loads((DEST / 'batch-release-policy.json').read_text())['independentPositiveWeights']
    fractions = {int(k.split('-')[0]): Fraction(int(v['numerator']), int(v['denominator'])) for k,v in weights.items()}
    denominator = lcm(*(f.denominator for f in fractions.values()))
    terms = [f'IF(?start<={start} && ?end>{start},{int(value*denominator)},0)' for start,value in sorted(fractions.items())]
    component_path = 'sparql/serving/metric-kernels/independent-runner-advancement.rq'
    columns = ['key','participant','start','end','terminal','creditProgress']
    outputs[ROOT / component_path] = query(columns,
        f'?key (SUM(?gain) AS ?numerator) ({denominator} AS ?denominator)',
        '  BIND(IF((?terminal="safe" || ?terminal="scored") && ?creditProgress, '
        + '+'.join(terms) + ', 0) AS ?gain)')
    components = [dict(id='independent-runner-advancement', authoritativeQuery=component_path,
                       inputColumns=columns, rowIdentity=['key','participant'],
                       executionMode='admitted-binding-kernel', liveAdapter='blocked-by-gap-register')]
    outputs[DEST / 'metric-catalog.json'] = json.dumps(dict(
        artifactType='baseballo-graph-native-metric-catalog', contractVersion=1,
        generator='scripts/generate_metric_suite.py', metricVersion='2.0.2',
        metrics=entries, components=components), indent=2)+'\n'
    return outputs


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args=parser.parse_args()
    bad=[]
    for path, text in artifacts().items():
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8')!=text: bad.append(path.name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode('utf-8'))
    if bad: raise SystemExit('Metric generation drift: '+', '.join(bad))
    print(('Verified' if args.check else 'Generated')+' 20 metric kernels, independent-advancement component and catalog.')


if __name__=='__main__': main()
