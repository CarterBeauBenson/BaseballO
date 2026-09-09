# Structural correction implementation

Decision commit `f7177e7` was pushed to `origin/dev` before protected changes.
The user supplied the structural replacement and explicitly directed removal
and correction. No new object properties were introduced.

- Removed the four declarations and their context/RML producers. The local
  object-property allowlist is empty. Negative SHACL rejects all four predicates.
- Added Runner Resolution Episode, Base Award Directive ICE and the PA-start
  stasis subclass from the supplied design. General stasis retains the same
  Base Site interpretation, with participant/role/location and temporal scope
  constraints. It has no agent and realizes no role.
- Source RML reuses existing act, resolution, judgment, decision, Person and
  persistent role identities. Episodes bind pairs; act agency identifies the
  runner. Safe decisions are about their own resolution and sole destination.
- Updated source SHACL, analytical evidence queries, tests, source design docs,
  active review notices, generated Mermaid inventory and correction-specific
  semantic pins. Contact-play containment and metric arithmetic remain intact.

## Focused validation

29 focused tests passed: 9 runner structure/context/SHACL tests, 6 independent
contact-containment regressions, 7 movement evidence query tests, 3 attribution
audit tests and 4 PA-start location evidence tests. Negative cases include
multiple agents/episodes, mismatched roles/PA/field, wrong destinations, missing
provenance/codes, directive realization and absent immediate stasis boundaries.

An isolated one-record fixture transformed with RMLMapper 8.1.0 and passed the
full source profile with pySHACL (1,505 triples, zero violations). The unchanged
checked-in game 566279 then transformed with the same mapper: 31,401 triples,
113 episodes, 113 movement acts, 113 runner resolutions, 46 safe-destination
decisions and 51 specifically PA-start stases. It contains zero withdrawn
predicate triples and zero manufactured award directives.

The full game passed the final authoritative SHACL profile with Jena 6.1.0,
the source-stage engine: zero violations. Long-running Python full-game checks
were interrupted before switching engines; they are not counted as passes.
No corpus-wide or repository aggregate gate was manually run.

Static RML validation passed (351 maps, 101 logical sources, no undeclared
classes). Ontology curation passed (275 classes, zero local object/data
properties, the same three unrelated frozen findings). Generated inventory
contains 61 patterns and 125 Markdown files. Source raw bytes are unchanged.
See `implementation-evidence.json` for fingerprints and graph counts.

## Evidence still unavailable

Current source rows do not establish particular award directive content and
prescription, or a preceding stasis interval ending at the act's beginning.
Those paths remain unbound. Safe completion must match the directive's awarded
Base; counted Run completion still needs corresponding destination evidence.
PA-start state does not become complete before-consequence state. These gaps
continue to block affected live metric scoring; arithmetic is unchanged.

This was a local developer proof, not graph promotion. Previously promoted RDF,
raw evidence, the enabled ingester and daily acquisition schedule were not
changed. Repository-wide validation remains the asynchronous NiFi-owned gate.
