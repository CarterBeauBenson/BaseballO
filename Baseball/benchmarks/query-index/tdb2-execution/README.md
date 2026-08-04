# TDB2 execution capture

Generated with Apache Jena Fuseki 6.1.0 and `tdb2.tdbquery --set arq:logExec=ALL --results=none`.

The 36 normalized logs capture Jena query text, optimized algebra, TDB2 algebra, and the initial reordered execution pattern for each authoritative/indexed benchmark pair. Repeated aggregate subexecution traces are omitted. Fuseki was stopped so the command could open the same persistent TDB2 datastore read-only. Result tables were suppressed.

- Corpus SHA-256: `53c64863b8f154fd867958b43bca0e2535798111aadd7fcc7f95fa6f44db4daa`
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Layer | TDB2 quad patterns | BGPs | Sequences | Left joins | Execution trace lines | Log |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| hits-by-player-and-venue | authoritative | 24 | 0 | 1 | 0 | 24 | [hits-by-player-and-venue-authoritative.log](hits-by-player-and-venue-authoritative.log) |
| hits-by-player-and-venue | indexed | 8 | 0 | 1 | 0 | 8 | [hits-by-player-and-venue-indexed.log](hits-by-player-and-venue-indexed.log) |
| outcomes-by-player | authoritative | 9 | 0 | 2 | 0 | 9 | [outcomes-by-player-authoritative.log](outcomes-by-player-authoritative.log) |
| outcomes-by-player | indexed | 4 | 0 | 1 | 0 | 4 | [outcomes-by-player-indexed.log](outcomes-by-player-indexed.log) |
| outcomes-by-season | authoritative | 15 | 0 | 1 | 0 | 15 | [outcomes-by-season-authoritative.log](outcomes-by-season-authoritative.log) |
| outcomes-by-season | indexed | 5 | 0 | 1 | 0 | 5 | [outcomes-by-season-indexed.log](outcomes-by-season-indexed.log) |
| plate-appearances-by-player-and-season | authoritative | 14 | 0 | 0 | 0 | 14 | [plate-appearances-by-player-and-season-authoritative.log](plate-appearances-by-player-and-season-authoritative.log) |
| plate-appearances-by-player-and-season | indexed | 6 | 0 | 1 | 0 | 6 | [plate-appearances-by-player-and-season-indexed.log](plate-appearances-by-player-and-season-indexed.log) |
| three-true-outcomes-by-player | authoritative | 9 | 0 | 2 | 0 | 9 | [three-true-outcomes-by-player-authoritative.log](three-true-outcomes-by-player-authoritative.log) |
| three-true-outcomes-by-player | indexed | 4 | 0 | 2 | 0 | 4 | [three-true-outcomes-by-player-indexed.log](three-true-outcomes-by-player-indexed.log) |
| extra-base-hits-by-player | authoritative | 9 | 0 | 2 | 0 | 9 | [extra-base-hits-by-player-authoritative.log](extra-base-hits-by-player-authoritative.log) |
| extra-base-hits-by-player | indexed | 4 | 0 | 2 | 0 | 4 | [extra-base-hits-by-player-indexed.log](extra-base-hits-by-player-indexed.log) |
| home-runs-by-player-and-venue | authoritative | 14 | 0 | 1 | 0 | 14 | [home-runs-by-player-and-venue-authoritative.log](home-runs-by-player-and-venue-authoritative.log) |
| home-runs-by-player-and-venue | indexed | 6 | 0 | 1 | 0 | 6 | [home-runs-by-player-and-venue-indexed.log](home-runs-by-player-and-venue-indexed.log) |
| multi-hit-games | authoritative | 14 | 0 | 2 | 0 | 14 | [multi-hit-games-authoritative.log](multi-hit-games-authoritative.log) |
| multi-hit-games | indexed | 4 | 0 | 1 | 0 | 4 | [multi-hit-games-indexed.log](multi-hit-games-indexed.log) |
| total-bases-by-player-and-season | authoritative | 19 | 0 | 1 | 0 | 19 | [total-bases-by-player-and-season-authoritative.log](total-bases-by-player-and-season-authoritative.log) |
| total-bases-by-player-and-season | indexed | 7 | 0 | 2 | 0 | 7 | [total-bases-by-player-and-season-indexed.log](total-bases-by-player-and-season-indexed.log) |
| hitless-games-by-player | authoritative | 19 | 0 | 2 | 0 | 8 | [hitless-games-by-player-authoritative.log](hitless-games-by-player-authoritative.log) |
| hitless-games-by-player | indexed | 8 | 0 | 1 | 0 | 5 | [hitless-games-by-player-indexed.log](hitless-games-by-player-indexed.log) |
| pitches-by-pitcher-and-venue | authoritative | 10 | 0 | 1 | 0 | 10 | [pitches-by-pitcher-and-venue-authoritative.log](pitches-by-pitcher-and-venue-authoritative.log) |
| pitches-by-pitcher-and-venue | indexed | 5 | 0 | 1 | 0 | 5 | [pitches-by-pitcher-and-venue-indexed.log](pitches-by-pitcher-and-venue-indexed.log) |
| pitch-summary-by-pitcher | authoritative | 18 | 0 | 2 | 0 | 6 | [pitch-summary-by-pitcher-authoritative.log](pitch-summary-by-pitcher-authoritative.log) |
| pitch-summary-by-pitcher | indexed | 10 | 0 | 1 | 0 | 4 | [pitch-summary-by-pitcher-indexed.log](pitch-summary-by-pitcher-indexed.log) |
| batted-balls-by-batter-and-venue | authoritative | 13 | 0 | 2 | 0 | 13 | [batted-balls-by-batter-and-venue-authoritative.log](batted-balls-by-batter-and-venue-authoritative.log) |
| batted-balls-by-batter-and-venue | indexed | 6 | 0 | 1 | 0 | 6 | [batted-balls-by-batter-and-venue-indexed.log](batted-balls-by-batter-and-venue-indexed.log) |
| events-by-player | authoritative | 8 | 0 | 2 | 0 | 8 | [events-by-player-authoritative.log](events-by-player-authoritative.log) |
| events-by-player | indexed | 4 | 0 | 1 | 0 | 4 | [events-by-player-indexed.log](events-by-player-indexed.log) |
| runs-by-season-and-venue | authoritative | 20 | 0 | 0 | 0 | 20 | [runs-by-season-and-venue-authoritative.log](runs-by-season-and-venue-authoritative.log) |
| runs-by-season-and-venue | indexed | 7 | 0 | 1 | 0 | 7 | [runs-by-season-and-venue-indexed.log](runs-by-season-and-venue-indexed.log) |
| games-by-team-and-season | authoritative | 10 | 0 | 1 | 0 | 10 | [games-by-team-and-season-authoritative.log](games-by-team-and-season-authoritative.log) |
| games-by-team-and-season | indexed | 7 | 0 | 2 | 0 | 7 | [games-by-team-and-season-indexed.log](games-by-team-and-season-indexed.log) |
| umpire-assignments | authoritative | 5 | 0 | 1 | 0 | 5 | [umpire-assignments-authoritative.log](umpire-assignments-authoritative.log) |
| umpire-assignments | indexed | 5 | 0 | 1 | 0 | 5 | [umpire-assignments-indexed.log](umpire-assignments-indexed.log) |
| available-players | authoritative | 3 | 0 | 1 | 0 | 3 | [available-players-authoritative.log](available-players-authoritative.log) |
| available-players | indexed | 3 | 0 | 1 | 0 | 3 | [available-players-indexed.log](available-players-indexed.log) |

These captures are storage-level query-planning evidence, not timing measurements. Each log is timestamp-normalized, limited to the first execution section, and content-hashed in the JSON summary.
