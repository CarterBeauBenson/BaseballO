# Authoritative/indexed optimized ARQ algebra

Generated with Apache Jena Fuseki 6.1.0 using `arq.qparse --print=opt`.

This captures high-level optimized ARQ algebra. It does not capture TDB2 storage-specific runtime join ordering; Jena execution logging is still required for that evidence.

| Query | Authoritative triple patterns | Indexed triple patterns | Reduction |
| --- | ---: | ---: | ---: |
| hits-by-player-and-venue | 24 | 8 | 16 |
| outcomes-by-player | 9 | 4 | 5 |
| pitches-by-pitcher-and-venue | 10 | 5 | 5 |
| pitch-summary-by-pitcher | 18 | 10 | 8 |
| batted-balls-by-batter-and-venue | 13 | 6 | 7 |
| events-by-player | 8 | 4 | 4 |
| runs-by-season-and-venue | 20 | 7 | 13 |
| games-by-team-and-season | 10 | 7 | 3 |
| umpire-assignments | 5 | 5 | 0 |
| available-players | 3 | 3 | 0 |

Raw optimized algebra for each layer is stored beside this summary. See the [Apache Jena explanation documentation](https://jena.apache.org/documentation/query/explain.html) for the distinction between algebra optimization and storage-specific execution logging.
