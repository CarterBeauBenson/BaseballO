# Archived Baseball Stage 1 RML Mapping

> **Historical prototype:** this workflow preprocesses and enriches the MLB JSON and is not part of the active direct-mapping architecture. It is retained for provenance only. See [`../../mappings/direct/`](../../mappings/direct/) for current work.

This directory contains the first executable mapping draft for the one-game vertical slice.

## Files

- `mlb-stage1.yml` — the human-maintained YARRRML mapping.
- `prepare_stage1_rml_input.py` — approved lightweight structural enrichment.
- `current-game.json` — enriched input generated from the raw game `566279` sample, now stored at `../../data/raw/game-566279.json`.
- `ontology-coverage-gaps.yaml` — explicit missing BaseballO coverage and temporary handling.
- `validate_stage1_mapping.py` — validates referenced ontology IRIs and reports source event types that receive only generic typing.

## Canonical pipeline represented here

```text
Raw MLB JSON
    ↓
lightweight structural enrichment
    ↓
YARRRML
    ↓
RML
    ↓
RDF
```

The enrichment script does not assign ontology classes or relations. It copies parent identifiers into nested records, exposes structural indexes, normalizes eventType strings only for IRI path segments, and derives temporal container bounds from source timestamps.

## Prepare the sample input

```bash
python prepare_stage1_rml_input.py \
  ../../data/raw/game-566279.json \
  current-game.json
```

## Validate ontology references

```bash
python validate_stage1_mapping.py
```

For the included sample, validation reports:

- 50 persons
- 79 plate appearances
- 282 pitches
- 81 YARRRML mappings
- `double_play` and `grounded_into_double_play` receive only generic `BaseballInstitutionalProcess` typing because BaseballO lacks specific classes

## Compile and run

The official YARRRML parser accepts:

```bash
yarrrml-parser -i mlb-stage1.yml -o mlb-stage1.rml.ttl
```

The resulting RML can then be executed by the selected RML processor against `current-game.json`.

## Stage 1 semantic coverage

The current mapping creates:

- Baseball Game
- CCO Organization team individuals
- CCO Person player individuals
- MLB name and identifier ICEs
- career-duration Batter Role and Pitcher Role individuals
- Inning, Half Inning, and Plate Appearance individuals
- Pitch Acts
- Baseball Event Records
- Ball, Strike, Foul Ball, Swing, Contact, and Batted-Ball Play structures where licensed
- generic institutional result processes for every plate appearance
- specific result typing where BaseballO currently provides the class
- BFO Temporal Intervals and Temporal Instants
- CCO time measurement ICEs
- Baseball Field Site fallback individuals

The mapping does not store statistical totals. SPARQL will calculate totals by counting process individuals.

## Deliberately deferred

- runner movements and baserunner roles
- fielding credits and fielder roles
- coordinate-defined sites
- named judgment acts not independently identified by the source
- team home/away role assertions
- empty-game derivation
