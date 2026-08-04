# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-04T17:10:10.1605257Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 228576 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `53c64863b8f154fd867958b43bca0e2535798111aadd7fcc7f95fa6f44db4daa`
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 232.534 | 62.614 | 257.622 | 28.089 | 9.172x |
| outcomes-by-player | 422 | 145.627 | 48.408 | 100.258 | 48.082 | 2.085x |
| outcomes-by-season | 15 | 609.091 | 14.345 | 607.247 | 12.645 | 48.023x |
| plate-appearances-by-player-and-season | 158 | 69.04 | 25.437 | 66.109 | 27.209 | 2.43x |
| three-true-outcomes-by-player | 121 | 37.663 | 33.117 | 37.468 | 20.661 | 1.813x |
| extra-base-hits-by-player | 39 | 16.34 | 7.777 | 12.793 | 7.345 | 1.742x |
| home-runs-by-player-and-venue | 26 | 10.866 | 7.26 | 11.135 | 8.074 | 1.379x |
| multi-hit-games | 39 | 216.668 | 9.495 | 167.282 | 9.489 | 17.629x |
| total-bases-by-player-and-season | 93 | 194.695 | 13.008 | 232.097 | 16.858 | 13.768x |
| hitless-games-by-player | 65 | 531.544 | 73.51 | 407.411 | 53.201 | 7.658x |
| pitches-by-pitcher-and-venue | 62 | 80.246 | 33.532 | 75.735 | 34.745 | 2.18x |
| pitch-summary-by-pitcher | 62 | 398.502 | 62.58 | 322.266 | 64.951 | 4.962x |
| batted-balls-by-batter-and-venue | 157 | 103.178 | 26.54 | 97.616 | 29.505 | 3.308x |
| events-by-player | 549 | 237.027 | 77.882 | 241.559 | 48.637 | 4.967x |
| runs-by-season-and-venue | 8 | 65.072 | 10.338 | 54.341 | 7.78 | 6.985x |
| games-by-team-and-season | 16 | 7.922 | 7.105 | 7.066 | 6.318 | 1.118x |
| umpire-assignments | 32 | 7.023 | 7.571 | 6.745 | 6.782 | 0.995x |
| available-players | 158 | 23.089 | 16.24 | 13.918 | 14.119 | 0.986x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
