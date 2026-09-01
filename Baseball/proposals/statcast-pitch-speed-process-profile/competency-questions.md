# Competency questions

| ID | Competency question | Candidate consequence or unresolved choice |
| --- | --- | --- |
| SCSPD-CQ-01 | What moves during a pitch? | A Baseball participates in a Pitch-Ball Motion Process following the Pitch Act. The moving Process is distinct from its Process Profiles and from information about them. |
| SCSPD-CQ-02 | What is measured by a scalar mph pitch value? | A CCO Speed Process Profile that is an occurrent part of the Pitch-Ball Motion Process, not the Pitch Act, pitch record, Baseball, or motion Process as a whole. |
| SCSPD-CQ-03 | Where does the number `90` belong? | A generic Measurement ICE that is a measurement of the Speed Process Profile has the decimal value and uses the CCO Miles Per Hour Measurement Unit. No field-specific measurement class is needed. |
| SCSPD-CQ-04 | Is scalar `release_speed` a Velocity? | No. A scalar magnitude is Speed. CCO Velocity additionally requires direction with respect to a frame of reference. Provider wording does not erase that differentia. |
| SCSPD-CQ-05 | When may CCO Velocity be instantiated? | Only after vector/component semantics, axis orientation, sign, origin, reference frame, unit, and evaluation period are reviewed and represented. Whether existing accepted relations are sufficient for the component structure is unresolved. |
| SCSPD-CQ-06 | What makes a release-speed profile different from a plate-speed or another speed observation of the same motion? | Unresolved. The design must identify the evaluated motion portion or temporal/position scope without putting `release` or `plate` semantics only in an IRI or ICE label. |
| SCSPD-CQ-07 | Is the evaluation an instantaneous value? | Unresolved. Tracking values may summarize a short interval, fitted trajectory, plane crossing, or provider-defined sample. Do not assert a Temporal Instant until source evidence warrants it. |
| SCSPD-CQ-08 | Is an Act of Measuring asserted? | Not from a CSV value alone. A measurement process requires evidence for that Process; the current minimum graph contains the result ICE and its measured Process Profile only. |
| SCSPD-CQ-09 | Does every pitch have one immutable speed? | No. Speed may vary throughout ball motion. Queries distinguish measurement target/scope and source method rather than attaching one literal to the whole pitch. |
| SCSPD-CQ-10 | Can Statcast `release_speed` be mapped even though MLB-game has `startSpeed`? | Not yet. The field remains an unresolved duplicate until corpus equivalence establishes whether target, evaluation plane/time, unit, and method-era semantics match. Missing MLB RML coverage does not make it genuinely additional. |
| SCSPD-CQ-11 | How are PitchFX-adjusted and Statcast-era release values distinguished? | The measurement/evidence identity must preserve method era and source provenance. Values from materially different reference methods are not silently merged. Exact Reference System or algorithm representation is unresolved. |
| SCSPD-CQ-12 | What does `effective_speed` measure? | It is a provider-derived perceived/effective metric, not another directly observed Speed Process Profile. Its algorithm, target, and reference population require a separate proposal. |
| SCSPD-CQ-13 | How does Statcast remain detachable? | Its mapping may use identity/join keys but may not duplicate MLB-owned facts. Statcast RML/SHACL stays source-local; integration and comparison occur only after graph promotion. |
| SCSPD-CQ-14 | What happens for null or untracked values? | Emit no profile or measurement from that field unless independent source evidence warrants the world entity. Absence, not tracked, and not applicable remain distinguishable in provenance, not invented zeroes. |

## Decisions requested from the ontologist

1. Should one Pitch-Ball Motion Process have one Speed Process Profile whose
   changing pattern receives several temporally scoped measurements, or should
   each provider-defined evaluation window identify a distinct local Speed
   Process Profile that is an occurrent part of the motion?
2. What world-side structure identifies "at release": a short motion-process
   segment, a plane-crossing Process Boundary, another Temporal Region, or a
   provider-defined model evaluation that remains only information-layer
   evidence?
3. What evidence is required before a fitted/adjusted value counts as a
   measurement of actual Speed rather than an estimate ICE about the profile?
4. Which versioned Reference System or Algorithm individuals distinguish the
   2008-2016 PitchFX-adjusted method from 2017+ Statcast out-of-hand values?
5. What corpus equivalence test will decide whether Statcast `release_speed`
   duplicates MLB-game `startSpeed`?
6. For directional components, is the accepted CCO reference-system pattern
   sufficient to capture Velocity, or is another world-side relation/class
   gap exposed by the required direction and frame?

## Negative tests

- A Pitch Act, Baseball, Pitch-Ball Motion Process, or source row has no direct
  mph literal standing in for the Process Profile.
- A Measurement ICE is not a Speed or Velocity.
- A Speed Process Profile is not a measurement record.
- A scalar mph value is not typed as Velocity.
- A Velocity profile is not asserted without direction and reference-frame
  semantics.
- `release`, `initial`, or `plate` in an IRI does not establish temporal or
  spatial evaluation scope.
- One reported value does not entail constant Speed throughout the motion.
- A source column already present in MLB-game remains a duplicate even when
  the MLB RML has not mapped it.
- `effective_speed` is not substituted for actual Speed.
- No measurement Act, instrument, or agent is invented from a result value.
