# Actual substituted batting participation

The [accepted question 4](../../../archive/design-records/substituted-batter-participation/review.json)
now has source context, RML, source SHACL and mechanical serialization checks.
The [real one-PA and whole-game proof](../../../benchmarks/metrics/substituted-batters-2026-09-15/README.md)
also verifies canonical query/SQL retention.

Explicit PH events connect incoming and replaced persons. The complete event
sequence and compatible substitution/pitch bounds assign actual pitches and
existing swing/bunt acts to the person batting. Persistent Batter Roles retain
their existing person identity. The original single-batter IRI remains for
ordinary PAs; multiple supported participants use person-suffixed Batter Acts.
Repeated-person stints and conflicting assignments fail this bounded source
projection rather than being merged. No source event supplies an invented
exact Batter Act interval or whole-act precedence assertion.

The source SHACL profile now allows multiple Batter Acts inside a PA, requires
each act's person and role, and checks agreement between each swing/bunt and
its enclosing act. Existing participant/type constraints still distinguish
the human batter from the bat artifact. NiFi verifies selected source identities
against RDF and retains that evidence in the RML manifest before promotion.

Actual agency is not official statistical PA attribution. The existing B1
admission independently reconciles official totals and withholds unresolved
substituted-turn assignments. This change does not duplicate PAs, relax
qualification, or certify a complete selected player population. It also does
not itself extend personal runner continuity through offensive replacements or
infer affected-player review assignments from a catcher/challenger identity.
Later accepted [history-effect handling](runner-history-effects.md) and
[C3 anchors](../../../archive/design-records/mlb-game-runner-boundary-anchors/README.md)
cover their supported replacement cases independently of batting attribution.
