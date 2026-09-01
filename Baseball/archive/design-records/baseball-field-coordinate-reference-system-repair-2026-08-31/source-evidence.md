# Source evidence

The ontologist explicitly rejected use of Spatial Region classes for this
model and approved the revised Fiat Line, Fiat Point, Angle Quality, Distance
Quality, and Reference System ICE pattern on 2026-08-31.

Repository evidence shows that the existing
`base:BaseballFieldCoordinateReferenceSystemICE` is currently asserted as a
subclass of `cco:ont00000275` (Spatial Reference System), while generic CCO
`cco:ont00000398` (Reference System) supplies the required information-entity
parent without committing BaseballO to CCO Spatial Region axes.

The active source inventory and semantic audit already defer `coordX` and
`coordY` execution because MLB does not document the required provider-frame
semantics. This repair preserves that gate.
