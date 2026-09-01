# Complete 31-class repair inventory

This inventory is class-level because the package repairs existing TBox debt;
it does not select new API fields. “Retain” means retain the existing IRI as a
candidate only. Nothing in this table approves an executable mapping. The
coordinate rows and physical ground-ball semantics remain unresolved where
source evidence does not establish the full proposed differentia.

| # | Existing class | Current debt | Proposed sole direct named parent | Proposed base-taxonomy and annotation repair | Proposed overlay treatment | Evidence status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `AwayBaseballTeam` | Missing example/note | `base:BaseballTeam` | Preserve the class; define it as a Baseball Team bearing an Away Team Role; add context-limiting comment and example. | Equivalent intersection of Baseball Team and bearer of some Away Team Role. | Existing role-defined term; no new field. |
| 2 | `AwayTeamRole` | Missing example/note | `base:BaseballGameTeamRole` | Preserve the game-scoped role; add comment and example. | Necessary inherence in a Baseball Team; game realization inherited from the parent. | Existing source-supported game role. |
| 3 | `BallAffirmingBaseballReplayReviewAct` | Two named parents | `base:BallJudgmentAct` | Remove the direct Affirming parent; retain the accepted definition and complete annotations. | Existing decision-pattern intersection; membership in Affirming group inferred by union. | Accepted replay design; occurrence mapping remains separately frozen. |
| 4 | `BallToStrikeBaseballReplayReviewAct` | Two named parents | `base:StrikeJudgmentAct` | Remove the direct Overturning parent; retain the accepted definition and annotations. | Existing input/output intersection; Overturning membership inferred by union. | Accepted replay design; synthetic-original-decision issue unresolved. |
| 5 | `BaseballEventTemporalInstant` | Missing example/note; parent too broad for definition | `obo:BFO_0000203` Temporal Instant | Replace zero-dimensional temporal-region parent; define the instant precisely as a first or last instant of the region occupied by a Process within a Baseball Game; add limitation and example. | First-instant/last-instant union over a Temporal Region that is temporal region of a Process occurrent part of a Baseball Game. | Existing temporal term; source timestamps still require boundary evidence. |
| 6 | `BaseballFieldCoordinateICE` | Dangling parent; ungrounded; missing example/note | `cco:ont00000686` Designative Information Content Entity | Define an ordered coordinate-content entity that designates a field-relative Site; add direct-value warning and example. | Designates some Site and directly uses some Baseball Field Coordinate Reference System ICE. Literal representation remains withheld. | **Unresolved for executable use:** axes, units, origin, value representation, and provider meaning are unapproved. |
| 7 | `BaseballFieldCoordinateReferenceSystemICE` | Dangling parent; ungrounded; missing example/note | `cco:ont00000275` Spatial Reference System | Define a field-relative Spatial Reference System; add a non-geospatial warning and example. | Remove the current inverse `prescribes Coordinate ICE` pattern; the Coordinate ICE directly uses this reference system under the shared foundation. | **Unresolved for executable use:** provider coordinate semantics unapproved. |
| 8 | `BaseballGameTeamRole` | Missing example/note | `obo:BFO_0000023` role | Preserve game-scoped team role; add comment and example. | Inheres in some Baseball Team and is realized in some Baseball Game. | Existing source-supported role. |
| 9 | `BaseballGameTemporalInterval` | Missing example/note; parent too broad for definition | `obo:BFO_0000202` Temporal Interval | Replace one-dimensional temporal-region parent; add continuity/evidence comment and example. | Is temporal region of some Baseball Game. | Existing temporal term. |
| 10 | `BaseballTeam` | Missing example/note | `cco:ont00001180` Organization | Preserve parent and definition; add organization-identity comment and example. | No participation existential: an organized expansion team may exist before its first game. | Existing source-supported organization. |
| 11 | `BaseballTimestampICE` | Dangling parent; ungrounded; missing example/note | `cco:ont00000540` Temporal Instant Identifier | Define a temporal-instant identifier for a baseball process; distinguish content from the designated instant and add an example. | Designates some Baseball Event Temporal Instant and directly has a datetime value under the shared foundation. | Existing time content; depends on acceptance of `ice-direct-values-and-units`. |
| 12 | `BaseballVenue` | Missing example/note; current parent broader than proposed genus | `cco:ont00000192` Facility | Define as a Facility bearing a Baseball Game Hosting Function; add venue/site limitation and example. | Bears some proposed Baseball Game Hosting Function; no direct Venue-to-Field-Site relation. | Candidate refinement; ontologist must confirm every intended venue is a Facility. |
| 13 | `BattedBallLocationSite` | Missing example/note | `obo:BFO_0000029` site | Define a real Site for a temporal Process part of Batted-Ball Motion and designate it with coordinate content; do not treat one coordinate as the Site of the entire motion. | Designated by some Baseball Field Coordinate ICE and `is site of` some Process that is occurrent part of a Batted-Ball Motion Process. | **Unresolved for executable use:** current MLB coordinates do not yet establish the Site or temporal part. |
| 14 | `BattedBallMotionProcess` | Two named parents | `base:BaseballPhysicalProcess` | Remove direct CCO Motion parent; retain current genus and annotations. | Anonymous necessary intersection includes CCO Motion, Baseball participant, and predecessor/contact restrictions. | Existing physical-process term. |
| 15 | `DoublePlayProcess` | Dangling parent; ungrounded; missing example/note | `base:BaseballInstitutionalProcess` | Define as an institutional process with two counted Out Process parts; add continuity/evidence comment and example. | Qualified cardinality two on existing `has process part` relation. | Existing result classification; explicit out-part evidence required before mapping approval. |
| 16 | `FoulTipCallICE` | Dangling parent; ungrounded; missing example/note; misleading label | `base:StrikeDecisionICE` | Preserve legacy IRI, relabel “Foul Tip Decision ICE,” define as strike-decision content, and add legacy-IRI comment/example. | Output of some Foul Tip Judgment Act and about some Foul Tip Process. | Existing mapping uses a decision IRI; no call act is entailed. |
| 17 | `FoulTipJudgmentAct` | Missing example/note | `base:StrikeJudgmentAct` | Refine parent and genus; add evidence comment and example. | Preceded by contact and catching; uses existing Strike Rule input relation. | Existing foul-tip adjudication pattern; one-game proof still required. |
| 18 | `FoulTipProcess` | Dangling parent; ungrounded; missing example/note | `base:StrikeProcess` | Define as a counted Strike Process adjudicated as a foul tip; add physical/institutional separation and example. | Has Foul Tip Judgment Act as occurrent part; preceded by contact and catching. | Existing RML already co-types the individual as Strike Process. |
| 19 | `GroundedIntoDoublePlayProcess` | Dangling parent; two named parents; ungrounded; missing example/note | **Blocked; no candidate parent asserted** | Keep the active term frozen. The provider code does not establish the independent institutional criterion or physical ground-ball structure required for a noncircular definition. | **No candidate axiom.** The former Rule/Judgment/Decision cycle is removed. | **Unresolved:** requires source-independent institutional and ground-ball differentiae before ontology repair or mapping expansion. |
| 20 | `HomeBaseballTeam` | Missing example/note | `base:BaseballTeam` | Preserve the class; define it as a Baseball Team bearing a Home Team Role; add context-limiting comment and example. | Equivalent intersection of Baseball Team and bearer of some Home Team Role. | Existing role-defined term; no new field. |
| 21 | `HomeTeamRole` | Missing example/note | `base:BaseballGameTeamRole` | Preserve the game-scoped role; add comment and example. | Necessary inherence in a Baseball Team; game realization inherited from the parent. | Existing source-supported game role. |
| 22 | `ManagerChallengeAct` | Two named parents | `base:ChallengeAct` | Remove direct Manager Act parent; keep accepted genus and annotations. | Equivalent intersection of Challenge Act and Manager Act. | Accepted replay design. |
| 23 | `OutAffirmingBaseballReplayReviewAct` | Two named parents | `base:OutJudgmentAct` | Remove direct Affirming parent; retain accepted definition and annotations. | Existing decision-pattern intersection; Affirming membership inferred by union. | Accepted replay design; occurrence mapping separately frozen. |
| 24 | `OutToSafeBaseballReplayReviewAct` | Two named parents | `base:SafeJudgmentAct` | Remove direct Overturning parent; retain accepted definition and annotations. | Existing decision-pattern intersection; Overturning membership inferred by union. | Accepted replay design; synthetic-original-decision issue unresolved. |
| 25 | `PitchBallMotionProcess` | Two named parents | `base:BaseballPhysicalProcess` | Remove direct CCO Motion parent; retain current genus and annotations. | Anonymous necessary intersection includes CCO Motion, Baseball participant, and predecessor Pitch Act restriction. | Existing physical-process term. |
| 26 | `PlayerChallengeAct` | Two named parents | `base:ChallengeAct` | Remove direct Player Act parent; keep accepted genus and annotations. | Equivalent intersection of Challenge Act and Player Act. | Accepted replay design. |
| 27 | `SafeAffirmingBaseballReplayReviewAct` | Two named parents | `base:SafeJudgmentAct` | Remove direct Affirming parent; retain accepted definition and annotations. | Existing decision-pattern intersection; Affirming membership inferred by union. | Accepted replay design; occurrence mapping separately frozen. |
| 28 | `SafeToOutBaseballReplayReviewAct` | Two named parents | `base:OutJudgmentAct` | Remove direct Overturning parent; retain accepted definition and annotations. | Existing decision-pattern intersection; Overturning membership inferred by union. | Accepted replay design; synthetic-original-decision issue unresolved. |
| 29 | `StrikeAffirmingBaseballReplayReviewAct` | Two named parents | `base:StrikeJudgmentAct` | Remove direct Affirming parent; retain accepted definition and annotations. | Existing decision-pattern intersection; Affirming membership inferred by union. | Accepted replay design; occurrence mapping separately frozen. |
| 30 | `StrikeToBallBaseballReplayReviewAct` | Two named parents | `base:BallJudgmentAct` | Remove direct Overturning parent; retain accepted definition and annotations. | Existing decision-pattern intersection; Overturning membership inferred by union. | Accepted replay design; synthetic-original-decision issue unresolved. |
| 31 | `ThrownBallMotionProcess` | Two named parents | `base:BaseballPhysicalProcess` | Remove direct CCO Motion parent; retain current genus and annotations. | Anonymous necessary intersection includes CCO Motion, Baseball participant, and preceding Throw Act restriction. | Existing physical-process term. |

## Proposed supporting vocabulary

| Class | Direct parent | Why it is required |
| --- | --- | --- |
| `BaseballGameHostingFunction` | CCO Artifact Function | Supplies a realizable, non-actuality-entailing candidate differentia for a Baseball Venue designed for hosting; mere selection or past use is insufficient, and temporary non-designed venues require another reviewed pattern. |

Only this one supporting class remains proposed. The three former GIDP support
classes were circular and are removed rather than used to hide an unresolved
criterion. No new object property is required.

## Explicit exclusions

- Exactly one supporting class IRI and no property IRI are proposed.
- No proposal term is admitted to executable code.
- No MLB, Statcast, weather, or derived-source field is newly selected.
- No coordinate literal mapping is approved.
- No IBE detour is proposed for value, measurement-unit, or reference-system
  assertions. Direct ICE assertions depend on separate acceptance of
  `ice-direct-values-and-units`.
- No source result code alone licenses a physical ground-ball profile.
- No replay-review act class licenses synthesis of an unobserved original
  decision.
