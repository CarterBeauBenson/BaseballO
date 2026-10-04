# Data

This is the checked-in evidence inventory. Runtime acquisition and cleanup are
owned by the [NiFi source lanes](../infra/nifi/README.md).

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

Raw schedules supply acquisition metadata. Their compact, validated revision
evidence can also support the accepted postponement mapping; raw schedules are
not passed directly to the game RML. Raw game and schedule bytes are immutable;
statistics, completeness decisions, RDF and query-index facts are derived.

This checked-in corpus is the bounded historical evidence set. Future MLB API
runs do not extend it by default. New schedule responses are deleted after
candidate selection, and exact game responses are retained only until NiFi
successfully promotes both the authoritative and query-index graphs. Compact
hashes, manifests, and failure evidence remain available for audit and retry.

The runner stages a byte-identical response as `game.json` and prepares the
disposable `game-context.json` consumed by RML. Both stay outside the repository.
Helper fields belong only in the execution context; never overwrite raw bytes.

Provisioning and asynchronous proof/corpus submission are documented once in
the [NiFi runbook](../infra/nifi/README.md). They are operational actions, not
prerequisites for a documentation, SQL or UI edit. The checked-in samples also
support the [direct developer importer](../scripts/pipeline/README.md#direct-fallback-import),
which does not download data and is not an active NiFi inbox.

Runtime API payloads are transient. The Game lane deletes them after
authoritative/index promotion and the applicable immediate or deferred batch
materialization gate. Reference and transaction lanes delete them after their
source-owned authoritative promotion and cleanup gate. Bounded failures retain
their inputs in source-local quarantine.
