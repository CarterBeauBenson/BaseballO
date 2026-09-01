# Statcast bat-tracking geometry

Status: **under review — design only**

This package isolates `attack_angle`, `attack_direction`, and
`swing_path_tilt`. The accepted Statcast inventory classifies all three as
genuinely additional, but blocks mapping until the tracked sweet-spot motion,
tangent/reference geometry, evaluation scope, and fitted-path semantics are
represented in reality.

The candidate shape uses a generic Motion as an occurrent part of a Swing Act,
a Velocity Process Profile as an occurrent part of that Motion, actual Fiat
Points/Fiat Lines and Angle Qualities, and generic Measurement ICEs. No
field-shaped ICE replaces the tangent line, ground/home-to-center reference,
or fitted path.

The archived source-independent review accepted the
`BaseballBatSweetSpotFiatPoint` proposal, but that class is not declared in the
current ontology files. This draft therefore uses the accepted generic BFO Fiat
Point plus a designating ICE and treats implementation/review of the specialized
class as a prerequisite rather than assuming it exists.

The governance schema retains the artifact key `sourceIndependentMermaid`;
this source-specific package points that key to `source-specific-mermaid.md`.
No RML, SHACL, ontology, or graph change is authorized.
