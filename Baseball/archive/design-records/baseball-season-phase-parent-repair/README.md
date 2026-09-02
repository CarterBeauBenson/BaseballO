# Baseball Season Phase parent repair

Accepted curation repair for the already accepted `BaseballSeasonPhase` class.

The class currently has both `BFO Process` and `BaseballSeasonSegment` as direct
named parents, while `BaseballSeasonSegment` is already a subclass of
`BFO Process`. The repair removes only the redundant direct `BFO Process`
assertion. It introduces no term, relation, definition, or change to the
inferred class hierarchy.
