# Automatic count awards

The question 5 [decision](../../../archive/design-records/automatic-count-awards/review.json)
was published in `6344630` before implementation. The bounded
[proof](../../../benchmarks/metrics/automatic-count-awards-2026-09-15/README.md)
records real one-PA and whole-game RML, source SHACL and evidence serialization.

The context builder selects explicit non-pitch `VP`/`pitcher_pitch_timer` and
`AC`/`batter_pitch_timer` awards only after source reconciliation, complete
indexed PA membership, distinct source IDs, operative count increments and
compatible event-time ordering. Substitutions and unresolved reviews are
withheld. Selected and withheld identities and reasons remain in the existing
RML manifest's metricMappingEvidence. Provider intentional-walk counters are
not turned into separately invented umpire performances.

RML emits existing Ball/Strike Process, Judgment Act, Decision ICE and Rule
patterns with PA containment and source-record aboutness. Supported order
anchors identify actual neighboring Pitch Acts. It emits no pitch or pitched
motion for the award, no named umpire assignment and no exact judgment time.
The source SHACL profile enforces the graph contract. The serialization check
compares selected source identities with RDF; it does not duplicate SHACL's
semantic rules in Python.

The canonical single-source metric evidence query carries the distinct award
through SQL. The recovery calculator uses it to update the count while adding
zero pitches. Complete ordered count histories and eligible populations remain
unfinished. Automatic awards alone do not prove either population complete.

The source reconciler also preserves absent unplayed halves during its existing
inning-membership comparison. This fixes a mutating defaultdict lookup; it does
not weaken the required source census or impute scores. The context's existing
helper fingerprint records the repaired implementation.
