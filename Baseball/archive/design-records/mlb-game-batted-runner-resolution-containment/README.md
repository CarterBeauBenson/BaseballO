# Batted-play runner-resolution containment (A1)

Decision date: 2026-09-08. Scope: the concrete contact-play parthood portion
of the targeted attribution fix approved by the ontologist in the current
conversation. The user clarified: "I mean I approve of your fix to solve this
issue" after the proposed semantic update and stasis distinction were described.

## Accepted structural change

A particular Batted-Ball Play Process may have as an occurrent part a
source-supported Runner Resolution Process belonging to that contact play.
Reuse BFO `has occurrent part` (`obo:BFO_0000117`) and the existing individuals.
Both processes retain the same particular Plate Appearance context. A runner
resolution must not acquire a second contact-play identity from ambiguous
source evidence.

This accepts the A1 structural addition presented in the
[attribution review](../../../proposals/mlb-game-batter-consequence-attribution/README.md).
The requested fix is not limited to documenting the existing stasis, but this
record admits only the concrete structural assertion already described.

## Scope limits

- Parthood does not entail causation or analytical credit. No TFS or PAQ value
  follows from this edge alone.
- Preserve runner-record, runner-resolution, PA, contact-play and persistent
  Role identities. No new ontology term or identity policy is introduced.
- Independent steals, caught stealing, wild pitches, passed balls, balks,
  pickoffs and unclassified evidence must not be assigned contact-play
  membership merely through PA containment or a coincident event index.
- The initial implementation may emit only an evidenced subset. Absence of a
  link means that membership has not been established; it does not establish
  independence or zero contribution.
- Institutional base association, consequence-boundary persistence,
  non-contact award relationships, operative adjudication and metric policy
  remain the separate unresolved portions of the active proposal. The existing
  PA-start physical-location stasis is unchanged.

Git is disabled in this session. This decision is recorded before executable
changes, without a commit or push. Focused component checks and a bounded
NiFi-owned proof must precede any corpus rollout. No corpus rollout is
authorized by treating the incomplete metric design as complete.
