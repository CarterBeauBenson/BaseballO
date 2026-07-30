# Direct MLB JSON → BaseballO RML

This package maps an **untouched** MLB `/game/{gamePk}/feed/live` JSON response directly to RDF.

## Input contract

Save the downloaded feed as:

```text
game.json
```

No normalization, flattening, helper fields, `_mapping` objects, or runner indexes are added. The same mapping file is reused for every completed game log.

## Main file

```text
mlb-direct.rml.ttl
```

The mapping uses the classic RML 1.1/RMLMapper-compatible vocabulary and JSONPath logical sources. It uses absolute JSONPath references such as `$.gamePk` inside nested iterators. RML 1.1.2 explicitly permits references to be absolute or relative to the iterator.

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

Plate appearances use source `about.atBatIndex` and absolute root `$.gamePk`:

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

With RMLMapper Java:

```bash
java -jar rmlmapper.jar \
  -m mlb-direct.rml.ttl \
  -o game-output.trig \
  -s trig \
  --strict
```

TriG is an output serialization supported by RMLMapper. The package was syntax-validated locally. Processor execution remains the final compatibility test, particularly for JSONPath filters, absolute references, the `[-1:]` terminal-play slice, and joins against `playEvents[*].playId`.
