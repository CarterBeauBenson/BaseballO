# Select-box option queries

These queries discover valid UI choices from the named graphs currently loaded
in Fuseki. They do not calculate or store statistics.

| Query | Select-box values |
| --- | --- |
| [`available-seasons.rq`](available-seasons.rq) | First-pitch years used as the current season convention |
| [`available-venues.rq`](available-venues.rq) | Canonical venue IRIs and labels |
| [`available-players.rq`](available-players.rq) | Canonical player IRIs and labels for observed batters |
| [`available-hit-types.rq`](available-hit-types.rq) | Explicit hit classes with hit judgments present in loaded graphs |
| [`available-games.rq`](available-games.rq) | Canonical game IRIs, start times, and venue labels |
| [`available-pitchers.rq`](available-pitchers.rq) | Players observed as agents of pitch acts |
| [`available-baserunners.rq`](available-baserunners.rq) | Players participating in runner resolutions |
| [`available-teams.rq`](available-teams.rq) | Canonical team IRIs and labels |
| [`available-umpires.rq`](available-umpires.rq) | People bearing mapped umpire roles |
| [`available-official-scorers.rq`](available-official-scorers.rq) | People bearing mapped official-scorer roles |
| [`available-batting-outcomes.rq`](available-batting-outcomes.rq) | The 17 explicit, adjudicated plate-appearance result classes present in loaded graphs |
| [`available-baserunning-events.rq`](available-baserunning-events.rq) | Source event labels for adjudicated runner resolutions present in loaded graphs |

The browser may use the returned IRIs as option values and the labels as option
text. The query API must still treat the submitted selection as untrusted input
and validate it against the same allowlist used by the compiler.

`available-players` has a measured indexed companion, but the reviewed router
keeps the authoritative version because its simple lookup performance is
neutral. UI option queries remain authoritative-only.
