# Field-selection inventory

| Evidence family | Decision | Implementation boundary |
| --- | --- | --- |
| pitch type code and description | genuinely additional MLB-game evidence | map reusable nominal category evidence; derive only the current explicit Pitch Act subtype in the rebuildable query index |
| batted-ball trajectory code and description | genuinely additional MLB-game evidence | map reusable nominal category evidence; derive only the current explicit motion subtype in the rebuildable query index |
| game type and season-phase evidence | genuinely additional MLB-game evidence | map the accepted Season Segment or Phase structure when supported by the payload |
| transaction calendar periods | accepted shared ontology coverage | implement vocabulary now; do not invent MLB-game rows where the Games payload provides none |
| strike-zone rule-book and ABS geometry | accepted shared ontology coverage | implement the accepted classes; retain source fields with unresolved measurement semantics as blocked |
| provider display coordinates | unresolved | retain information-space evidence only; do not designate or mint a world-side Site |
| deferred speed, break, spin, acceleration, launch, and distance semantics | unresolved unless separately accepted | do not map in this implementation |
| Statcast fields | separate source | do not map or duplicate in MLB-game work |
