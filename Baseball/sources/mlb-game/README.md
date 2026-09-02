# MLB game source module

This module is the complete source-owned boundary for the MLB Stats API
`feed/live` game response.

- [`schema/`](schema/) records the observed source contract.
- [`mapping/`](mapping/) contains the only executable RML and source-field IRI
  policy for this source.
- [`shacl/`](shacl/) validates only authoritative RDF emitted by this source.
- [`review/`](review/) owns the reviewed pattern manifest used to generate the
  post-implementation Mermaid regression catalog and the machine-readable
  semantic-status record.
- [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) records the current anti-flattening
  review and the gates for extending coverage.

NiFi owns acquisition, dependency ordering, isolated execution, validation,
promotion, retry, and provenance for this module. Integration with other source
families happens only after promotion, through dependency-declared SPARQL over
the triple store. This module must never import another source's RML or SHACL.
Its registered source-owned NiFi process group is `MLB Game`. That group owns
proof requests, schedule discovery, completed-game fanout, per-game semantic
promotion, deferred corpus materialization, cleanup, and source-local failure
handling. There is no active NiFi manual inbox.

Schedule discovery deduplicates by stable MLB `gamePk`. When the same game has
an official postponed occurrence and a later completed occurrence, the lane
persists compact schedule evidence and maps one game plus the postponement
declaration, its old and revised Schedule Plans, their canonical Days, and any
provider reason as nominal evidence. It does not assert that the provider
reason is a world-side weather cause. Parser failures preserve the original
response bytes for bounded retry or quarantine.

A schedule request that arrives while the current mapping and SHACL still need
a bounded proof remains inside the NiFi lane. NiFi retries the proof-release
readiness check every 30 seconds for up to 30 minutes, releases the request as
soon as the proof completes, and uses source-local schedule quarantine only if
that readiness window is exhausted.

The module is operationally active and its current pinned contract is
semantically `approved`. NiFi runs it asynchronously and applies the
source-owned SHACL profile before promotion.
[`review/semantic-status.json`](review/semantic-status.json) is the machine
gate; [`SEMANTIC-AUDIT.md`](SEMANTIC-AUDIT.md) preserves the original audit and
records how the accepted 2026-08-31 migrations resolved it.

Future MLB-game fields still require reviewed proposals. Other MLB APIs and
Statcast remain detachable source modules with their own Mermaid, RML, SHACL,
and NiFi lanes; no later source may broaden this module implicitly.

The bounded proof passed, the source-owned 05:00 Eastern trigger is enabled,
and the 2026 season-to-date request was submitted on 2026-09-01. Schedule runs
materialize SQL once per completed batch rather than once per discovered game.
Consult terminal NiFi evidence only when checking completion or a recorded
failure.
