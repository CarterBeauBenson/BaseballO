# Field inventory and de-duplication

| Field or evidence | Disposition | Design consequence |
| --- | --- | --- |
| person 'id' | identity/join-only | Reuse the canonical Person; never key Mass by response position. |
| 'weight' | authoritative duplicate; proposed mapping | Positive numeric value becomes a decimal Mass measurement in pounds in the owning people lane only. |
| Pound source-unit fact | source evidence | Use accepted Pound Measurement Unit; do not create a provider unit class. |
| response hash and retrieval time | provenance only | Version the evidence; do not assert a measuring process or measurement time. |
| null or absent 'weight' | resolved absence | Emit no Mass measurement subgraph. |
| malformed, zero, or negative present value | invalid input | Quarantine before RML; do not silently omit or coerce. |
| converted kilograms or BMI | derived | Calculate downstream only when needed; do not add source assertions. |

The Mass Quality identity is Person-scoped. The Measurement ICE identity is
response/content-scoped. This package proposes no class or property IRI.

