# Data

Run project-relative commands in this document from the `Baseball/` project
directory.

`raw/` contains untouched MLB `feed/live` responses used for development. The
older checked-in fixture is game `566279`. The dated sample corpus contains 43
schedule responses and 546 distinct completed game feeds with authoritative
official dates from 2026-07-14 through 2026-08-25. The 2026-07-15 schedule has
no completed games. Games repeated by the schedule API on adjacent dates are
stored once under the feed's `gameData.datetime.officialDate`.

The original eight-game 2026-08-03 directory remains the accepted audit and
benchmark subset. Its raw files were preserved when that date was reacquired;
newer content-addressed MLB response variants remain in managed local state
rather than overwriting the checked-in evidence.

The schedule is acquisition metadata, not an RML input. Raw game and schedule
bytes are immutable; statistics, completeness decisions, RDF, and query-index
facts are all derived downstream.

This checked-in corpus is the bounded historical evidence set. Future MLB API
runs do not extend it by default. New schedule responses are deleted after
candidate selection, and exact game responses are retained only until NiFi
successfully promotes both the authoritative and query-index graphs. Compact
hashes, manifests, and failure evidence remain available for audit and retry.

The active RML mapping expects its isolated runtime input to be named `game.json`; keep that disposable copy outside the repository. Do not add helper fields or overwrite the authoritative raw response.

The clean NiFi runtime acquires API payloads through seven independent
source-owned lanes. Provisioning and proof commands are listed in the
[NiFi runbook](../infra/nifi/README.md). A one-game proof can be submitted from
the repository root with:

```powershell
.\Baseball\sources\mlb-game\nifi\provision.ps1 -RunProof -ProofGamePk 566279
```

The checked-in samples may still be imported directly with
`scripts/pipeline/import-game-json.ps1` as a developer fallback; that command
does not download data and is not an active NiFi inbox. Submit an admitted
season-to-date acquisition without reprovisioning the flow with:

```powershell
.\Baseball\scripts\infra\submit-nifi-corpus.ps1 -Module all
```

Runtime API payloads are transient. The Game lane deletes them after
authoritative/index promotion and the applicable immediate or deferred batch
materialization gate. Reference and transaction lanes delete them after their
source-owned authoritative promotion and cleanup gate. Bounded failures retain
their inputs in source-local quarantine.
