# MLB people source-specific contract

Status: **accepted by the ontologist on 2026-08-29**

This package proposes the source-specific RDF shape for the detachable
`mlb-people` module. It introduces no new class, object-property, or
data-property IRI and contains no executable RML, SHACL, or NiFi artifacts.

The solid review shape covers canonical Person identity, full name, nickname,
Height and its reported measurement, and Birth/date evidence. The provider's
bare integer `weight` remains blocked because this package has no official
source evidence establishing its unit as pounds. Laterality, position,
current-team context, uniform number, strike-zone values, debut/draft facts,
and provider status fields also remain blocked.

Existing MLB-game RDF remains persistent during population and equivalence
testing. The ontologist accepted the solid edges and the identity, null,
Unicode, and version policies in `source-specific-mermaid.md`; dashed edges
remain non-executable. The governance schema's historical
`sourceIndependentMermaid` key points to that source-specific review artifact
in `review.json`.
