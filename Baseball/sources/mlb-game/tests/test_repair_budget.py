"""The NiFi repair slot releases on failure and reports resource deferrals."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]

class RepairBudget(unittest.TestCase):
    def test_exclusive_slot_memory_deferral_and_exception_release(self):
        helper=ROOT/'sources/mlb-game/pipeline/repair-budget.ps1'
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);script=state/'check.ps1'
            script.write_text(r"""param($Helper,$State)
$ErrorActionPreference='Stop'
. $Helper
function Get-CimInstance { [pscustomobject]@{FreePhysicalMemory=1200*1024} }
$path=Join-Path $State 'pipeline\work\mlb-game-locks\targeted-repair-budget.lock'
[void](New-Item -ItemType Directory -Force -Path (Split-Path $path))
$held=[IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    $result=Invoke-MlbRepairBudget -StateRoot $State -Worker 'test' -TimeoutSeconds 0 -Action {throw 'must not run'}
    if (($result | ConvertFrom-Json).reason -ne 'repair-slot-busy') {throw 'missing slot deferral'}
} finally {$held.Dispose()}
try {Invoke-MlbRepairBudget -StateRoot $State -Worker 'test' -Action {throw 'stage failure'}}
catch {if ($_.Exception.Message -ne 'stage failure') {throw}}
$result=Invoke-MlbRepairBudget -StateRoot $State -Worker 'test' -TimeoutSeconds 0 -Action {'recovered'}
if ($result -ne 'recovered') {throw 'slot leaked after failure'}
function Get-CimInstance { [pscustomobject]@{FreePhysicalMemory=512*1024} }
$result=Invoke-MlbRepairBudget -StateRoot $State -Worker 'test' -Action {throw 'must not run'}
if (($result | ConvertFrom-Json).reason -ne 'waiting-for-memory') {throw 'missing memory deferral'}
""",encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                str(script),str(helper),str(state)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
