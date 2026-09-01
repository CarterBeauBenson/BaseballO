# Field selection and de-duplication inventory

This inventory is deliberately narrow. It does not reopen the full Statcast
selection catalog or authorize any mapping.

| Statcast field or family | Existing-source classification | Design consequence |
| --- | --- | --- |
| `game_pk`, batter ID, pitcher ID, pitch number/row join keys | already supplied or identity/join-only | Use only for transient matching to canonical MLB game entities. Do not mint source-local Games, Persons, or pitches. |
| `release_speed` | unresolved duplicate of MLB-game `startSpeed` | Candidate target is a Speed Process Profile measured in mph, but no Statcast RML until evaluation semantics and corpus equivalence are resolved. |
| MLB-game `startSpeed` | authoritative MLB-game mapping-coverage debt | The MLB owner should eventually use the same realist Speed-profile pattern after its own accepted source-specific review. Statcast cannot take ownership merely because this field is currently unmapped. |
| MLB-game `endSpeed` | already supplied by MLB-game; mapping-coverage debt | Requires its own evaluation-scope identity; it is not another constant property of the motion Process. |
| `vx0`, `vy0`, `vz0` | already supplied by MLB-game | Exclude from Statcast. Directional Velocity modeling still requires axes, signs, origin, frame, and evaluation semantics. |
| `ax`, `ay`, `az` | already supplied by MLB-game | Exclude from Statcast; acceleration Process Profile is outside this proposal. |
| `effective_speed` | unresolved provider-derived value | Separate modeling question for algorithm, reference extension/population, estimate target, and version. Do not type as actual Speed. |
| `release_extension` | already supplied by MLB-game | Exclude; may be an input to a later effective-speed derivation. |
| `pitch_type`, `zone`, `plate_x`, `plate_z` | already supplied or unresolved duplicates | Outside this speed foundation. Do not use them to smuggle evaluation-plane semantics into a speed IRI. |
| null value | source missingness | Emit no measurement from that field. Preserve whether the provider says absent, not tracked, or not applicable when the source exposes that distinction. |
| method era / acquisition metadata | provenance, genuinely required | Persist source, request, response hash, method era/reference, mapping version, validation result, and promoted graph hash. |

## Candidate entity identity after approval

| Entity | Candidate identity policy |
| --- | --- |
| Pitch-Ball Motion Process | Reuse the canonical MLB-game world Process joined by reviewed pitch identity. Statcast does not mint a competing motion Process. |
| Baseball | Reuse the game-scoped participating Baseball identity where the accepted MLB model supplies it. |
| Speed Process Profile | Key to the canonical motion Process plus a reviewed evaluation-scope identity. Whether the whole motion has one changing profile or several local profiles is unresolved. |
| Velocity Process Profile | Not minted until direction and frame are represented. It must not share identity with a scalar Speed profile merely because values use mph. |
| Measurement ICE | Source-, field/evaluation-, method-, and response-versioned evidence measuring exactly one Process Profile. |
| Miles Per Hour unit | Reuse the accepted CCO named individual; do not mint a source unit. |
| source record | Content-versioned Descriptive ICE distinct from the Process, profile, and measurement result. |

## Ownership gate

- MLB-game owns facts already present in its authoritative payload, including
  start/end speed and initial vector components.
- Statcast may later own only genuinely additional facts or a distinctly
  evidenced assertion whose non-equivalence is approved.
- The two source mappings and SHACL profiles never cross. Equivalence is tested
  with explicitly scoped SPARQL after independent promotion.
- This package's Process Profile shape is source-independent and may guide both
  source contracts; it does not merge their evidence ICEs or provenance.
