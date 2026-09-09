# Runner location and institutional base association

## Confirmed clarification, 2026-09-08

The user subsequently clarified that approval applies to implementing the
targeted fix, not merely this explanation. The concrete contact-play
parthood slice is now
[recorded separately](../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md).
In the existing `base:BaserunnerAtBaseStasis`, the persisting condition is the runner's
location at the site occupied by a particular Base, during an interval at
the beginning of a Plate Appearance. The stasis does not realize the
Baserunner Role.

The targeted fix preserves this existing class meaning. It does not supply
a new institutional-state class, a broader stasis definition, a destination
relation, or a complete attribution pattern through this note. The unresolved
state pattern remains distinct from the accepted contact-play structural change.

## Vocabulary assessment

Definitions and restrictions were checked in
[`BaseballO.ttl`](../../ontology/BaseballO.ttl),
[`BaseballO-axioms-overlay.ttl`](../../ontology/BaseballO-axioms-overlay.ttl),
and the pinned
[`CommonCoreOntologiesMerged.ttl`](../../ontology/CommonCoreOntologiesMerged.ttl).

| Existing term | What it expresses | Remaining limitation |
| --- | --- | --- |
| `base:BaserunnerAtBaseStasis` | Persistence of runner location at a Base Site at PA start | Physical location is distinct from the institutional runner-to-base association needed by the metric. Its definition does not cover arbitrary consequence boundaries. |
| `base:BaserunnerRole` | A persistent Role realized in advancing among bases or avoiding an out | First, second and third do not constitute different identities of this career-persistent Role. The Role alone supplies no particular base association. |
| `cco:ont00000824` (Stasis of Role) | Persistence of an Independent Continuant bearing an unchanged Role during a Temporal Interval | Persisting in the Baserunner Role does not distinguish which base applies. |
| `base:BaserunningAct` | A Baserunner Act directed toward advancing, retreating or remaining legally associated with bases | An act's direction does not establish its achieved institutional result. The phrase in its definition does not provide an executable relation to a particular Base. |
| `base:SafeProcess` | An adjudicated runner resolution counting the runner safe | The current graph still needs an explicit, reviewed account of the particular institutional destination. |
| `base:SafeDecisionICE` | Content expressing that a runner is counted safe in the adjudicated situation | Adding aboutness to a runner and a Base would not by itself supply the missing world-side relationship or its temporal scope. |
| `cco:ont00000751` (Action Permission) | A Process Regulation permitting a Process | This is a prescriptive ICE. It does not replace the runner, Base, institutional relationship, or its persistence. |
| `cco:ont00000819` (Stasis) | A Process in which Independent Continuants endure in an unchanging condition | The relevant condition must first be identified and expressible. Merely naming a generic stasis does not model it. |

## Remaining A3/A4 boundary

The missing assertion concerns a particular runner's institutionally recognized
association with a particular base at a particular point in a Game. Its
world-side category, grounding relation, and temporal scope remain unresolved.
No new Role, Quality, Stasis or ICE subclass is proposed. The subsequent
[resolution-link proposal](../../archive/design-records/mlb-game-resolution-award-links/resolution-links-review.md) supplies a narrower
accepted relation: an event-scoped Safe-Process-to-Base relation. It expresses the
adjudicated destination without claiming an interval of persistent entitlement.
It does not resolve the stronger immediate-before assertion.

A state observed at one event boundary also does not establish a nonzero
interval of persistence. A reviewed temporal account must distinguish a
boundary observation from evidence that the condition continued between
events. The metrics must not obtain that continuity from missing runner rows.

Any eventual pattern must distinguish these cases:

- Physical movement away from a base site while the institutional association
  remains applicable.
- Institutional advancement to another base without changing the persistent
  Baserunner Role's identity.
- A safe adjudication whose particular base is known, versus safe status for
  which destination evidence is missing.
- A source observation at a boundary, versus an evidenced persistence interval.
- Replacement by a pinch runner, where a different Person becomes relevant.

Implementation of the unresolved state assertion stops at this modeling boundary. The confirmed
physical-location clarification does not license filling it with labels,
aboutness links, inferred physical touching, or a stasis of unspecified status.
