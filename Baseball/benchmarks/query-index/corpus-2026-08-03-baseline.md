# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-04T16:49:08.0092475Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 228576 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `53c64863b8f154fd867958b43bca0e2535798111aadd7fcc7f95fa6f44db4daa`
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 252.16 | 55.756 | 251.231 | 22.476 | 11.178x |
| outcomes-by-player | 422 | 148.676 | 42.605 | 104.867 | 50.357 | 2.082x |
| outcomes-by-season | 15 | 758.015 | 13.022 | 611.44 | 11.459 | 53.359x |
| plate-appearances-by-player-and-season | 158 | 65.557 | 37.677 | 61.334 | 25.604 | 2.395x |
| three-true-outcomes-by-player | 121 | 60.253 | 24.228 | 35.792 | 20.241 | 1.768x |
| pitches-by-pitcher-and-venue | 62 | 103.515 | 34.182 | 75.094 | 35.076 | 2.141x |
| pitch-summary-by-pitcher | 62 | 472.843 | 86.723 | 319.649 | 67.421 | 4.741x |
| batted-balls-by-batter-and-venue | 157 | 101.448 | 26.505 | 93.907 | 28.082 | 3.344x |
| events-by-player | 549 | 241.949 | 74.944 | 239.36 | 55.862 | 4.285x |
| runs-by-season-and-venue | 8 | 55.31 | 11.055 | 55.1 | 7.982 | 6.903x |
| games-by-team-and-season | 16 | 8.305 | 7.69 | 8.55 | 7.673 | 1.114x |
| umpire-assignments | 32 | 8.489 | 9.438 | 8.333 | 8.184 | 1.018x |
| available-players | 158 | 20.168 | 17.393 | 17.89 | 17.126 | 1.045x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
