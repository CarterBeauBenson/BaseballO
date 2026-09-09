# Correction: four runner object properties

2026-09-09 user clarification:

> I misunderstood your requests then, because you are not allowed to make new object properties. You asked your question in natural language and interpreted as permission to make an OP.

The assistant authored `hasResolvedRunner`, `hasAdjudicatedBase`,
`settlesAwardFrom` and `hasBaserunningOriginBase`, and interpreted earlier
answers as permission to introduce them. The ontology already stated that
BaseballO introduces no domain-specific object properties. The assistant's
interpretation was wrong. The archived accepted-status records are historical
records of that interpretation, not sufficient authorization to keep extending
or using these properties in new work.

This document records the correction and prepares a removal-only package.
It does not claim that removal has executed, change a protected semantic pin,
or mark a replacement design as approved. The four declarations and their
existing executable dependencies are still present at this point.

## Removal-only package: runner-object-property-removal

The intended change removes the four predicates and only their dependent
implementation. It does not revert the entire metrics commit or introduce
replacement ontology vocabulary.

| Component | Targeted correction |
| --- | --- |
| `ontology/BaseballO.ttl` | Remove the four object-property declarations. Preserve all pre-existing classes and BFO/CCO relations. |
| `governance/ontology-curation-debt.json` | Remove the four entries from the approved-local-object-property list. Preserve unrelated frozen findings. |
| `scripts/pipeline/prepare-rml-context.py` | Remove `runner_resolution_links` and its four execution-context products. Retain the independently accepted `batted_runner_resolution_links` contact-play containment. |
| `sources/mlb-game/mapping/mlb-game.rml.ttl` | Remove the four predicate-producing maps and their now-unused logical sources. Retain accepted contact-play parthood and the rest of the lane. |
| `sources/mlb-game/shacl/authoritative.ttl` | Remove constraints whose contract is specifically those withdrawn predicates. Preserve unrelated conformance constraints. |
| `sparql/metrics/attribution-evidence.rq`, `runner-movement-evidence.rq` | Remove dependencies on the four properties. Continue exposing only evidence obtainable with accepted terms; report absent bindings or unavailable results. Do not infer equivalent paths without review. |
| Source and metric tests | Replace tests asserting the four predicates with focused absence/non-regression checks. Retain accepted contact-play and metric arithmetic tests. |
| Source design docs and generated mapping inventory | Describe the removal and regenerate the owning module's actual mapping inventory; do not invent a replacement Mermaid pattern. |
| `governance/semantic-freeze.json` | After explicit acceptance of this named removal package, record the removal-specific review and matching protected fingerprints; do not bypass or weaken validation. |
| Existing decision records | Preserve history and add a superseding correction; never rewrite an earlier user answer or pretend approval occurred. |

The implementation must audit all executable references, including JSON
contracts and generated inventory. No blanket checkout of the previous commit:
that would also discard unrelated accepted work. Publish the removal decision
before implementation, using the existing dev workflow.

Already promoted RDF must not be silently deleted or rewritten. Whether any
promoted graph contains these assertions requires a user-authorized diagnostic
or NiFi failure evidence. Removing the TBox declaration does not erase those
triples. Graph retirement or correction requires its own explicit scope; source
raw bytes remain unchanged. Keep the semantic ingester and daily acquisition
schedule enabled. The removal package does not authorize new runtime topology.

## Assessment of the pasted structural replacement

The proposed direction is to express meaning through full patterns over
accepted relations, and derive SQL shortcuts only after those patterns are
admitted. The pasted text is design input, not approval of every diagram.

- **Runner resolution episode:** an episode's class, identity, temporal scope
  and pairing of act with resolution still need review. A count of one agent
  does not by itself establish which of several acts/resolutions belong together.
- **Adjudication:** `is about` a Base establishes aboutness. It does not by
  itself establish that this Base is the safe destination rather than another
  referent mentioned in the decision. Review the decision-content contract.
- **Award and prescription:** a directive's existence, identity, content and
  prescription of the particular act need source support. An award is not
  automatically evidence of an instruction held by an agent. Realization must
  remain distinct from prescription and the ICE.
- **Origin stasis:** retain the existing PA-start restriction until a specific
  generalization is reviewed. Temporal precedence alone is not immediacy or
  continuity. A source observation does not prove an interval of persistence.
- **Stasis participation:** the pasted final diagram uses `agent in` from the
  Player to a stasis. Use only a reviewed participation account for stasis;
  it neither realizes the role nor establishes intentional agency there.
- **Indexes:** changing the predicate namespace does not repair missing
  semantics. Prefer SQL projections of proven authoritative query paths. A
  shortcut alone cannot reconstruct the full path after the authoritative
  evidence is discarded.

No replacement classes, identity policies, object properties, stasis changes,
index predicates or mapping assumptions are accepted in this correction note.
Metric arithmetic can remain unchanged while those graph prerequisites are
reviewed.
