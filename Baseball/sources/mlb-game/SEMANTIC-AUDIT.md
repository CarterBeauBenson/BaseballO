# MLB game RML semantic audit

Original audit: 2026-08-28

Disposition update: 2026-08-31

Scope: active `mlb-game.rml.ttl` before further MLB game-field expansion

## Verdict: current pinned semantic surface accepted

The original pass found thirteen blockers in the then-active mapping. The
ontologist reviewed and accepted the corrected current RML contract on
2026-08-31. Its implementation now keeps source records, Identifier ICEs,
nominal classifications, real-world acts and processes, adjudication, temporal
structure, and the rebuildable current-state index distinct. Provider display
coordinates no longer mint world-side Sites. The accepted contract is approved;
future fields, deferred measurements, coordinate grounding, and other sources
still require their own proposal-first review.

The accepted decision was recorded and pushed before its executable
consequences. Historical text below is retained as performance and curation
evidence; the disposition subsection identifies the corrections now in force.

## Evidence reviewed

- 326 triples maps across 87 logical sources and 152 asserted subject classes.
- Separate game, inning, half-inning, plate-appearance, pitch, contact,
  batted-ball-motion, batted-ball-play, runner-resolution, adjudication, and
  replay-review individuals.
- Persistent people and teams are separated from the roles they bear and the
  acts in which those roles are realized.
- A pitch act is separated from ball motion; swing or bunt is separated from
  bat-ball contact; contact is separated from later ball motion and the
  institutional result.
- A judgment act is separated from its decision ICE, the institutional process
  being decided, the call act, and the source event record.
- Identifier, name, record, and timestamp ICEs have explicit designation or
  aboutness instead of substituting for their referents.
- MLB pitch and batted-ball measurements remain deferred because approved
  world-side measurement patterns and coverage are not yet complete.

Fixture and bounded-corpus counts from the 2026-08-28 audit are historical
baselines, not the expected counts after the accepted correction.

## Accepted 2026-08-31 dispositions

- **MLB-GAME-001:** `playId` is carried by an Identifier ICE that designates the
  source event-record ICE; the record is separately about the Pitch Act.
- **MLB-GAME-002:** a plate-appearance-start out count is derived from the
  preceding recorded Out Processes in the same Half Inning and describes that
  inning at the plate-appearance start boundary.
- **MLB-GAME-003:** unresolved provider coordinates are not mapped into a
  Coordinate ICE, Reference System, or world-side Site. The future grounding
  question remains outside the accepted executable contract.
- **MLB-GAME-004:** an overturn establishes that an original Decision existed,
  but the mapping no longer manufactures its content or an inverse transition.
- **MLB-GAME-005:** provider routing tokens are nominal classification evidence,
  not direct record identifiers or RDF types. Current class assertions are
  selected only in the rebuildable query index.
- **MLB-GAME-006:** passed ball and wild pitch remain institutional scorer
  classifications; they no longer mint a physical
  `PitchBallControlFailureProcess`.
- **MLB-GAME-009:** MLB bunt-attempt pitch codes and in-play bunt trajectories
  create `BuntAct` and are excluded from `SwingAct`; `sac_bunt` remains a result
  classification.
- **MLB-GAME-010:** genuine play structure creates a PlateAppearance, while
  completion plus result evidence separately gates its institutional result.
  Administrative pseudo-plays are excluded.
- **MLB-GAME-011:** runner `movement.end` is retained as an institutional
  destination state and does not mint physical `BaseTouchingProcess` instances.
- **MLB-GAME-012:** a terminal baseball event supplies the game endpoint only
  when Final or a game-over transition corroborates termination; it need not be
  a final out or completed plate appearance.
- **MLB-GAME-013:** games are occurrent parts of reviewed season-phase
  Processes, including the All-Star phase, and each phase is an occurrent part
  of its Baseball Season. Provider game-type codes remain nominal evidence.

## Historical findings and their migration decisions

The numbered findings below are preserved as curation evidence showing what the
2026-08-28 audit detected. They are not open blockers on the accepted pinned
contract. Entries concerning deferred measurements or provider-coordinate
grounding describe work that remains outside that contract and must re-enter
through a new proposal.

1. `PitchActMap` carries a direct `dcterms:identifier`, unlike the explicit
   Identifier ICE pattern used for games, teams, players, and venues. This is a
   consistency issue, not a measurement collapse; changing it requires an
   approved migration and baseline update.
2. `PlateAppearanceStartOutCountICE` carries a synthesized integer while being
   about the plate appearance, without an approved world-side count/status or
   counting pattern. The dependent Empty Games damage grain makes this a data
   and UI migration decision, not merely a class-name cleanup.
3. Batted-ball coordinate and location individuals are emitted when coordinate
   source fields exist, but no coordinate values are emitted. Disable that
   partial pattern or complete an ontologist-approved geometry model; do not
   treat the existence of fields as support for a valueless location entity.
4. Overturned replay reviews synthesize the opposite original decision and a
   transition class even though the replay design record still marks that
   closed-domain inference unresolved. Retain only directly supported review
   structure unless the inference rule is explicitly approved.
5. Shared event, review-status, and pitch-call tokens are used as
   `dcterms:identifier` or `dcterms:type` values on record individuals. Review
   them as classifications/data elements rather than record identities.
6. Passed-ball and wild-pitch runner tokens plus a nearest-pitch association
   gate creation of a physical `PitchBallControlFailureProcess`. The evidence
   and identity rule for that physical process requires explicit review.
7. Event records may be about several entities. Each aboutness assertion must
   remain source-supported and must not be used as a shortcut for a missing
   real-world relation.
8. Deferred measurements must stay deferred until the ontologist approves the
   world-side quality, measurement process, unit, estimate, and ICE pattern.
9. The bunt gate collapses batting-act kind into the terminal plate-appearance
   result. `prepare-rml-context.py` sets `plateAppearanceIsSacBunt` only when
   `result.eventType` is `sac_bunt`; `InPlayOutSource`,
   `InPlayNoOutSource`, and `InPlayRunsSource` therefore send every other
   in-play pitch to a `SwingAct`, while `BuntSource` admits only sacrifice-bunt
   plate appearances. The mapping-validation samples contain seven
   non-sacrifice `bunt_grounder` events that this rule treats as swings. They
   also contain 28 `W` (swinging strike blocked), 11 `L` (foul bunt), and three
   `M` (missed bunt) pitch calls that the current swinging-strike, foul, swing,
   and bunt logical sources do not cover. This is an active false world-side
   classification, not merely missing feed metadata, and it affects downstream
   swing, grind, and Good At Bat facts. Review the source evidence and batting-
   act identity rules before changing the gate; then migrate authoritative RDF,
   rebuild derived layers, and regenerate fixture and corpus evidence.
10. `PlaySource` iterates every `allPlays` member without requiring a completed
    plate appearance. It drives `PlateAppearanceMap`, `BatterActMap`,
    `PlateAppearanceResultMap`, the result record, and the result adjudication
    and decision maps. In checked source game `824807`, `atBatIndex` 50 is an
    incomplete `game_advisory` whose description is a rain-delay status change
    and which has no pitches or runner records. The current mapping nevertheless
    turns that feed container into a plate appearance and terminal
    institutional result. This conflicts with the existing action-event gap,
    can alter plate-appearance and Good At Bat counts, and demonstrates that the
    unseen-event policy is too broad. Incomplete and advisory records must be
    deferred from complete plate-appearance/result structures unless the
    ontologist approves a distinct real-world pattern. Runner-only `allPlays`
    results also require an explicit identity review before they are assumed to
    be plate-appearance results. Any correction requires authoritative RDF and
    derived-layer migration plus regenerated evidence.
11. `RunnerReachBaseTouchingMap`, `RunnerAdvanceBaseTouchingMap`,
    `RunnerScoreOriginHomeTouchingMap`, and
    `RunnerScoreBaseHomeTouchingMap` create a physical
    `BaseTouchingProcess` from a runner record's institutional `movement.end`
    state. The ontology definition requires actual physical contact with a
    base, while the module IRI policy already prohibits minting actual
    rule-satisfying processes merely because MLB records an institutionally
    counted outcome. Retain the source-supported baserunning act and
    institutional safe, out, or run resolution, but do not treat the end-state
    token alone as evidence of physical contact. Disposition requires
    ontologist review and a migration/backfill decision.
12. `prepare-rml-context.py` always copies the last `allPlays` member's
    `about.endTime` into `gameEndTime`, and `GameEndInstantMap` plus
    `GameEndTimestampMap` assert that value as the game's end. The last member
    can be an incomplete administrative record: in game `824807` it is the
    rain-delay advisory described above. Its event end is not evidence of the
    official termination instant of a rain-shortened game. Keep the game
    interval end open unless selected source evidence supports game
    termination, or obtain approval for a documented derivation rule. Changing
    the current rule requires authoritative RDF and derived-layer migration and
    regenerated temporal evidence.
13. The source exposes an MLB game-type code, including `A` for checked
    All-Star game `823443`, but the active mapping emits no game-type or
    competition-classification fact. The SQL serving layer therefore obtains
    its regular-season/All-Star partition from compact acquisition provenance
    plus checked historical schedule evidence, and handles mapper fixture
    `566279` through a separate hard-coded corpus label. Do not infer game type
    from participant team IDs, labels, dates, or absence. Review a realist game/competition
    classification pattern, map the accepted source evidence into
    authoritative RDF, and backfill it before claiming that the SQL layer is
    rebuildable from RDF alone. Keep development-fixture membership distinct
    from the type of game in the world.

## Query source-scope enforcement finding

The version 2 source-scope catalog assigns the intended read and write layers
to all current query roles, but the single-source declaration is not yet
enforced by 35 authoritative query texts. Six root hit queries, six baserunning
queries, nine batting queries, seven games queries, and seven pitching queries
use an unrestricted `GRAPH ?graph` without constraining it to the MLB-game
authoritative graph namespace. They can therefore match a future promoted
source or reasoning graph that uses the same ontology terms.

The Explorer server's compiled authoritative fallback is separately protected:
it requires the MLB-game graph-prefix guard and injects a date-scoped
`VALUES ?graph` binding before execution. The finding here concerns the 35
cataloged static query artifacts and the catalog validator; it is not a claim
that the current compiled Explorer fallback is unguarded.

`validate_repository.py` currently detects any non-index-benchmark
`GRAPH ?graph` as `authoritative-rdf` based on the query's repository path; it
does not prove which authoritative source graph the variable can bind. Before
the catalog is treated as an enforced disconnect boundary, each single-source
query needs an explicit graph namespace constraint or an equivalent runtime
graph binding, and validation must check that restriction. This is a SPARQL
contract change, not permission to modify query behavior during this audit.

## Gate for completing the MLB game API

For each missing field or coherent field family:

1. prove it is useful, source-supported, and not already represented;
2. identify its real-world referent and identity scope;
3. document duplicates, derivability, null behavior, units, and provenance;
4. draw source-independent Mermaid shapes and obtain ontologist review;
5. record ontology gaps without inventing workaround classes or properties;
6. only after approval, add source-specific Mermaid and RML in this module;
7. validate one record and one complete game semantically before corpus work.

Passing syntax, SHACL, or a fast transformation never overrides this gate.
