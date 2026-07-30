# Data

`raw/` contains untouched MLB `feed/live` responses used for development. The checked-in sample is game `566279`.

The active RML mapping expects its runtime input to be named `game.json`; keep that runtime copy local under `mappings/direct/`. Do not add helper fields or overwrite the authoritative raw response.

To exercise the active local pipeline, copy a completed-game JSON file into the manual inbox shown by:

```powershell
.\scripts\infra\configure-nifi-games-manual.ps1 -Enable
```

The checked-in sample may also be imported directly with `scripts/pipeline/import-game-json.ps1`; neither path downloads data.
