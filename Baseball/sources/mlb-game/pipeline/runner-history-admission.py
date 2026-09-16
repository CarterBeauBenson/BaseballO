"""C1/C3 exact source-selected history SHACL, independent of PA-start admission."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
from rdflib import Graph, Literal

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('c3_batting_support',HERE/'batting-admission.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
CONTEXT=B.module(ROOT/'scripts/pipeline/prepare-rml-context.py','c3_context')
SHAPE=HERE.parent/'shacl/runner-history-admission.ttl'


def fingerprint():
    paths=[Path(__file__),SHAPE,HERE/'batting-admission.py',HERE/'reconcile-metric-source.py',
           ROOT/'scripts/pipeline/prepare-rml-context.py',ROOT/'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix()+':'+B.sha(p.read_bytes()) for p in paths).encode())


def census(raw,game_pk):
    game_pk=B.identity(int(game_pk));doc=json.loads(raw)
    if str(doc['gamePk'])!=game_pk:raise ValueError('Runner-history game identity mismatch')
    history=CONTEXT.personal_runner_histories(raw)
    return dict(gamePk=game_pk,game=B.BASE+'data/game/'+game_pk,sourceSha256=B.sha(raw),
        sourceReconciled=history['sourceConsistency']=='consistent',history=history,
        populationComplete=history['sourceConsistency']=='consistent' and bool(history['halves'])
            and all(h['status']=='reconciled' for h in history['halves']))


def shape_text(source):
    shapes=[];wholes=[]
    prop=lambda path,value:'sh:property [ sh:path '+path+' ; sh:hasValue '+B.iri(value)+' ; sh:minCount 1 ; sh:maxCount 1 ]'
    def node(target,parts):shapes.append('[] a sh:NodeShape ; sh:targetNode '+B.iri(target)+' ; '+' ;\n'.join(parts)+' .')
    for row in source['history']['histories']:
        whole=source['game']+'/runner-trajectory/'+row['lifetimeKey'];wholes.append(whole)
        interval=whole+'/temporal-interval';person=B.BASE+'data/player/'+row['runnerId']
        half=source['game']+'/inning/'+row['inning']+'/'+row['half']
        members=[source['game']+'/runner-episode/'+r['atBatIndex']+'/'+r['runnerIndex'] for r in row['episodes']]
        node(whole,['sh:class obo:BFO_0000015',prop('obo:BFO_0000057',person),
            prop('obo:BFO_0000132',half),prop('obo:BFO_0000199',interval),
            'sh:property [ sh:path obo:BFO_0000117 ; sh:in ('+' '.join(B.iri(m) for m in members)+') ; '
            'sh:minCount '+str(len(members))+' ; sh:maxCount '+str(len(members))+' ]',
            'sh:property [ sh:path cco:ont00001833 ; sh:maxCount 0 ]',
            'sh:property [ sh:path obo:BFO_0000055 ; sh:maxCount 0 ]'])
        node(person,['sh:class cco:ont00001262'])
        node(half,['sh:class base:HalfInning'])
        node(interval,['sh:class obo:BFO_0000038',
            prop('obo:BFO_0000224',row['gameEndInstantIri']) if row.get('gameEndInstantIri') else
            'sh:property [ sh:path obo:BFO_0000224 ; sh:maxCount 0 ]'])
        for member in members:node(member,['sh:class base:RunnerResolutionEpisode'])
    members=', '.join(B.iri(v) for v in wholes) or '<urn:baseballo:no-runner-histories>'
    query=B.PREFIXES+'''SELECT $this WHERE {
      ?whole ?p ?o . FILTER(STRSTARTS(STR(?whole), "'''+source['game']+'''/runner-trajectory/"))
      FILTER(!CONTAINS(STRAFTER(STR(?whole), "/runner-trajectory/"), "/"))
      FILTER(?whole NOT IN ('''+members+'''))
    }'''
    node(source['game'],['sh:sparql [ sh:message "C1/C3 history census has an extra whole" ; sh:select '+Literal(query).n3()+' ]'])
    text=SHAPE.read_text(encoding='utf-8').replace('# __RUNNER_HISTORY_SHAPES__','\n'.join(shapes))
    Graph().parse(data=text,format='turtle')
    return text


def prove(*,raw,game_pk,rdf_path,output,java=None,classpath=None):
    source=census(raw,game_pk);implementation=fingerprint();rdf_sha=B.sha(rdf_path.read_bytes())
    proof=dict(artifactType='baseballo-runner-history-admission',contractVersion=1,
        gamePk=source['gamePk'],graph='https://w3id.org/baseball/graph/game/'+source['gamePk'],
        sourceSha256=source['sourceSha256'],authoritativeRdfSha256=rdf_sha,
        implementationSha256=implementation,status='withheld',sourceReconciled=source['sourceReconciled'],
        graphConforms=False,populationComplete=source['populationComplete'],
        selectedHistories=len(source['history']['histories']),issues=[])
    output.parent.mkdir(parents=True,exist_ok=True)
    source_path=output.with_suffix('.source.json');B.SOURCE.write_atomic(source_path,source)
    proof['sourceCensusSha256']=B.sha(source_path.read_bytes())
    if proof['sourceReconciled']:
        shapes=output.with_suffix('.shapes.ttl');shapes.write_text(shape_text(source),encoding='utf-8',newline='\n')
        if java:
            validator=B.module(ROOT/'scripts/pipeline/validate-shacl.py','c3_history_shacl')
            conforms,report,_=validator.validate_with_jena(data_path=rdf_path.resolve(),shape_path=shapes.resolve(),
                java=java,classpath=classpath,max_heap='384m')
        else:
            from pyshacl import validate
            conforms,report,_=validate(Graph().parse(rdf_path),shacl_graph=Graph().parse(shapes),inference='none',advanced=True)
        report_path=output.with_suffix('.report.ttl');report.serialize(destination=report_path,format='turtle')
        proof.update(graphConforms=bool(conforms),shapeSha256=B.sha(shapes.read_bytes()),
            reportSha256=B.sha(report_path.read_bytes()),engine='jena' if java else 'pyshacl')
        if not conforms:proof['issues'].append(dict(code='SOURCE_GRAPH_CONFORMANCE'))
    else:proof['issues'].append(dict(code='SOURCE_RECONCILIATION'))
    if not proof['populationComplete']:proof['issues'].append(dict(code='INCOMPLETE_PERSONAL_HISTORIES'))
    if proof['sourceReconciled'] and proof['graphConforms'] and proof['populationComplete']:proof['status']='admitted'
    if rdf_sha!=B.sha(rdf_path.read_bytes()) or implementation!=fingerprint():
        raise ValueError('Runner-history admission changed during validation')
    B.SOURCE.write_atomic(output,proof)
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('input','rdf','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--game-pk',required=True)
    parser.add_argument('--java',type=Path);parser.add_argument('--jena-classpath',type=Path)
    args=parser.parse_args()
    if args.java and not args.jena_classpath:parser.error('--java requires --jena-classpath')
    outputs={args.output.resolve(),*(args.output.with_suffix(s).resolve() for s in ('.source.json','.shapes.ttl','.report.ttl'))}
    if outputs & {args.input.resolve(),args.rdf.resolve()}:raise ValueError('History proof cannot overwrite source or RDF')
    raw=args.input.read_bytes()
    result=prove(raw=raw,game_pk=args.game_pk,rdf_path=args.rdf,output=args.output,java=args.java,classpath=args.jena_classpath)
    if raw!=args.input.read_bytes():raise ValueError('History source changed during validation')
    print(json.dumps(result))
    if not result['sourceReconciled'] or not result['graphConforms']:
        raise SystemExit('C1/C3 source/graph SHACL failed; promotion must stop')
