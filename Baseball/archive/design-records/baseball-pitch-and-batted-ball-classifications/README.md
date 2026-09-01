# Baseball pitch and batted-ball classification classes

Status: **accepted 2026-08-31**

This package proposes exact world-side class definitions for the accepted
classification-dependent pattern. Provider labels remain reusable Nominal
Measurement ICE individuals. They classify Pitch Acts or Batted-Ball Motion
Processes; they do not replace those entities or make variable grips,
velocities, spin, or trajectories essential conditions.

The reusable category ICEs are ontology individuals. The applicable MLB
Reference System edition is source evidence and must be minted as a versioned
individual by the owning mapping; this proposal deliberately does not install
one timeless MLB reference-system individual.

Historical nominal classifications remain persistent evidence. They do not
drive OWL class inference. The currently authoritative classification is
promoted as an explicit `rdf:type` assertion in a rebuildable current-state
reasoning graph. Reclassification replaces that current-state graph assertion
without deleting the historical ICEs. The proposed OWL therefore contains
necessary restrictions only and no classification-based
`owl:equivalentClass` axioms.

No object property or data property is proposed. The package is archived as an
accepted design record; bounded implementation is authorized by the separate
MLB-game classification and geometry implementation record.
