# Accepted field consequences

| Evidence | Accepted consequence |
| --- | --- |
| `details.type.code`, `details.type.description` | Reusable Nominal Measurement ICE under the MLB pitch-type Reference System; nominally measures the particular Pitch Act. Genuine pitch types may trigger reviewed Pitch Act subtypes. |
| `playId` | Identifier ICE designating the source event record; suitable for unique record IRI construction. |
| generated `outsBefore` | Count ICE derived from recorded preceding Out Processes in the same Half Inning and scoped to the Plate Appearance start. |
| result/event, pitch-call, and review-status tokens | Routing evidence, not direct `dcterms:identifier` or `dcterms:type` literals on records or world-side particulars. |
| replay outcome evidence | New review output and Decision ICEs persist alongside the earlier Decision; later institutional effect overrides rather than deletes history. |
| `strikeZoneTop`, `strikeZoneBottom`, pitch evaluation evidence | Preserve the three-dimensional rulebook Strike Zone Site and the distinct two-dimensional ABS evaluation Fiat Surface that is a continuant part of it. Method and era remain explicit. |
| game type and season date evidence | Build game-containing Season Phase Processes and no-game-required Season Segment Processes, including offseason structure needed by the transactions layer. |

Provider display `coordX` and `coordY` are not accepted by this record. Their
revised Cartesian reference-system pattern remains under review.
