# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-04T14:50:51.0970073Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 228571 triples
- Query-index graphs: 8, 53530 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `030e601dceb5d4d525d7dee6f756d284daeff5615621e1703c46fd3ec66dcb46`
- Query-index contract SHA-256: `bfbfcdb4aa60b3819353d538a0a0076e50a2d14e110b6f6b4db50bb9e2f85b37`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 129.956 | 13.881 | 125.12 | 13.39 | 9.344x |
| outcomes-by-player | 422 | 60.368 | 24.756 | 61.963 | 28.676 | 2.161x |
| pitches-by-pitcher-and-venue | 62 | 61.865 | 27.032 | 56.865 | 25.88 | 2.197x |
| pitch-summary-by-pitcher | 62 | 214.287 | 50.632 | 220.571 | 49.574 | 4.449x |
| batted-balls-by-batter-and-venue | 157 | 71.721 | 23.336 | 72.418 | 21.11 | 3.431x |
| events-by-player | 549 | 149.733 | 48.678 | 152.106 | 36.407 | 4.178x |
| runs-by-season-and-venue | 8 | 33.205 | 5.43 | 32.552 | 4.729 | 6.883x |
| games-by-team-and-season | 16 | 4.625 | 3.675 | 4.805 | 4.512 | 1.065x |
| umpire-assignments | 32 | 5.645 | 5.366 | 4.542 | 4.507 | 1.008x |
| available-players | 158 | 10.812 | 10.659 | 10.958 | 10.289 | 1.065x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
