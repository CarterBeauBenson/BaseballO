# Direct MLB JSON → BaseballO RML

This package maps an **untouched** MLB `/game/{gamePk}/feed/live` JSON response directly to RDF.

## Input contract

Save the downloaded feed as:

```text
game.json
```

No normalization, flattening, helper fields, `_mapping` objects, or runner indexes are added. The same tracked mapping file is reused for every completed game log.

## Main file

```text
mlb-direct.rml.ttl
```

The mapping uses the classic RML 1.1/RMLMapper-compatible vocabulary and JSONPath logical sources. JSONPath references inside a logical source are evaluated relative to its current record. Templates explicitly mark the root identifiers for the game, venue, away team, and home team when those values are needed in generated IRIs.

Before invoking RMLMapper, [`../../scripts/pipeline/run-rml.ps1`](../../scripts/pipeline/run-rml.ps1) copies the mapping and the byte-identical JSON into an isolated work directory. It resolves only those four numeric markers in the temporary mapping copy from the root document, records both source and effective mapping hashes, then discards the working copy. The checked-in mapping and MLB response are never rewritten.

## What is mapped

- game, venue, and baseball field site
- teams and game-specific home/away team roles
- players, proper-name ICEs, and MLB identifier ICEs
- career-duration batter, pitcher, baserunner, and fielder roles
- innings, half innings, and plate appearances
- game, plate-appearance, and pitch temporal intervals, instants, and timestamp ICEs
- pitch acts and pitch event records
- ball, strike, foul, foul-tip, fair-ball, swing, contact, and batted-ball-motion structures
- generic plate-appearance result processes plus specific types observed in the sample
- runner acts, runner-resolution processes, safe/out/run results, and runner event records
- umpires and the official scorer

## Direct nested-record strategy

### Plate appearances

Plate appearances use source `about.atBatIndex` and the materialized root `gamePk` marker:

```text
/game/{gamePk}/plate-appearance/{atBatIndex}
```

### Pitches

Every observed pitch has a source `playId`, which is used as the pitch identifier. A referencing-object-map join connects the pitch to the enclosing plate appearance by matching:

```text
child playId = parent playEvents[*].playId
```

### Runner records

MLB provides no runner-record ID and no runner array index value. The mapping therefore uses pattern-specific composite keys made entirely from fields present in each runner record. No source field is invented. `validate_direct_mapping.py` checks the sample for collisions, and the same collision check should be run for every new feed.

RMLMapper's streaming JSONPath grammar has no `null` or not-equal literal operators. Runner sources therefore express non-null starting bases as the closed MLB base set `1B`, `2B`, and `3B`, and negate that set for a null start. The validator rejects any unexpected non-null start value before execution so it cannot be silently classified as an origin record.

## Deliberately deferred

The mapping does not invent ontology coverage for:

- field-relative `coordX` and `coordY`
- venue geographic latitude and longitude until an appropriate ICE class is approved
- pitch velocity, spin, break, launch, and distance measurement models
- individual fielding-credit acts
- non-pitch game-advisory action events
- aggregate boxscore statistics

See `ontology-coverage-gaps.yaml` and `mapping-coverage.yaml`.

## Validation

Run from this directory after placing a completed feed at `game.json`:

```bash
python validate_direct_mapping.py
```

Or validate an untouched feed at another path without copying or renaming it:

```bash
python validate_direct_mapping.py ../../data/raw/game-566279.json
```

The validator checks Turtle syntax and triples-map structure, locally declared BaseballO class references, the completed-game precondition, required play identifiers, observed result coverage, pitch `playId` uniqueness, and runner composite-key collisions. BFO and CCO terms come from imported ontologies and are not resolved by this offline check. The validator does not replace execution by an RML processor.

## RML execution

From the repository root, run the pinned processor through the guarded harness:

```powershell
.\scripts\pipeline\run-rml.ps1 -InputJson .\data\raw\game-566279.json
```

The harness accepts only completed games, verifies that staging did not change the input bytes, materializes the guarded root markers, runs RMLMapper in strict mode, validates the generated Turtle, and writes an operational manifest. Failures and their logs move to the local quarantine directory rather than producing loadable output.
