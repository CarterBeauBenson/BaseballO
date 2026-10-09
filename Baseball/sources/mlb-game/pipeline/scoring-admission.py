"""Shared EG4/EG5 conformance for ordinary ingestion and bounded additions."""
import hashlib
import importlib.util
import json
from pathlib import Path
from rdflib import Graph, URIRef

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('scoring_batting_census', HERE/'batting-admission.py')
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
S = B.SCORING
SHAPE = HERE.parent/'shacl/official-scoring.ttl'
MAPS = tuple(name+part+'Map' for name in ('OfficialPA', 'RBICredit')
             for part in ('Judgment', 'Decision', 'Record', 'Rule'))+tuple(
                 'SecondaryError'+part+'Map' for part in ('Process', 'Judgment', 'Decision', 'Record'))+('ErrorRuleMap',)


def select(raw, game_pk):
    document = json.loads(raw)
    if str(document.get('gamePk')) != game_pk:
        raise ValueError('Scoring source game differs')
    census = B.census(raw, game_pk)
    reviewed = lambda play: not B.CONTEXT.accounted_runner_history_reviews(play)['issues']
    return dict(officialPACredits=S.pa_rows(census),
        secondaryErrors=([row for play in document['liveData']['plays']['allPlays']
                         for row in S.secondary_errors(play, game_pk, reviewed(play))]
                         if census['sourceConsistency']=='consistent' else []),
        rbiCredits=S.rbi_rows(document, census, reviewed))


def shapes(selected):
    parts = ['@prefix sh: <http://www.w3.org/ns/shacl#> .']
    iri = lambda value: URIRef(value).n3()
    template = SHAPE.read_text(encoding='utf-8')
    for family in ('officialPACredits', 'rbiCredits', 'secondaryErrors'):
        for row in selected.get(family, []):
            record, judgment, decision = (iri(row[k]) for k in ('record', 'judgment', 'decision'))
            pattern = f'{record} a base:BaseballEventRecord ; cco:ont00001808 {judgment}, {decision} .\n'
            conflicts = f'{{ {judgment} cco:ont00001986 ?extra . FILTER(?extra != {decision}) }}'
            if family == 'secondaryErrors':
                error, resolution = (iri(row[k]) for k in ('error', 'resolution'))
                pattern += f'''{record} cco:ont00001808 {error}, {resolution} .
{resolution} a base:RunnerResolutionProcess .
{error} a base:ErrorProcess ; obo:BFO_0000117 {judgment} .
{judgment} a base:ErrorJudgmentAct ; cco:ont00001921 <{S.BASE}data/rule/error> ; cco:ont00001986 {decision} .
<{S.BASE}data/rule/error> a base:ErrorRule .
{decision} a base:ErrorDecisionICE ; cco:ont00001808 {error} .'''
                conflicts += f' UNION {{ {record} cco:ont00001808 ?extra . ?extra a base:ErrorProcess . FILTER(?extra != {error}) }}'
                contact = row.get('contactPlay')
                if contact:
                    pattern += f'\n{record} cco:ont00001808 {iri(contact)} . {iri(contact)} a base:BattedBallPlayProcess .'
                else:
                    conflicts += f' UNION {{ {record} cco:ont00001808 ?contact . ?contact a base:BattedBallPlayProcess . }}'
                about = [error]
            else:
                subject, player = (iri(row[k]) for k in ('subject', 'player'))
                rule = S.PA_RULE if family == 'officialPACredits' else S.RBI_RULE
                kind = 'PlateAppearance' if family == 'officialPACredits' else 'RunProcess'
                pattern += f'''{judgment} a base:ScoringJudgmentAct ; cco:ont00001921 <{rule}> ; cco:ont00001986 {decision} .
<{rule}> a base:BaseballRule .
{decision} a base:BaseballDecisionICE ; cco:ont00001808 {subject}, {player} .
{subject} a base:{kind} .'''
                conflicts += f''' UNION {{ ?other a base:ScoringJudgmentAct ; cco:ont00001921 <{rule}> ; cco:ont00001986 ?otherDecision .
?otherDecision cco:ont00001808 {subject} . FILTER(?other != {judgment} || ?otherDecision != {decision}) }}'''
                about = [subject, player]
            conflicts += f' UNION {{ {decision} cco:ont00001808 ?extra . FILTER(?extra NOT IN ({", ".join(about)})) }}'
            parts.append(template.replace('__RECORD__', row['record']).replace('__PATTERN__', pattern).replace('__CONFLICTS__', conflicts))
    text = '\n'.join(parts)
    Graph().parse(data=text, format='turtle')
    return text


def validate(raw, game_pk, rdf, output, session, java, classpath):
    selected = select(raw, game_pk)
    shape = output/'official-scoring.shapes.ttl'
    shape.write_text(shapes(selected), encoding='utf-8', newline='\n')
    conforms, report, _ = session.validate_with_jena(data_path=rdf, shape_path=shape,
        java=java, classpath=classpath, max_heap='384m')
    report.serialize(destination=output/'official-scoring.report.ttl', format='turtle')
    sha = lambda data: hashlib.sha256(data).hexdigest()
    receipt = dict(selected=selected, conforms=conforms, sourceSha256=sha(raw),
        authoritativeRdfSha256=sha(rdf.read_bytes()), shapeSha256=sha(shape.read_bytes()))
    (output/'official-scoring.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    if not conforms:
        raise ValueError('EG4/EG5 scoring-decision SHACL failed')
