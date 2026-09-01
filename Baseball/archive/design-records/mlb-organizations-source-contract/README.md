# MLB organizations source-specific contract

Status: **accepted by the ontologist on 2026-08-29**

This package proposes the source-specific RDF shape for the detachable
`mlb-organizations` module. It is the review gate between the already accepted
source-independent ontology and executable RML. It introduces no new class,
object-property, or data-property IRI.

The proposal maps stable MLB identifiers and canonical names for teams,
leagues, and divisions; represents leagues and divisions as generic CCO
Organizations distinguished by their provider identifiers; and uses the
accepted Baseball Season, Baseball Season Phase, and Baseball Season Plan
classes. It deliberately does **not** assert team-to-league,
team-to-division, or division-to-league affiliation. Those season-scoped
institutional relations remain unresolved and are dashed in the Mermaid
diagram.

The accepted ownership migration is non-destructive. Existing MLB-game RDF
remains authoritative history while this reference graph is populated and
tested. Future removal of duplicate reference assertions from the game lane
requires query and corpus equivalence; it is not authorized by this package.

The ontologist accepted the solid shapes and identity/null policies in
`source-specific-mermaid.md`. Dashed shapes remain blocked. The governance
schema retains the historical artifact key `sourceIndependentMermaid`; in
`review.json` that key points to this source-specific Mermaid review artifact.

No RML, SHACL, NiFi process group, acquisition run, graph promotion, or query
cutover is included in this decision commit; implementation follows separately.
