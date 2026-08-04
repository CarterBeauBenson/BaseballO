# Data

`raw/` contains untouched MLB `feed/live` responses used for development. The
older checked-in fixture is game `566279`. The active audit corpus under
`raw/samples/2026-08-03/` contains the original schedule response plus eight
completed game feeds: `822867`, `823431`, `823520`, `823757`, `824160`,
`824324`, `824647`, and `825095`.

The schedule is acquisition metadata, not an RML input. Raw game and schedule
bytes are immutable; statistics, completeness decisions, RDF, and query-index
facts are all derived downstream.

The active RML mapping expects its runtime input to be named `game.json`; keep that runtime copy local under `mappings/direct/`. Do not add helper fields or overwrite the authoritative raw response.

To exercise the active local pipeline, copy a completed-game JSON file into the manual inbox shown by:

```powershell
.\scripts\infra\configure-nifi-games-manual.ps1 -Enable
```

The checked-in sample may also be imported directly with
`scripts/pipeline/import-game-json.ps1`; neither path downloads data. External
MLB acquisition remains parked while source authorization is unresolved.
