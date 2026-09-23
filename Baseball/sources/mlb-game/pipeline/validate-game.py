"""Run the existing source profiles with one Jena data-graph load per game."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
VALIDATOR=ROOT/'scripts/pipeline/validate-shacl.py'


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def validate(args):
    batch=module(ROOT/'scripts/pipeline/jena_session.py','mlb_jena_session')
    raw=args.input.read_bytes(); rdf_hash=hashlib.sha256(args.rdf.read_bytes()).hexdigest()
    args.output.mkdir(parents=True,exist_ok=True)
    with batch.Session(args.rdf,args.java,args.jena_classpath) as session:
        conforms,report,_=session.validate_with_jena(data_path=args.rdf,
            shape_path=HERE.parent/'shacl/authoritative.ttl',java=args.java,classpath=args.jena_classpath,max_heap='384m')
        report.serialize(destination=args.output/'authoritative.report.ttl',format='turtle')
        if not conforms: raise ValueError('Authoritative SHACL failed')
        for name in ('clock','runner-history','defensive','pitch-count','runner-boundary',
                     'runner-resolution','scoring-run','contact-continuation','batting'):
            producer=module(HERE/(name+'-admission.py'),'mlb_suite_'+name.replace('-','_'))
            owner=getattr(producer,'B',producer)
            loader=owner.module
            # The producer retains its unchanged census, shapes, stop conditions
            # and report serialization. Inject only the Jena execution transport.
            owner.module=lambda path,label,load=loader: (session if Path(path).resolve()==VALIDATOR.resolve() else load(path,label))
            proof=producer.prove(raw=raw,game_pk=args.game_pk,rdf_path=args.rdf,
                output=args.output/(name+'-admission.json'),java=args.java,classpath=args.jena_classpath)
            if name=='clock' and proof['status']!='admitted': raise ValueError('T1 clock source/graph conformance failed')
            if name=='runner-history' and not proof['promotionAllowed']: raise ValueError('C1/C3 source/graph conformance failed')
            if name=='contact-continuation' and not proof['conforms']: raise ValueError('B2 contact continuation SHACL failed')
        review=module(HERE/'review-inventory.py','mlb_suite_reviews')
        review_record=review.inventory(raw,args.game_pk)
        (args.output/'review-inventory.json').write_text(json.dumps(review_record,indent=2)+'\n',encoding='utf-8')
        if args.input.read_bytes()!=raw or hashlib.sha256(args.rdf.read_bytes()).hexdigest()!=rdf_hash:
            raise ValueError('Source or RDF changed during source validation')
        execution=dict(artifactType='baseballo-mlb-shacl-execution',dataGraphLoads=1,dataTriples=session.data_count,
            authoritativeRdfSha256=rdf_hash,profiles=session.timings,
            executorSha256=hashlib.sha256(Path(__file__).read_bytes()+Path(batch.__file__).read_bytes()+
                (ROOT/'scripts/pipeline/ShaclSession.java').read_bytes()).hexdigest())
        (args.output/'shacl-execution.json').write_text(json.dumps(execution,indent=2)+'\n',encoding='utf-8')
        return execution


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ('input','rdf','output','java','jena-classpath'): parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--game-pk',required=True)
    print(json.dumps(validate(parser.parse_args())))
