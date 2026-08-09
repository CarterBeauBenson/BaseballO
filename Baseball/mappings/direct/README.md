# Direct MLB JSON to BaseballO RML

This package maps an untouched completed MLB feed/live JSON document to RDF.
An isolated execution-context copy supplies ancestor identifiers that the
selected RML processor cannot resolve from nested JSONPath records.

## Active mapping

The active file is [mlb-direct.rml.ttl](mlb-direct.rml.ttl). It creates distinct individuals for source records, agents, contextual roles, intentional acts, physical processes, institutional processes, judgment acts, call acts, decision and rule ICEs, temporal regions, sites, teams, and artifacts.

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

Separate implemented paths cover called balls, called strikes, swinging strikes, fouls, foul tips, hits, errors, fielder's choices, sacrifices, batted outs, runner safe/out/run resolutions, stolen bases, the full intentional-walk process, pitch-ball control failures, passed balls, wild pitches, and uncaught third strikes. See the [discrete Mermaid catalog](../../mermaid/patterns/README.md).

## Input and execution boundary

The authoritative source is named `game.json` during RML execution. It is
copied byte-for-byte and is never normalized or rewritten.

JSONPath references inside nested logical sources are relative to their current
records. RMLMapper 8.1.0 also treats a parent-side `playEvents[*].playId`
reference as a terminal value rather than expanding it for every pitch. The
guarded [execution harness](../../scripts/pipeline/run-rml.ps1) therefore runs
[`prepare-rml-context.py`](../../scripts/pipeline/prepare-rml-context.py) to
create a temporary `game-context.json`. It retains the source structure and
adds only reserved `_baseballO` execution fields:

- each pitch's enclosing atBatIndex;
- batter and pitcher IDs;
- each runner record's enclosing atBatIndex and zero-based runnerIndex;
- source-fact booleans needed to partition runner movements and distinguish
  sacrifice-bunt pitches without processor-unsafe negation;
- whether a runner row carries a real Boolean safe/out resolution or is an
  unresolved source placeholder;
- the source pitch identifier supporting each passed-ball or wild-pitch row,
  including action rows that must resolve to the immediately preceding pitch;
- the exact source-supported uncaught-third-strike composite flag;
- each play's terminal pitch playId and source-reported in-play state; and
- the completed game's final play timestamp.

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
- Player and adjudicator roles are game-scoped.
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
- Coordinate ICEs and designated batted-ball sites are created when hitData.coordinates exists, but coordX and coordY literals remain deferred pending approved datatype properties.
- Non-pitch advisory events and measurement values remain deferred.
- A passed-ball or wild-pitch classification does not collapse into its
  preceding physical control failure, and an uncaught third strike does not by
  itself entail a safe or out resolution.

## Validation

From the repository root:

```powershell
python Baseball/mappings/direct/validate_direct_mapping.py Baseball/data/raw/game-566279.json
powershell -NoProfile -ExecutionPolicy Bypass -File Baseball/scripts/pipeline/run-rml.ps1 -InputJson Baseball/data/raw/game-566279.json
python Baseball/scripts/validate_repository.py
```

Static validation checks Turtle, TriplesMap structure, logical sources,
processor-incompatible JSONPath expressions, declared BaseballO classes,
completed-game preconditions, identifiers, structural runner identities, and
legacy composite collisions. The
execution harness runs the pinned RMLMapper and the generated-RDF validator,
which requires complete ancestor context on every pitch, swing/bunt act, and
contact; one final game timestamp; physical chains; adjudication structure;
shared foul-tip/strike identity; and event-record separation.
The resulting Turtle must then conform to the separate
[`authoritative SHACL profile`](../../shacl/authoritative.ttl) before it is
published.
Repository validation exercises the accepted eight-game 2026-08-03 mapping
subset, the original fixture, and the two passed-ball/wild-pitch
uncaught-third-strike regression games. It checks the identity and official
date of all 288 raw corpus games and includes an explicit regression for
challenge versus umpire-initiated review context. Full corpus promotion uses
the same per-game RML, SHACL, graph-load, query-index, and equivalence gates
without modifying any raw source.
