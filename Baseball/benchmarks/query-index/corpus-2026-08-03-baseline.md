# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-04T16:21:44.0018388Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 228576 triples
- Query-index graphs: 8, 53542 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `53c64863b8f154fd867958b43bca0e2535798111aadd7fcc7f95fa6f44db4daa`
- Query-index contract SHA-256: `bfbfcdb4aa60b3819353d538a0a0076e50a2d14e110b6f6b4db50bb9e2f85b37`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 127.101 | 14.449 | 125.651 | 12.916 | 9.728x |
| outcomes-by-player | 422 | 83.014 | 24.891 | 60.683 | 28.842 | 2.104x |
| pitches-by-pitcher-and-venue | 62 | 58.062 | 28.251 | 57.778 | 26.414 | 2.187x |
| pitch-summary-by-pitcher | 62 | 217.56 | 52.756 | 214.771 | 50.158 | 4.282x |
| batted-balls-by-batter-and-venue | 157 | 73.392 | 20.843 | 74.839 | 21.313 | 3.511x |
| events-by-player | 549 | 144.276 | 60.746 | 145.776 | 33.659 | 4.331x |
| runs-by-season-and-venue | 8 | 32.56 | 5.357 | 32.361 | 4.804 | 6.736x |
| games-by-team-and-season | 16 | 5.039 | 4.741 | 4.582 | 4.173 | 1.098x |
| umpire-assignments | 32 | 4.965 | 4.66 | 4.759 | 4.843 | 0.983x |
| available-players | 158 | 11.449 | 10.301 | 11.438 | 11.111 | 1.029x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
