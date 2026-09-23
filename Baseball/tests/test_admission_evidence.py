import importlib.util
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission_evidence',ROOT/'sources/mlb-game/pipeline/admission-evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)


class AdmissionEvidence(unittest.TestCase):
    def test_exact_q5_edit_does_not_change_reused_proof_dependencies(self):
        record=E.read(E.COMPATIBILITY_PATH)
        path=ROOT/record['contextPath']
        old=subprocess.check_output(['git','-C',str(ROOT.parent),'show',
            record['changeCommit']+'^:Baseball/'+record['contextPath']])
        current=path.read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),record['previousContextSha256'])
        self.assertEqual(hashlib.sha256(current).hexdigest(),record['currentContextSha256'])
        before,after=ast.parse(old),ast.parse(current)
        changed=record['changedDefinition']
        # The whole module, including imports and constants, must be identical
        # apart from this one definition. Never infer compatibility by labels.
        def without_changed(tree):
            clone=copy.deepcopy(tree)
            clone.body=[n for n in clone.body if getattr(n,'name',None)!=changed]
            return ast.dump(clone,include_attributes=False)
        self.assertEqual(without_changed(before),without_changed(after))
        definitions={n.name:n for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old_definitions={n.name:n for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertNotEqual(ast.dump(old_definitions[changed]),ast.dump(definitions[changed]))
        for family,entry in record['families'].items():
            adapter=E.module(E.HERE/(family+'-admission.py'),'equivalence_'+family.replace('-','_'))
            self.assertEqual(adapter.fingerprint(),entry['currentImplementationSha256'])
            context_attributes={n.attr for n in ast.walk(ast.parse(Path(adapter.__file__).read_text()))
                if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='CONTEXT'}
            self.assertEqual(context_attributes,set(entry['contextDefinitions']))
            visited=set();pending=list(context_attributes & definitions.keys())
            while pending:
                name=pending.pop()
                if name in visited:continue
                visited.add(name)
                nodes=list(ast.walk(definitions[name]))
                self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                    and n.func.id in {'eval','exec','getattr','globals','locals','__import__','module'} for n in nodes))
                pending.extend({n.id for n in nodes if isinstance(n,ast.Name)} & definitions.keys()-visited)
            self.assertNotIn(changed,visited,family)
            common=[E.HERE/'batting-admission.py',E.HERE/'reconcile-metric-source.py',ROOT/'scripts/pipeline/validate-shacl.py']
            paths=([Path(adapter.__file__),adapter.SHAPE,path,*common] if family=='runner-resolution' else
                [Path(adapter.__file__),adapter.SHAPE,*common[:2],path,common[2]])
            prior=hashlib.sha256('\n'.join(p.relative_to(ROOT).as_posix()+':'+
                (record['previousContextSha256'] if p==path else E.sha(p)) for p in paths).encode()).hexdigest()
            self.assertEqual(prior,entry['previousImplementationSha256'])
        self.assertNotIn('runner-boundary',record['families'])

    def test_equivalent_code_reuses_exact_proof_without_changing_its_outcome_or_fingerprint(self):
        record=E.read(E.COMPATIBILITY_PATH)
        for family,status in [('runner-resolution','admitted'),('pitch-count','withheld'),('defensive','withheld')]:
            with self.subTest(family=family),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run'/f'{family}.json'
                entry=record['families'][family]
                proof=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,
                    status=status,gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',graph='graph',
                    implementationSha256=entry['previousImplementationSha256'],sourceReconciled=True,graphConforms=True,
                    issues=[] if status=='admitted' else [dict(code='ORIGINAL_WITHHELD_REASON')])
                for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
                    E.atomic(path.with_suffix(suffix),dict(retained=key));proof[key]=E.sha(path.with_suffix(suffix))
                E.atomic(path,proof);original=path.read_bytes()
                marker=state/'promotion.json';field=E.FIELDS[family]
                E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                    promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
                adapter=SimpleNamespace(fingerprint=lambda:entry['currentImplementationSha256'],
                    promoted_admission=lambda *args:{'status':'withheld'})
                result=E.load(adapter,state,promotion,family)
                self.assertEqual({key:result[key] for key in proof},proof)
                self.assertEqual(path.read_bytes(),original)
                self.assertEqual(result['implementationReuse']['currentImplementationSha256'],adapter.fingerprint())
                self.assertEqual(E.diagnostic(state,promotion,family,adapter.fingerprint())['evidenceState'],'implementation-compatible')
                self.assertIsNone(E.compatible_proof(state,{**promotion,'rawSha256':'different'},family,adapter.fingerprint()))
                self.assertIsNone(E.compatible_proof(state,promotion,family,'unrecognized-next-version'))
                if family=='defensive':
                    invalid={**proof,'status':'admitted','populationComplete':False}
                    E.atomic(path,invalid);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                    invalid_promotion={**promotion,'promotionManifestSha256':E.sha(marker)}
                    with self.assertRaisesRegex(ValueError,'conformance evidence'):
                        E.load(adapter,state,invalid_promotion,family)
                    E.atomic(path,proof);E.atomic(marker,{field:str(path),field+'Sha256':E.sha(path)})
                path.with_suffix('.report.ttl').write_text('changed report')
                with self.assertRaisesRegex(ValueError,'artifact changed'):E.load(adapter,state,promotion,family)

    def test_stale_previously_withheld_is_preserved_and_never_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/evidence/mlb-game/1/run/defensive.json'
            proof=dict(status='withheld',gamePk='1',sourceSha256='source',authoritativeRdfSha256='rdf',
                implementationSha256='old',issues=[dict(code='INCOMPLETE_DEFENSIVE_POPULATION')])
            E.atomic(path,proof)
            marker=state/'promotion.json';E.atomic(marker,dict(defensiveAdmission=str(path),defensiveAdmissionSha256=E.sha(path)))
            promotion=dict(gamePk='1',rawSha256='source',authoritativeRdfSha256='rdf',authoritativeGraph='graph',
                promotionManifest=str(marker),promotionManifestSha256=E.sha(marker))
            result=E.diagnostic(state,promotion,'defensive','current')
            self.assertEqual((result['evidenceState'],result['previousStatus']),('implementation-stale','withheld'))
            self.assertEqual(result['previousIssues'],proof['issues'])
            adapter=SimpleNamespace(fingerprint=lambda:'current',promoted_admission=lambda *args:{'status':'withheld'})
            self.assertEqual(E.load(adapter,state,promotion,'defensive'),{'status':'withheld'})
            # A separately produced current proof still must match the exact graph,
            # source, implementation, promotion and retained artifacts.
            target=E.refresh_path(state,promotion,'defensive','current')
            E.atomic(target,{**proof,'artifactType':'baseballo-defensive-admission','contractVersion':1,
                'graph':'graph','implementationSha256':'current'})
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            self.assertEqual(E.load(adapter,state,promotion,'defensive')['issues'],proof['issues'])
            changed=E.read(target);changed['sourceSha256']='another-input';E.atomic(target,changed)
            E.atomic(target.with_suffix('.receipt.json'),dict(promotionManifestSha256=E.sha(marker),proofSha256=E.sha(target)))
            with self.assertRaisesRegex(ValueError,'different inputs'):E.load(adapter,state,promotion,'defensive')


if __name__=='__main__':unittest.main()
