# Data

`raw/` contains untouched MLB `feed/live` responses used for development. The
older checked-in fixture is game `566279`. The dated sample corpus contains 24
schedule responses and 288 distinct completed game feeds with authoritative
official dates from 2026-07-14 through 2026-08-06. The 2026-07-15 schedule has
no completed games. Games repeated by the schedule API on adjacent dates are
stored once under the feed's `gameData.datetime.officialDate`.

The original eight-game 2026-08-03 directory remains the accepted audit and
benchmark subset. Its raw files were preserved when that date was reacquired;
newer content-addressed MLB response variants remain in managed local state
rather than overwriting the checked-in evidence.

The schedule is acquisition metadata, not an RML input. Raw game and schedule
bytes are immutable; statistics, completeness decisions, RDF, and query-index
facts are all derived downstream.

The active RML mapping expects its runtime input to be named `game.json`; keep that runtime copy local under `mappings/direct/`. Do not add helper fields or overwrite the authoritative raw response.

To exercise the active local pipeline, copy a completed-game JSON file into the manual inbox shown by:

```powershell
.\scripts\infra\configure-nifi-games-manual.ps1 -Enable
```

The checked-in samples may also be imported directly with
`scripts/pipeline/import-game-json.ps1`; neither manual path downloads data.
External MLB acquisition is available only when a caller explicitly supplies
`-ExternalDataAccessApproved`. No unattended acquisition schedule is enabled.
