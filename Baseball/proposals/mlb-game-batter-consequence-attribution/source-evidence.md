# Evidence and existing graph paths

This inventory records the mapping examined before the A1 extension. The
contact-play connection has since been implemented under the
[separate accepted decision](../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md).
The remaining state and destination limitations below still apply.

This is a static review of checked-in source bytes and executable definitions,
not a claim that a new graph pattern has passed RML or SHACL. The inspection
covered the original fixture and the 2026-08-25 sample directory (16 game
payloads in total, plus one schedule file). No source bytes were changed and
no live acquisition or transformation was run.

## Source anchors

JSON paths below are relative to `liveData.plays.allPlays[N]`; in the cited
examples `N` also equals `about.atBatIndex`. Runner row numbers are zero-based.

| File | SHA-256 |
| --- | --- |
| [game-566279.json](../../data/raw/game-566279.json) | `e36caf73ff54d6eeac29dba350d5d37001e769eaaf4c1a9e5eac4763ad2630c2` |
| [822693.json](../../data/raw/samples/2026-08-25/822693.json) | `c2701c7de786df80013b21b36d74e8c5d6f6b1d0063bfab86d83ce6f5fb5fe02` |
| [823826.json](../../data/raw/samples/2026-08-25/823826.json) | `1c2f05b2a5dc3a806a348ff45bed3e1b2d8d1e32c70d7f52509bec6c15d9237e` |
| [822773.json](../../data/raw/samples/2026-08-25/822773.json) | `fa98482cc0ddb8760e77864cd7225ecac498ba8ee86b5a7bfcb8a1753483353d` |

| Game / PA | Observed evidence | Design implication |
| --- | --- | --- |
| 566279 / 2 | Batter row 0 ends safely at `2B`; result `double` | Destination is supplied by MLB; its missing RDF link is mapping-coverage debt. |
| 566279 / 4 | Batter row 0 ends safely at `1B`; result `walk` | Non-contact path is required independently of contact-play structure. |
| 566279 / 15 | Two out rows, both event index 2; `outNumber` 2 and 3 | Count distinct operative outs, not the result label plus the runner rows. This is a one-out-start example, not the zero-out GIDP metric fixture. |
| 566279 / 22 | Batter out and runner from third scores on `sac_fly` | A batter out and another participant's counted run must remain separate. |
| 566279 / 23 | Runner 606466: row 0 `1B -> 2B`, stolen base, index 5; row 2 `2B -> score`, single, index 7 | Separate the independent segment; the single's immediate start base is second. Its completion score alone would not expose the wrong start base, so also test a steal followed by a partial advance. |
| 566279 / 40 | Three runner rows share index 5; labels include `fielders_choice` and `error` | Same contact-play membership does not settle treatment of the error-related advance. |
| 822693 / 36 | Row 0 strikeout; rows 1 and 2 wild-pitch advances `2B -> score` and `1B -> 3B`; all index 4 | Same event index cannot distinguish independent consequences; simultaneous out/advance ordering also affects erosion. |
| 823826 / 78 | Row 0 steal; rows 1 and 2 advance with label `strikeout`; row 3 batter `isOut: null`; row 4 batter safe at first with label `wild_pitch` | Neither result-label equality nor a strikeout label proves attribution or an out. Preserve the unresolved placeholder without inventing a resolution. |
| 822773 / 60 | Batter safely reaches first, `hit_by_pitch` | Supports a non-contact example; it is not a fixture proving forced runner advances. |

## Existing RDF inventory

Map names are stable search anchors in
[`mlb-game.rml.ttl`](../../sources/mlb-game/mapping/mlb-game.rml.ttl).
These are observed executable paths on the current accepted surface.

| Required structure | Current map/path | Limit for the new metrics |
| --- | --- | --- |
| PA and batter | `BatterAct` is occurrent part of `PlateAppearance`, has the batter as participant, and realizes the persistent Batter Role | Keep this common event grain and persistent role identity. |
| Contact play | `BattedBallPlayMap`: play has occurrent parts contact and ball motion; `TerminalBattedBallPlayResultContainmentMap`: also fair-ball process and terminal PA result | Runner resolutions are not connected to this container by these maps. |
| Runner and resolution | `RunnerOutResolutionMap`, `RunnerReachResolutionMap`, `RunnerAdvanceResolutionMap`, and score variants: resolution has participant runner, is preceded by Baserunning Act, and is part of PA | Temporal order and PA containment do not assert causation or credit. |
| Runner provenance | Runner record `cco:ont00001808` (is about) resolution, judgment, decision; structural identity uses PA index plus runner-row index | Several records for one runner do not by themselves prove one continuous consequence. |
| Start outs | `PlateAppearanceStartOutCountMap`: ICE is about PA and carries `_baseballO.outsBefore` | PA-start count does not account for a later independent out before the batter result. |
| Start occupancy | `BaserunnerAtBaseStasisMap`: stasis has runner, Base, and Base Site as participants; occupies interval anchored to PA start | Existing class definition is limited to PA start; arbitrary boundary reuse is blocked. |
| Safe destination | `ReachedBaseArtifactMap`, `AdvancedToBaseArtifactMap`: mint Base from `movement.end` | No resolution-to-destination edge in these maps. Neither IRI parsing nor a physical base-touch assertion repairs this. |
| Out and run | Explicit `OutProcess` and `RunProcess` resolutions and their judgments | Need reviewed attribution, operative identity, and complete distinct out/run evidence. |
| Steal | `StolenBaseAttemptOverlayMap`, `StolenBaseProcessMap`, `StolenBaseRecordMap` | A shared record can describe both safe advancement and scorer classification; do not count them as two advances. |
| Wild pitch / passed ball | Separate institutional scorer classification and decision patterns | They do not assert a physical control-failure process or establish batter causation. |
| Replay | On-field judgment/decision, review input/output, replay decision and disposition | A PA-level review is not automatically the operative decision for every runner resolution in that PA. Unknown original content remains unknown. |

[`prepare-rml-context.py`](../../scripts/pipeline/prepare-rml-context.py)
currently resolves `details.playIndex` for passed-ball/wild-pitch classification
and maintains structural runner-row identity. That special-case join must not
be generalized into attribution by matching every row to a pitch. Some source
events have no `playId`, and an event index can contain mixed consequences.

The existing
[`productive-plate-appearances.rq`](../../sparql/advanced/productive-plate-appearances.rq)
explicitly measures association and disclaims official credit. It is not an
attribution contract for PAQ-2.

## Accepted relation candidates and limits

The local [CCO dependency](../../ontology/CommonCoreOntologiesMerged.ttl)
defines `cco:ont00001803` (is cause of) between occurrents. This is available
vocabulary, but selecting a causal subject and supporting its consequence
still needs review. Batter benefit or metric credit is insufficient evidence.

`obo:BFO_0000117` / `obo:BFO_0000132` express occurrent parthood;
`obo:BFO_0000063` / `obo:BFO_0000062` express temporal precedence.
Neither relation entails causation. CCO `has output` (`ont00001986`) ranges
over continuants, so it cannot connect a result Process to another Process as
an expedient consequence edge. It remains appropriate for judgment-to-ICE.

The [domain definitions](../../ontology/BaseballO.ttl) and
[overlay](../../ontology/BaseballO-axioms-overlay.ttl) provide the existing
Contact, Batted-Ball Play, Runner Resolution, Judgment, Decision, Base and
Base Site anchors. They do not settle the unresolved pattern decisions below.
