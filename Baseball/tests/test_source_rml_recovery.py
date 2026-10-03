"""Run the source RML harness with controlled mapper failures and input races."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class SourceRmlRecovery(unittest.TestCase):
    def test_failed_execution_retains_evidence_and_never_replaces_previous_output(self):
        for mode in ('mapper-failure','context-change','mapping-change','success'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);pipeline=root/'scripts/pipeline';pipeline.mkdir(parents=True)
                runner=pipeline/'run-source-rml.ps1';runner.write_bytes((ROOT/'scripts/pipeline/run-source-rml.ps1').read_bytes())
                module=root/'sources/mlb-people';module.mkdir(parents=True)
                mapping=module/'mapping.ttl';mapping.write_text('# original mapping',encoding='utf-8')
                context=root/'context.json';context.write_bytes(b'{"name":"original"}')
                output=root/'prior.ttl';output.write_bytes(b'previous RDF')
                manifest=root/'prior.json';manifest.write_bytes(b'previous manifest')
                common=root/'scripts/infra/common.ps1';common.parent.mkdir(parents=True)
                common.write_text(r'''
$script:RepositoryRoot=$env:TEST_RML_ROOT
$script:StateRoot=Join-Path $script:RepositoryRoot 'state'
function Initialize-LocalLayout {}
function Get-JavaExecutable { 'Invoke-TestMapper' }
function Get-RMLMapperJar { 'mapper.jar' }
function python {
    if ($env:TEST_RML_MODE -eq 'mapping-change') {
        [IO.File]::WriteAllText((Join-Path $script:RepositoryRoot 'sources\mlb-people\mapping.ttl'),'changed mapping')
    }
    $global:LASTEXITCODE=0
}
function Invoke-TestMapper {
    'full mapper diagnostic retained'
    if ($env:TEST_RML_MODE -eq 'mapper-failure') { $global:LASTEXITCODE=17; return }
    $destination=$args[[array]::IndexOf($args,'-o')+1]
    [IO.File]::WriteAllText($destination,'<urn:s> <urn:p> <urn:o> .')
    if ($env:TEST_RML_MODE -eq 'context-change') {
        [IO.File]::WriteAllText((Join-Path $script:RepositoryRoot 'context.json'),'changed context')
    }
    $global:LASTEXITCODE=0
}
function Write-AtomicJsonFile {
    param($Path,$Value,$Depth)
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth $Depth),[Text.UTF8Encoding]::new($false))
}
''',encoding='utf-8')
                env=dict(os.environ,TEST_RML_ROOT=str(root),TEST_RML_MODE=mode)
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(runner),
                    '-ModuleId','mlb-people','-ContextJson',str(context),'-MappingFile',str(mapping),
                    '-MappingContextName','people-context.json','-OutputFile',str(output),'-ManifestFile',str(manifest)],
                    env=env,capture_output=True,text=True,timeout=30)
                quarantine=list((root/'state/pipeline/quarantine/mlb-people/rml').glob('*'))
                self.assertFalse(list((root/'state/pipeline/work/mlb-people').glob('*')))
                if mode=='success':
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertFalse(quarantine)
                    self.assertEqual(json.loads(manifest.read_bytes())['shaclStatus'],'pending')
                    self.assertEqual(output.read_bytes(),b'<urn:s> <urn:p> <urn:o> .')
                else:
                    self.assertNotEqual(result.returncode,0)
                    self.assertEqual(output.read_bytes(),b'previous RDF')
                    self.assertEqual(manifest.read_bytes(),b'previous manifest')
                    self.assertEqual(len(quarantine),1)
                    self.assertEqual((quarantine[0]/'people-context.json').read_bytes(),b'{"name":"original"}')
                    if mode=='mapping-change':
                        self.assertIn('mapping changed before RML execution',result.stderr)
                        self.assertFalse((quarantine[0]/'rmlmapper.log').exists())
                    else:
                        self.assertIn('full mapper diagnostic retained',(quarantine[0]/'rmlmapper.log').read_text(encoding='utf-8-sig'))


if __name__=='__main__':unittest.main()
