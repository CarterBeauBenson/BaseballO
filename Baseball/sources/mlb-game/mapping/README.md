# MLB game feed to BaseballO RML

This package maps an untouched completed MLB feed/live JSON document to RDF.
An isolated execution-context copy supplies ancestor identifiers that the
selected RML processor cannot resolve from nested JSONPath records.

## Active mapping

The active file is [mlb-game.rml.ttl](mlb-game.rml.ttl). It creates distinct individuals for source records, agents, persistent person roles, contextual team roles, intentional acts, physical processes, institutional processes, judgment acts, call acts, decision and rule ICEs, temporal regions, sites, teams, and artifacts.

The mapping retains the historical base IRI
`https://baseballontology.org/mapping/mlb-direct` solely for stable blank-node
and execution identity across existing evidence. `mlb-direct` is retired as a
file or package name; changing this internal base would invalidate reproducible
mapping and reasoning fingerprints without changing the source boundary.

The central implemented batted-play chain is:

```text
SwingAct or BuntAct
  -> BatBallContactProcess
  -> BattedBallMotionProcess
  -> FairBallProcess
  -> most-specific plate-appearance result

counted result
  -> has occurrent part -> Judgment Act
Judgment Act
  -> has output -> Decision ICE
Decision ICE
  -> is about -> counted result
```

Separate implemented paths cover called balls, called strikes, swinging strikes, bunts, fouls, foul tips, hits, errors, fielder's choices, sacrifices, batted outs, runner safe/out/run resolutions, stolen bases, the full intentional-walk process, institutional passed-ball and wild-pitch classifications, and uncaught third strikes. See the [discrete Mermaid catalog](../../../mermaid/patterns/README.md).

## Input and execution boundary

The [accepted resolution/award relations](../../../archive/design-records/mlb-game-resolution-award-links/README.md)
identify the runner resolved, a supported adjudicated first/second/third Base,
and completion of a particular walk/HBP award. Three small mapping additions
reuse the existing resolution, runner, Base and award IRIs. The
[source design](../review/resolution-award-source-design.md) specifies the
conservative forced-chain guards. Missing links do not establish unchanged
state or zero contribution; these relations do not complete TFS/PAQ-2.

The [accepted baserunning origin](../../../archive/design-records/mlb-game-baserunning-origin/README.md)
links an existing Baserunning Act to its supported starting Base. The
[source design](../review/baserunning-origin-source-design.md) requires agreement
between the source origin and start, a unique event join and an unambiguous
runner row. Explicit Base Code Identifiers support query joins for origins and
adjudicated destinations without parsing IRIs. No missing row supplies an
unchanged state, and separate acts are not automatically coalesced.

The authoritative source is named `game.json` during RML execution. It is
copied byte-for-byte and is never normalized or rewritten.

JSONPath references inside nested logical sources are relative to their current
records. RMLMapper 8.1.0 also treats a parent-side `playEvents[*].playId`
reference as a terminal value rather than expanding it for every pitch. The
guarded [execution harness](../../../scripts/pipeline/run-rml.ps1) therefore runs
[`prepare-rml-context.py`](../../../scripts/pipeline/prepare-rml-context.py) to
create a temporary `game-context.json`. It retains the source structure and
adds only reserved `_baseballO` execution fields:

- each pitch's enclosing atBatIndex;
- each accepted boxscore player's participating MLB team ID;
- batter and pitcher IDs;
- each runner record's enclosing atBatIndex and zero-based runnerIndex;
- source-fact booleans needed to partition runner movements and distinguish
  bunt attempts from swings using MLB pitch codes and in-play trajectories;
- separate gates for genuine plate-appearance structure and a completed
  institutional plate-appearance result;
- whether a runner row carries a real Boolean safe/out resolution or is an
  unresolved source placeholder;
- the source pitch identifier supporting each passed-ball or wild-pitch row,
  including action rows that must resolve to the immediately preceding pitch;
- the exact source-supported uncaught-third-strike composite flag;
- each play's terminal pitch playId and source-reported in-play state;
- unresolved-original-decision evidence when an overturned review establishes
  a prior decision but does not state its content; and
- the terminal baseball-event timestamp corroborated by Final or game-over
  source state.

The temporary mapping also materializes safe root identifiers:

- gamePk
- venue ID
- away and home team IDs
- official scorer ID, when present
- home-plate umpire ID, when present

When an optional adjudicator is absent, the harness removes only the
marker-bearing participant and role assertions from the temporary mapping.
Judgment, decision, and counted-process individuals remain. The checked-in
mapping and authoritative source are unchanged. Source, context-builder,
execution-context, mapping, and output hashes are recorded.

## Identity

- Games, players, teams, venues, officials, and pitch events use stable source identifiers.
- PlayerRole uses stable person-team identity across games with that team; ManagerRole follows the same policy when a manager source is added.
- Batter, pitcher, fielder, catcher, baserunner, umpire, and official-scorer roles use stable person-and-role identity across games.
- Every accepted player is a game participant whose team-scoped PlayerRole is realized by that game, including a bench player; specialized roles are realized only by supported acts.
- Every mapped persistent role participates in an open CCO Stasis of Role that occupies an unbounded Temporal Interval. Boundary processes and date ICEs are deferred until an authoritative tenure or retirement source is selected.
- HomeTeamRole and AwayTeamRole remain game-scoped.
- Pitch-related acts and processes use gamePk plus playId.
- Plate-appearance results use gamePk plus atBatIndex and receive their most specific source-supported class on one individual.
- Runner acts, records, resolutions, judgments, and decisions use the
  execution-only `(atBatIndex, runnerIndex)` structural identity required by
  the IRI policy. Runner acts and resolutions link to their plate appearance.
- Null runner placeholders receive record identity only. They do not produce a
  BaserunningAct or RunnerResolutionProcess.
- Event-scoped baseball and bat IRIs keep artifacts stable through one mapped pitch without claiming cross-pitch identity.

## Conservative source boundaries

The mapping does not infer physical detail from a counted outcome alone.

- Fielding-credit acts are deferred because credits lack stable ancestor-aware identity.
- Pickoff acts are deferred because a runner record does not identify the pitcher who performed the act.
- Terminal pickoff and caught-stealing runner outcomes found in the current corpus remain explicit generic terminal-result structures. They are not silently promoted into performer-specific acts when the feed lacks the required agent evidence.
- Ordinary fouls always produce FoulBallProcess. A distinct StrikeProcess is produced only for the unambiguous count.strikes equals 1 subset; the event-local feed cannot distinguish every second counted foul from an unchanged two-strike count.
- MLB pitch-code `buntAttemptStatus` semantics and in-play bunt trajectories
  create `BuntAct`; those pitches are excluded from every `SwingAct` source.
  A `sac_bunt` result remains only an institutional sacrifice classification.
- Genuine plate-appearance structure creates the PlateAppearance. Completion
  and recognized result evidence separately gate its institutional result,
  judgment, decision, and result record. Administrative pseudo-plays do not
  create plate appearances.
- Coordinate ICEs and designated batted-ball sites are created when hitData.coordinates exists, but coordX and coordY literals remain deferred pending approved datatype properties.
- Non-pitch advisory events and measurement values remain deferred.
- Runner `movement.end` supports an institutional destination state, not a
  physical `BaseTouchingProcess`.
- A passed-ball or wild-pitch classification is represented with the official
  scorer's judgment and does not create a physical
  `PitchBallControlFailureProcess`; an uncaught third strike does not by itself
  entail a safe or out resolution.

## Validation

The accepted 2026-09-08 A1 extension connects an evidenced subset of existing
Runner Resolution Processes to their Batted-Ball Play Process. It requires
completed, recognized contact-result evidence, a unique terminal-event join,
and a matching runner classification. Mixed or unknown cases remain unlinked.
This is parthood only; it does not establish batter credit, independence when
absent, destination, or institutional base occupancy. See the
[accepted decision](../../../archive/design-records/mlb-game-batted-runner-resolution-containment/README.md).

From the repository root:

```powershell
python Baseball/sources/mlb-game/mapping/validate_mlb_game_mapping.py Baseball/data/raw/game-566279.json
```

That command is the focused static developer check for this component. NiFi's
MLB-game mapping lane owns routine RML execution, source SHACL, promotion,
quarantine, and evidence. The separate NiFi `Repository Evidence` group owns
the aggregate repository gate; do not reproduce either workflow as a routine
manual script chain.

Static validation checks Turtle, TriplesMap structure, logical sources,
processor-incompatible JSONPath expressions, declared BaseballO classes,
completed-game preconditions, identifiers, structural runner identities, and
legacy composite collisions. The NiFi execution harness runs the pinned
RMLMapper and the generated-RDF validator,
which requires persistent role IRIs and matching bearers, complete accepted-player participation, complete ancestor context on every pitch, swing/bunt act, and
contact; one corroborated game-end timestamp; supported physical chains; adjudication structure;
shared foul-tip/strike identity; and event-record separation.
The resulting Turtle must then conform to the separate
[`authoritative SHACL profile`](../shacl/authoritative.ttl) before it is
published.
NiFi repository validation exercises the accepted eight-game 2026-08-03 mapping
subset, the original fixture, and the two passed-ball/wild-pitch
uncaught-third-strike regression games. It checks the identity and official
date of all 546 raw corpus games and includes an explicit regression for
challenge versus umpire-initiated review context. Full corpus promotion uses
the same per-game RML, SHACL, graph-load, query-index, and equivalence gates
without modifying any raw source.
