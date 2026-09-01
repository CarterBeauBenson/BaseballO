# Statcast pitch speed process-profile foundation

Status: **under review — design only**

This package restarts the narrow physical foundation needed before any
Statcast pitch-speed mapping can be reviewed. It models motion in reality first:
a Pitch-Ball Motion Process has a Speed Process Profile as an occurrent part,
and a Measurement Information Content Entity measures that Process Profile.
The measurement ICE carries the decimal value and uses CCO Miles Per Hour.
The pitch-motion Process itself is not asserted to be "90 mph."

The source's scalar mph value is a measurement of Speed. It is not CCO
Velocity merely because baseball prose sometimes uses the words speed and
velocity interchangeably. Velocity is direction-bearing and frame-relative;
it may be used only when the direction, coordinate/reference frame, component
semantics, and evaluation period are represented.

The package proposes no ontology term. It also does not select
`release_speed` for Statcast RML: the existing field inventory correctly leaves
that field unresolved against MLB-game `startSpeed`. This design establishes
the world/ICE pattern needed for a later equivalence decision, not an exception
to source de-duplication.

The remaining central question is how the provider's release, initial-plane,
or plate-local value constrains a time-local portion of a changing Speed
Process Profile. "Time shot" must not be translated into an unsupported exact
Temporal Instant. No Statcast RML, SHACL, acquisition, or graph promotion is
authorized by this active draft.
