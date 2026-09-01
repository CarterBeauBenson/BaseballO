# Design records

Accepted and rejected proposal packages move here with their disposition and
review history. They are not executable source modules and must not be imported
by RML, SHACL, SPARQL, serving, or UI code.

- [`replay-review/`](replay-review/) — accepted on 2026-08-05 and implemented
  in the authoritative ontology and MLB game source module.
- [`game-season-process-and-team-context/`](game-season-process-and-team-context/)
  — accepted on 2026-08-28; classifies games and seasons as processes and
  reuses occupation-role organizational context for team membership.
- [`plate-appearance-batter-role-realization/`](plate-appearance-batter-role-realization/)
  — accepted on 2026-08-28; restores the generic Batter Act as the realization
  grain for the career-persistent Batter Role.
- [`ice-direct-values-and-units/`](ice-direct-values-and-units/) — accepted on
  2026-08-29; authorizes direct ICE values and direct unit/reference-system use.
- [`mlb-organizations/`](mlb-organizations/) — accepted on 2026-08-29; admits
  the reviewed season classes while preserving the organization blockers.
- [`mlb-people/`](mlb-people/) — accepted on 2026-08-29 as a de-duplication and
  gap record; it authorizes no standalone mapping.
- [`mlb-transactions/`](mlb-transactions/) — accepted on 2026-08-29; admits the
  reviewed Trade and Uniform Number Assignment classes and record pattern.
- [`mlb-venues/`](mlb-venues/) — accepted on 2026-08-29 as a de-duplication and
  gap record; it authorizes no standalone mapping.
- [`ontology-curation-debt-repair/`](ontology-curation-debt-repair/) — accepted
  on 2026-08-29; authorizes the reviewed repairs and hosting function.
- [`realist-geometry-foundations/`](realist-geometry-foundations/) — accepted on
  2026-08-29; admits Angle Quality and Distance Quality.
- [`statcast-nonduplicate/`](statcast-nonduplicate/) — accepted on 2026-08-29;
  authorizes the reviewed ontology term but no Statcast executable artifacts.
- [`mlb-reference-source-ownership/`](mlb-reference-source-ownership/) —
  accepted on 2026-08-29; assigns independently promoted MLB reference facts
  to detachable organization, people, venue, and transaction modules.
- [`mlb-venue-field-dimension-foot-unit/`](mlb-venue-field-dimension-foot-unit/)
  — accepted on 2026-08-29; fixes feet as the unit for the five venue field
  dimensions while retaining the source-specific geometry gate.
- [`mlb-organizations-source-contract/`](mlb-organizations-source-contract/)
  — accepted on 2026-08-29; authorizes the solid organizations source-specific
  RML/SHACL shape while retaining its affiliation blockers.
- [`mlb-people-source-contract/`](mlb-people-source-contract/) — accepted on
  2026-08-29; authorizes the solid people identity, name, height, and birth
  source shape while retaining the reviewed blocked fields.
- [`mlb-venues-source-contract/`](mlb-venues-source-contract/) — accepted on
  2026-08-29; authorizes the solid venue and field-distance source shape using
  CCO Foot while retaining the reviewed blocked fields.
- [`mlb-transactions-source-contract/`](mlb-transactions-source-contract/)
  — accepted on 2026-08-29; authorizes the information-layer transaction shape
  and conditional Death gate while retaining Trade and number blockers.
- [`FINAL-MLB-RML-REVIEW.md`](FINAL-MLB-RML-REVIEW.md) - accepted on
  2026-08-30; consolidates nineteen accepted source-independent design records
  for canonical Days, temporal Role histories, grounded transaction events,
  people SDCs, and venue parts, Functions, and Qualities. The decision admits
  nineteen class IRIs and no new object properties; executable source mappings
  remain gated by source-specific Mermaid review.
  The machine-readable aggregate decision is preserved in
  [`final-mlb-rml-review/`](final-mlb-rml-review/).
- [`mlb-game-measurement-classification-lifecycle-2026-08-31/`](mlb-game-measurement-classification-lifecycle-2026-08-31/)
  — accepted on 2026-08-31; fixes the evidence-equivalence gate,
  evaluation-local Process Profile pattern, classification-dependent pitch and
  batted-ball kinds, offseason temporal parts, and the bounded semantic-freeze
  generator repair.
- [`nifi-control-plane-hardening/`](nifi-control-plane-hardening/) — accepted
  on 2026-09-01; separates NiFi reconciliation, exact-build provenance,
  semantic index compatibility, consumer-grain preflight, and durable
  completion/outbox dispatch.
