"""Exercise the real NiFi wrapper with busy unrelated admission maintenance."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('powershell'), 'Windows NiFi wrapper')
class TargetedRunnerWorker(unittest.TestCase):
    def test_repair_reaches_its_own_admission_without_running_general_sweep(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);lane=root/'sources/mlb-game/pipeline';lane.mkdir(parents=True)
            infra=root/'scripts/infra';infra.mkdir(parents=True)
            shutil.copyfile(ROOT/'sources/mlb-game/pipeline/targeted-runner-addition.ps1',lane/'worker.ps1')
            (infra/'common.ps1').write_text(r'''
$script:StateRoot=$PSScriptRoot
$script:FusekiHome=$PSScriptRoot
$script:selected=$false
$script:calls=@()
function Get-JavaExecutable { 'java' }
function Get-RMLMapperJar { 'mapper' }
function python {
    $global:LASTEXITCODE=0
    $worker=[IO.Path]::GetFileName($args[1])
    if ($args -contains '--next') {
        if (-not $script:selected) { $script:selected=$true; '{"gamePk":"999"}' }
        else { 'null' }
    }
    elseif ($worker -eq 'admission-evidence-queue.py') {
        if ($args -notcontains '--game-pk') {
            $script:calls+='unrelated'; '{"outcomes":{"refreshed":1}}'
        } else {
            $game=$args[[array]::IndexOf($args,'--game-pk')+1]
            $script:calls+="admission:$game"; '{"outcomes":{"current":1}}'
        }
    } else { $script:calls+='repair:999'; '{"status":"complete"}' }
}
''',encoding='utf-8')
            (lane/'game-lock.ps1').write_text('function Enter-MlbGameLock { [IO.MemoryStream]::new() }')
            (lane/'repair-budget.ps1').write_text('''
function Invoke-MlbRepairBudget {
    param($StateRoot,$Worker,$TimeoutSeconds,[scriptblock]$Action)
    & $Action | Out-Null
    @{ calls=$script:calls; waitSeconds=$TimeoutSeconds } | ConvertTo-Json -Compress
}
''')
            result=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(lane/'worker.ps1')],
                                  capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),dict(calls=['repair:999','admission:999'],waitSeconds=45))


if __name__=='__main__':unittest.main()
