# Statcast defensive alignment

Status: **under review — design only**

This package isolates `if_fielding_alignment` and `of_fielding_alignment`, both
accepted as genuinely additional provider classifications. The category token
is not a world-side configuration. The candidate graph represents actual
Fielder Persons located in field-relative Sites during a generic Stasis, then
lets a Nominal Measurement ICE classify that Stasis under a versioned provider
Reference System.

The review must decide whether generic Sites, `located in`, shared Stasis
participation, and a Temporal Interval are sufficient to identify the actual
configuration, or whether a source-independent ontology gap remains. It must
also determine the pitch-relative interval and official category values/rules.
An aggregate of Fielder Persons alone is never enough.

Duplicate fielder identities, positions, lineup history, game/pitch context,
and field identity remain owned by MLB-game or their authoritative reference
lanes. The governance artifact bucket `sourceIndependentMermaid` points to
`source-specific-mermaid.md`.
