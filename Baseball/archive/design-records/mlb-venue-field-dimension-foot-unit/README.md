# MLB venue field-dimension foot-unit decision

Status: **accepted by the ontologist on 2026-08-29**

This record preserves the domain decision that the five MLB baseball field
dimension values are distances reported in feet. BaseballO reuses the existing
CCO `Foot Measurement Unit` individual (`cco:ont00001714`); no BaseballO class
or property is introduced.

The decision resolves only the measurement unit for `fieldInfo.leftLine`,
`leftCenter`, `center`, `rightCenter`, and `rightLine`. It does not settle the
exact Fiat Point endpoints, intended path or boundary, measurement method,
field configuration, or temporal validity. Those relata must be fixed in an
approved source-specific Mermaid before RML is written.
