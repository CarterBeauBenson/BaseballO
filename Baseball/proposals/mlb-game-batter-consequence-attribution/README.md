# Batter-consequence attribution for graph-native metrics

Status: **partially accepted; remaining semantic design under review**. Prepared 2026-09-08 from the
next deliverable in the [metrics roadmap](../../sparql/metrics/README.md).
The ontologist approved the targeted fix. The concrete A1 contact-play
parthood slice is recorded in a
[separate accepted decision](../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md).
The three accepted relations now make the destination and walk/HBP award
links concrete in [resolution-links-review.md](../../archive/design-records/mlb-game-resolution-award-links/resolution-links-review.md).
Their acceptance is recorded separately; ontology, RML and SHACL implementation
now reuse existing runner-resolution and Base identities.
The [accepted origin relation](../../archive/design-records/mlb-game-baserunning-origin/README.md)
also links a particular supported Baserunning Act to its starting Base.
Complete pre-consequence state and full metric completeness remain unresolved.

This package asks how a plate appearance's batter-linked consequences can be
distinguished from independent runner events. It is the prerequisite for TFS,
PAQ-2, Offensive Reach, Hidden Help, Rally Kill, and Opportunity Erosion.

## Read the review

1. [Source evidence and current RDF paths](source-evidence.md).
2. [Field selection and de-duplication inventory](field-selection-inventory.md).
3. [Source-independent candidate shapes](source-independent-mermaid.md).
4. [Competency questions and decisions](competency-questions.md).
5. [Minimal-change implementation boundary](minimal-change-plan.md): reuse
   per-game replacement; no separate mapping or dataset reset. The current
   replacement mechanism is recoverable, not an atomic two-graph swap.
6. [Runner-state modeling review](state-modeling-review.md): the confirmed
   physical-location meaning of the existing stasis and the remaining
   institutional base-association gap.
7. [Concrete resolution and award links](../../archive/design-records/mlb-game-resolution-award-links/resolution-links-review.md): the
   three accepted relations, temporal scope, forced-walk/HBP evidence,
   negative cases and their SHACL obligations.
8. [Baserunning origin](../../archive/design-records/mlb-game-baserunning-origin/baserunning-origin-review.md): the accepted
   act-to-origin relation, with real steal-then-partial-advance evidence.
9. [Metric boundary contract](metric-boundary-contract.md): accepted release,
   error/FC and inning-ending policies, exact examples and remaining gates.

## Findings that affect the design

The [unchanged/stranded-runner evidence](boundary-state-evidence.md) records
eight concrete PA excerpts and the remaining time-qualified association gap.
The [shared-play erosion decision](../../archive/design-records/tfs-shared-play-erosion/README.md)
accepts actual end-state context for its bounded simultaneous-event case.
The [current location review](boundary-temporal-vocabulary.md) follows the user's
nested-site direction: preserve the Base Site, locate it in the larger Site,
and locate the runner in that larger Site. The Quality candidate is withdrawn.
Mermaid remains unchanged; larger-Site identity and temporal evidence stay open.

- The checked-in game 566279, PA 23, contains a steal from first to second
  followed by a single that scores the same runner. PA-start occupancy cannot
  stand in for the state immediately before the single.
- Game 822693, PA 36, contains a strikeout and wild-pitch advances at the same
  event index. Joining runner records to the terminal event is insufficient
  to establish batter attribution.
- Game 823826, PA 78, includes advances labeled `strikeout`, a null batter
  placeholder, and a safe batter resolution labeled `wild_pitch`. Matching
  provider result labels is also insufficient.
- The original destination-link gap is addressed by the accepted
  `hasAdjudicatedBase` mapping for supported Safe runner resolutions.
- `BaserunnerAtBaseStasis` is defined specifically at PA start. Reusing it at
  an arbitrary later event boundary would change its accepted meaning.
- Contact-play parthood, physical causation, and analytical batter credit are
  distinct claims. In particular, HBP does not establish that the batter
  caused the pitch to hit him.

## Review boundary

Decision A1 accepts adding supported runner resolutions as parts of the
existing Batted-Ball Play Process. This is a structural assertion;
it does not make every part of that process batter credit. A2-A6 address
non-contact consequences, event-boundary state, destination, completeness,
and operative adjudication. The final section of the source-independent
diagrams now records the accepted destination and award links; the other gaps remain.
The user's approval is for implementing the fix, not merely documenting the
stasis explanation. It does not fill an unspecified graph pattern with an
invented ontology term or relation.

The user has now accepted the percentile display, reference population,
exact internal precision, error/FC progress exclusion and inning-ending
erosion choices. Their separate decisions are linked in the metric boundary
contract. They do not approve the remaining continuity and completeness graph pattern.

After review, follow the existing sequence: record the named decisions,
implement accepted ontology/identity changes if needed, prepare the
source-specific design and RML, encode graph constraints in source SHACL,
prove a fixture and one game, then submit bounded NiFi work. An unresolved
field stops at its gate. This review changes no runtime artifact or schedule.
