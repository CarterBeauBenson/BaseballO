# Concrete resolution and award links

Status: **proposed, not accepted**. Prepared 2026-09-08. This narrows the
remaining A2/A4 design to three relations over existing world-side entities.
It does not change the accepted A1 implementation or the meaning of
`BaserunnerAtBaseStasis`.

## Recommended modeling decision

Represent the adjudicated destination on the particular `SafeProcess`.
Identify the Person whose status that process settles. For a walk or HBP,
link a supported safe or scoring resolution to the particular institutional
award it completes. Reuse the existing Person, Base, resolution, award and
Game identities.

The three proposed properties are defined in [resolution-links.ttl](resolution-links.ttl).

| Proposed relation | Domain and range | Assertion |
| --- | --- | --- |
| `hasResolvedRunner` | Runner Resolution Process to Person | This is the particular runner whose counted status the process assigns. Other participants, including officials, are not thereby the resolved runner. |
| `hasAdjudicatedBase` | Safe Process to Base | The process counts this runner safe at this particular base in this adjudicated situation. It does not assert that the runner keeps touching the artifact, or retains entitlement indefinitely. |
| `settlesAwardFrom` | Safe Process or Run Process to Walk Process or Hit-by-Pitch Process | This resolution counts the runner's arrival at the base awarded by that process, directly to the batter or through the applicable forced advance. A counted Run Process is required for a scoring resolution. |

These are proposed primitive relations with independent anchors in the
accepted process definitions. No new class, Role, Quality, ICE subclass or
Stasis is proposed. OWL declares their domains and ranges and makes
`hasResolvedRunner` a specialization of `has participant`. OWL does not infer
the new relations from participation, aboutness, parthood or temporal order.
Their positive assertions require the reviewed evidence contract below.

## Why existing relations do not express these assertions

- `has participant` identifies involvement, but does not distinguish the
  runner whose status is decided from other Persons participating.
- `occurs at` identifies where a process happens. A Base is an artifact and
  the adjudicated destination is distinct from the location of adjudication.
- `is about` relates information to its referent; the Safe Process is the
  world-side institutional event already modeled in the accepted ontology.
- `has output` does not mean adjudicated destination; the pre-existing Base
  is not produced by the resolution.
- `has occurrent part` cannot connect a process to a Base. For awards it
  would assert containment of the later resolution in the award, which is
  not entailed by the fact that the award is completed.
- `is cause of` does not express the rule-governed relationship between an
  award and its completion, or analytical batter credit.

## Independent rules evidence

The [2019 Official Baseball Rules](https://content.mlb.com/documents/2/2/4/305750224/2019_Official_Baseball_Rules_FINAL_.pdf),
Rules 5.05(b), 5.06(a)(1), 5.06(b)(3)(B), and 5.06(b)(4)(I) Comment,
distinguish entitlement, forced advancement, arrival and the obligation to
touch awarded bases. The award alone therefore cannot establish completed
safe arrival. The [2026 edition](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf),
Rules 5.06(a)(1) and 5.06(b)(3)(B), retains the relevant distinction between
base entitlement and forced advancement. Use the applicable edition for a
game; this comparison does not impose 2026 rules on the 2019 fixture.

**Modeling inference:** an adjudication-to-base relation is the narrower
claim supported by the accepted Safe Process model. The source's terminal
base token does not alone establish a continuously persisting entitlement.

## Temporal scope and identity

The destination is qualified by the existing resolution instance and its
Game. The resolution occupies its own Temporal Region through
`obo:BFO_0000199`. Where evidence supports exact endpoints, that region can
use `obo:BFO_0000222` / `obo:BFO_0000224` for first / last instant, with
`obo:BFO_0000203` Temporal Instants. Never copy the enclosing pitch's timestamp
onto a runner resolution as if it precisely timed the adjudication.

This is an event-scoped adjudication relation, not a continuously valid
Person-to-Base assertion. It makes no claim about a nonzero persistence
interval, the runner's location while leading off, or the runner's base
entitlement after subsequent events. No stasis is required for this link.
The existing PA-start location stasis retains its existing meaning.

Use one existing runner resolution for each supported counted result.
Different resolutions concerning the same runner remain different events.
A later appeal or replay may supersede a result; neither an overturn flag
nor a subsequent safe result proves the content of the original decision.
The operative-resolution path remains a prerequisite for metric admission.

## Source evidence for the proposed links

All PA numbers below are `about.atBatIndex`; runner row numbers are zero-based.
All files are preserved checked-in evidence. These observations are evidence
for review, not reports of new RML output.

| Fixture | Observed evidence | Proposed interpretation to test |
| --- | --- | --- |
| `game-566279.json`, PA 2 | Batter double, terminal base second | Existing Safe Process receives the particular second Base as adjudicated base. |
| `samples/2026-08-25/822693.json`, PA 6 | Walk; runner 694673 first to second and batter 695734 to first, both event index 6 | Two separate Safe Processes, each linked to its own resolved runner and base, settle the same Walk Process. |
| `samples/2026-08-25/823016.json`, PA 39 | HBP; 691723 second to third, 687952 first to second, batter 681047 to first, all index 1 | Three separate resolutions settle the same HBP award, subject to corroborating the complete forced chain. |
| `game-566279.json`, PA 12 | 488671 first to second on balk at index 5; batter 518876 walks at index 6 | The balk resolution does not settle the later walk. Both safe destinations can be represented independently. |
| `game-566279.json`, PA 23 | 606466 steals first to second, then scores on the single | Two resolution events; a final score uses Run Process, not Safe Process at Home Plate. |

Raw SHA-256 pins:

- `data/raw/game-566279.json`: `e36caf73ff54d6eeac29dba350d5d37001e769eaaf4c1a9e5eac4763ad2630c2`
- `data/raw/samples/2026-08-25/822693.json`: `c2701c7de786df80013b21b36d74e8c5d6f6b1d0063bfab86d83ce6f5fb5fe02`
- `data/raw/samples/2026-08-25/823016.json`: `a443116b6a3be5f3f4b3eb1b623a352ecffd198d9f9cb921cf4d9cac8af9c15d`

For `hasAdjudicatedBase`, require an admitted Safe Process, a known resolved
runner, `isOut` exactly false, and an unambiguous terminal first/second/third
base for that resolution. Unknown and null destinations produce no link.
The same token on an out row is not a safe destination. Preserve the source
record's aboutness links to the resolution and decision as evidence.

For `settlesAwardFrom`, require the particular admitted Walk/HBP Process,
matching runner identities, unambiguous event association, and direct award
or corroborated forced-advance evidence. Matching labels alone is insufficient.
For a forced runner, corroborate each occupied base in the forcing chain
and advancement to the awarded next base. Missing rows cannot prove an
unoccupied base. An overshoot, later out, independent advance or mixed
reason is not completion at the awarded base merely because the PA ends
in a walk. Interference, uncaught third strikes and ambiguous mixed awards
remain outside this bounded proposal.

## Proposed conformance obligations after acceptance

1. Every resolution using these links has exactly one resolved runner, typed
   Person, also a participant of that resolution. Do not impose this constraint
   retrospectively on all earlier graphs before their per-game replacement.
2. Every adjudicated-base link has a Safe Process subject and the particular
   first, second or third Base as object in the same game/field context.
   Require exactly one destination for an admitted destination-complete
   resolution. Unknown legacy destinations are not silently filled.
3. Every award link has an admitted Safe or Run Process subject and a
   Walk/HBP Process object in the same Game and PA. Its source record must
   support the same resolved runner and the awarded arrival.
4. The graph may contain independent resolutions in the same PA without
   an award link. A missing link means unasserted, not a proved negative.
   Analytical admission requires positive evidence or a separately reviewed
   completeness contract.
5. A Safe Process at Home Plate does not replace a counted Run Process.
   Multiple runners settling one award remain separate resolutions; the
   award itself is not counted as another run, out or trajectory.

These obligations belong in source SHACL after acceptance. Identity, source
mechanics and fixture extraction may be checked by supporting code; semantic
constraints must not be duplicated as imperative graph-review code.

## What this resolves and what it does not

This provides concrete A2 award and A4 safe-destination relations. It also
specifies their temporal scope without inventing a persistent institutional
state. It does **not** claim that these links finish TFS/PAQ-2.

A3 still needs a reviewed graph assertion for progression immediately before
the consequence. A prior Safe Process is a historical adjudication, not
proof of unchanged state until a later event. `movement.start` remains
unresolved for that stronger assertion. A5/A6 additionally require operative
out identity, complete participant coverage, simultaneous-event treatment
and inning-ending/walk-off policy. No metric will treat these missing claims
as zero or carry state forward from absent rows.

Accepting this named three-relation slice would authorize its ontology,
source-specific Mermaid, targeted RML, SHACL and one-game proof through the
existing per-game replacement lane. It would not approve the unresolved
initial-state or metric-policy decisions. There is no dataset reset or new
pipeline topology in this proposal.
