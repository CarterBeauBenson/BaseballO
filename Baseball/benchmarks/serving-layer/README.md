# Analytical serving evidence

[`current.json`](current.json) is a historical compact summary captured on
2026-08-28 from a contract-5 local serving build: 558 promoted local game
graphs, all Explorer grains, PAQ, and the 17 advanced queries. Its filename is a
legacy evidence name, not the runtime serving pointer and not a claim that the
capture describes the current materializer. It is retained in place so links
and research history remain stable.

That local scope is larger than the 546-game checked-in raw evidence corpus and
must not be described as the tracked corpus baseline. The capture also predates
the current promotion-inventory and live graph-pair integrity gates. Runtime
databases, the actual `serving/current.json` pointer, and detailed NiFi evidence
remain under LocalAppData and are not committed.

The captured SPARQL measurement is bounded per game because its purpose is the
rebuild lifecycle, not an interactive full-corpus query. The SQL measurement is
the Explorer's representative latest-seven-day read, repeated seven times from
the validated immutable candidate. These timings establish the first serving
baseline; they are not presented as an indexed-RDF comparison or as a claim
that unlike scopes are a single speedup ratio.

The historical `equivalence` member reports binding-hash preservation within
that build. It is not an end-to-end SPARQL-to-SQL result-equivalence proof and
must not be used to admit the current materializer. A current-contract
equivalence capture remains required.

DuckDB was considered at the runtime-fit gate but is not installed on the
Windows deployment host. SQLite is already in the supported Python runtime,
needs no service, and passed the real workload. A later DuckDB evaluation
remains possible if columnar Explorer families justify adding that dependency.
