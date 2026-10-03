function Get-MlbMappedClassificationCounts {
    param([Parameter(Mandatory = $true)][object] $ContextDocument)

    # Count the identifiers already selected for the unchanged RML sources.
    # MLB event indexes are identifiers, not offsets into playEvents.
    $passed = [System.Collections.Generic.HashSet[string]]::new()
    $wild = [System.Collections.Generic.HashSet[string]]::new()
    $uncaught = 0
    foreach ($play in $ContextDocument.liveData.plays.allPlays) {
        $flag = $play._baseballO.PSObject.Properties['isUncaughtThirdStrike']
        if ($null -ne $flag -and $flag.Value -eq $true) { $uncaught++ }
        foreach ($runner in @($play.runners)) {
            $kind = $runner.details.PSObject.Properties['eventType']
            if ($null -eq $kind -or $kind.Value -notin @('passed_ball', 'wild_pitch')) { continue }
            $id = [string]$runner._baseballO.eventPlayId
            if ([string]::IsNullOrWhiteSpace($id)) {
                throw 'Selected pitch classification has no RML event identifier.'
            }
            if ($kind.Value -eq 'passed_ball') { [void]$passed.Add($id) }
            else { [void]$wild.Add($id) }
        }
    }
    return @{passedBalls=$passed.Count; wildPitches=$wild.Count; uncaughtThirdStrikes=$uncaught}
}
