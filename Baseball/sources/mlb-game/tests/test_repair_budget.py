"""The NiFi repair slot releases on failure and reports resource deferrals."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]

class RepairBudget(unittest.TestCase):
    def test_reclaims_owned_cache_before_rechecking_full_memory_reserve(self):
        helper=ROOT/'sources/mlb-game/pipeline/repair-budget.ps1'
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);script=state/'check.ps1'
            script.write_text(r'''param($Helper,$State)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. $Helper
$script:freeKB=512*1024
function Get-CimInstance { [pscustomobject]@{FreePhysicalMemory=$script:freeKB} }
function Release-MlbFusekiWorkingSet { $script:freeKB=1200*1024 }
$result=Invoke-MlbRepairBudget -StateRoot $State -Worker 'test' -Action {'reclaimed'}
if ($result -ne 'reclaimed') { throw 'reserve was not rechecked after reclaim' }
$script:freeKB=512*1024
function Release-MlbFusekiWorkingSet {}
$result=Invoke-MlbRepairBudget -StateRoot $State -Worker 'test' -Action {throw 'reserve must remain enforced'}
if (($result | ConvertFrom-Json).reason -ne 'waiting-for-memory') {throw 'reserve was bypassed'}
# A recycled PID must never target a different application.
. $Helper
$script:FusekiState=$State
$script:FusekiHome=$State
Set-Content (Join-Path $State 'fuseki.pid') '123'
function Get-Process {
    $p=[pscustomobject]@{WorkingSet64=2GB}
    $p | Add-Member ScriptMethod Dispose {}
    return $p
}
function Get-CimInstance { [pscustomobject]@{ExecutablePath='another-app.exe';CommandLine='anything'} }
function Get-JavaExecutable {'owned-java.exe'}
Release-MlbFusekiWorkingSet
if ('BaseballO.RepairMemory' -as [type]) {throw 'unrelated process reached native memory call'}
''',encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                str(script),str(helper),str(state)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_admission_maintenance_holds_the_same_lease_as_targeted_repairs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);lane=root/'sources/mlb-game/pipeline';lane.mkdir(parents=True)
            for name in ('refresh-admission-evidence.ps1','repair-budget.ps1'):
                (lane/name).write_bytes((ROOT/'sources/mlb-game/pipeline'/name).read_bytes())
            common=root/'scripts/infra/common.ps1';common.parent.mkdir(parents=True)
            common.write_text("$script:StateRoot=$env:TEST_REPAIR_STATE\n$script:FusekiHome=$script:StateRoot\n"
                "function Get-JavaExecutable {'java'}\n",encoding='utf-8')
            script=root/'check.ps1'
            script.write_text(r'''param($Wrapper,$State)
$ErrorActionPreference='Stop'
$env:TEST_REPAIR_STATE=$State
function Get-CimInstance { [pscustomobject]@{FreePhysicalMemory=1200*1024} }
function python {
    $path=Join-Path $State 'pipeline\work\mlb-game-locks\targeted-repair-budget.lock'
    try {
        $handle=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    } catch [IO.IOException] { $global:LASTEXITCODE=0; 'lease-held'; return }
    $handle.Dispose();throw 'maintenance wrote without the repair lease'
}
$result=& $Wrapper
if ($result -ne 'lease-held') {throw 'maintenance did not invoke its worker'}
''',encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                str(script),str(lane/'refresh-admission-evidence.ps1'),str(root/'state')],
                capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

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
