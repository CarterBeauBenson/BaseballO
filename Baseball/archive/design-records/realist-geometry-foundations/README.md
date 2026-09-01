# Realist geometry foundations

Status: **accepted by the ontologist on 2026-08-29; implementation pending**

This package proposes the two source-neutral world-side classes needed before
BaseballO can model venue dimensions or Statcast angles without embezzling the
geometry into Measurement ICEs. The definitions follow the ontologist's
existing football-ontology treatment of angle and distance.

The proposal adds only:

- `AngleQuality`, a Relational Quality borne by two intersecting Fiat Lines;
- `DistanceQuality`, a Relational Quality borne by two nonidentical Fiat
  Points.

Measurement ICEs remain about instances of these classes. Units, literals,
and reference systems remain on the Measurement ICE under the separately
reviewed direct-ICE relation proposal.

This package deliberately does **not** define signed axis displacement. The
Statcast intercept fields can be negative and are components relative to an
X/Y frame, while a Distance Quality is nonnegative. No existing relation was
found that would justify collapsing that distinction. Those fields remain
blocked until the world-side displacement account is reviewed.

No active ontology, overlay, mapping, or source module changes here.
