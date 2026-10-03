"""The RML harness counts selected identities and preserves output on failure."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rdflib import Graph, RDF, URIRef
from test_targeted_award_addition import W

ROOT=W.ROOT
sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools


class RmlOutputCounts(unittest.TestCase):
    def test_sparse_event_indexes_and_shared_runner_classification_match_real_rml(self):
        source=ROOT/'data/raw/samples/2026-08-25/822693.json'
        doc=json.loads(source.read_bytes())
        for play in doc['liveData']['plays']['allPlays']:
            if not any(r['details'].get('eventType') in {'passed_ball','wild_pitch'} for r in play['runners']):continue
            for event in play['playEvents']:event['index']+=100
            for key in ('pitchIndex','actionIndex'):
                play[key]=[i+100 for i in play.get(key,[])]
            for runner in play['runners']:runner['details']['playIndex']+=100
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);raw=work/'input.json';raw.write_text(json.dumps(doc),encoding='utf-8')
            context=work/'game-context.json'
            prepared=subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(raw),str(context)],
                capture_output=True,timeout=120)
            self.assertEqual(prepared.returncode,0,prepared.stderr.decode(errors='replace'))
            # Two runners share this wild pitch. Count the process only once.
            document=json.loads(context.read_bytes())
            rows=[r for p in document['liveData']['plays']['allPlays'] for r in p['runners']
                  if r['details'].get('eventType')=='wild_pitch']
            self.assertEqual(len(rows),2)
            self.assertEqual(len({r['_baseballO']['eventPlayId'] for r in rows}),1)
            harness=work/'counts.ps1'
            harness.write_text('''param($Helper, $ContextPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. $Helper
$document = Get-Content -LiteralPath $ContextPath -Raw | ConvertFrom-Json
Get-MlbMappedClassificationCounts -ContextDocument $document | ConvertTo-Json -Compress
''',encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(harness),
                str(ROOT/'scripts/pipeline/rml-output-counts.ps1'),str(context)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            counts=json.loads(result.stdout)
            mapping=work/'classifications.rml.ttl';output=work/'classifications.ttl'
            W.A.subset_mapping('822693',mapping,('PassedBallProcessMap','WildPitchProcessMap','UncaughtThirdStrikeProcessMap'))
            java,mapper=installed_tools()
            result=subprocess.run([str(java),'-Xmx256m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],
                cwd=work,capture_output=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            graph=Graph().parse(output)
            expected={key:len(set(graph.subjects(RDF.type,URIRef('https://baseballontology.org/'+kind))))
                for key,kind in [('passedBalls','PassedBallProcess'),('wildPitches','WildPitchProcess'),
                                 ('uncaughtThirdStrikes','UncaughtThirdStrikeProcess')]}
            self.assertEqual(counts,expected)
            self.assertEqual(counts['wildPitches'],1)

    def test_changed_input_does_not_replace_the_previous_rdf(self):
        text=(ROOT/'scripts/pipeline/run-rml.ps1').read_text()
        start=text.index('    $inputHashAfter =')
        end=text.index('    $manifestPath =',start)
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);input_path=work/'input.json';input_path.write_bytes(b'changed')
            stage=work/'new.ttl';stage.write_bytes(b'new output')
            output=work/'existing.ttl';output.write_bytes(b'previous output')
            script=work/'publish.ps1'
            script.write_text('''param($inputPath, $stageOutput, $outputPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$inputHashBefore = 'original-input-hash'
'''+text[start:end],encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(input_path),str(stage),str(output)],
                capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('changed during RML execution',result.stderr)
            self.assertEqual(output.read_bytes(),b'previous output')


if __name__=='__main__':unittest.main()
