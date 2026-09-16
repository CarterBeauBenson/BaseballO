# Proposed C3 identity and source-selection contract

Reuse the accepted personal BFO Process, Person, Half Inning, Temporal Interval
and Runner Resolution Episode pattern. The existing history key remains the
SHA-256 of compact JSON `[gamePk, runnerId, entryAnchor, terminationAnchor]`.
Existing pitch-based histories retain their current anchors and identities.

The following are proposed **serialization tokens**, not new RDF nodes,
predicates, ontology classes or claims of strict temporal precedence.

| Boundary | Proposed anchor token | Required source reconciliation |
| --- | --- | --- |
| Non-pitch runner terminal outcome | `action/{actionPlayId}/{eventType}/{outcomeRunnerId}` | Unique supported action record and exact runner movement join; supported final out/score; stable association ID; no unresolved review |
| Pinch-runner replacement | `replacement/{inning}/{half}/{outgoingPersonId}/{incomingPersonId}` | Explicit PR substitution, distinct known Persons, outgoing active runner at the reported base, incoming not active, exactly one such replacement in the owning game |
| Placed-runner entry | `placement/{inning}/{half}/{personId}` | Explicit runner-placed record at second, known Person, regular-season extra inning, unique entry before the half's first actual play, no conflicting initial occupancy |

`half` is `top` or `bottom`. Game scope is already in the outer key. Person
IDs identify the existing source-owned Persons. PA numbers, event array
positions, timestamps, base numbers and current source hashes are not identity
components. They remain evidence or joins where appropriate.

## Non-pitch outcomes

`actionPlayId` can refer to an associated pitch. It is not globally unique
action identity. The full action token must be unique in the exhaustive game
inventory and must match one reconciled outcome for its named runner. If two
distinct records share that token, withhold; do not append an array index.
For a supported third out, the same action boundary can terminate other
still-active histories as stranded, without adding an Out to those histories.

Pitch event counts and action event counts have different observed scopes.
Reconcile a non-pitch action's reported post-out count against distinct runner
out ordinals and the prior state. Do not silently subtract one or assume every
action adds one out. Preserve independently supported temporal bounds; ordered
source records alone do not establish BFO precedence.

## Replacements and placements

An explicit PR boundary finishes the outgoing personal whole and starts the
incoming person's distinct whole. Earlier episodes stay with the outgoing
Person. A placement begins a new whole in that half; it does not continue the
Person's history from an earlier inning. Do not attach the administrative
record as a fictional baserunning act, credited advance or Safe decision.

Administrative observation bounds may straddle a PA header. Admission requires
the replacement/placement boundary to be separable from the earlier and later
state-changing evidence, using its full source context. Do not truncate its
timestamp to the PA header or claim that the observation is an exact physical
instant. An uncertain boundary keeps the affected history withheld.

This bounded implementation requires at least one independently supported
Runner Resolution Episode in a selected personal whole. A zero-episode history
remains an explicit gap; do not manufacture an episode or omit that lifetime
from a supposedly complete population. An outgoing/incoming administrative
base field alone does not authorize a new PA-start location stasis or reverse
projection from a later origin. Separate boundary admission remains required.

## Corrections and proof

Compare the previous source manifest's selected lifetimes and source witnesses
before emitting replacements. Unchanged anchors retain existing keys. A change
that makes Person, entry/termination correspondence or episode allocation
ambiguous is quarantined for review; it is not silently assigned another key.
A source correction's new hash alone neither changes nor proves identity.

For each selected history retain the exact source pointers, anchor form,
participant, episode inventory, temporal evidence bounds and terminal kind in
the manifest. Source-owned generated SHACL must require the exact selected
graph membership and reject extra/misattributed histories. Every source
lifetime, including unresolved and zero-episode cases, remains in the census.
Proof sidecars must stay bound to the promoted source/RDF/implementation hashes.
