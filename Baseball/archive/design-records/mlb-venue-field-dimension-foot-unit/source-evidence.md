# Source and domain evidence

Hydrated MLB venue data exposes five baseball field-dimension values under
`fieldInfo`: `leftLine`, `leftCenter`, `center`, `rightCenter`, and `rightLine`.
The previously reviewed venue inventory established their availability but
withheld mapping because the unit and world-side grounding were not both fixed.

On 2026-08-29 the ontologist supplied the domain fact that stadium field
dimensions are expressed in feet: baseball distances of this kind use feet.
This settles the unit for those five fields.

The pinned CCO dependency already contains
`https://www.commoncoreontologies.org/ont00001714`, an individual labeled
`Foot Measurement Unit` with alternative label `ft`. The accepted direct-ICE
foundation supplies the intended pattern in which the measurement ICE directly
uses that unit.

The source values and unit still do not identify the exact two Fiat Points,
the path or boundary between them, how the measurement was obtained, which
physical field configuration it describes, or when that configuration was
valid. No executable mapping follows until a source-specific geometry diagram
resolves those questions.
