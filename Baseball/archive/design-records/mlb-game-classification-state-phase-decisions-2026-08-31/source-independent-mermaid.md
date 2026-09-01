# Accepted source-independent patterns

## Pitch type and record identity

```mermaid
flowchart LR
    CODE[Reusable pitch-type Nominal Measurement ICE]
    SYSTEM[MLB Pitch-Type Reference System]
    RECORDID[Pitch-event-record Identifier ICE]
    RECORD[MLB Pitch Event Record ICE]
    PITCH[Particular Pitch Act]
    TYPE[Reviewed pitch-type-specific Pitch Act class]

    CODE -->|uses reference system| SYSTEM
    CODE -->|is a nominal measurement of| PITCH
    RECORDID -->|designates| RECORD
    RECORD -->|is about| PITCH
    PITCH -->|rdf:type after class review| TYPE
```

## Count anchored in recorded outs

```mermaid
flowchart LR
    HALF[Half Inning]
    OUT1[Recorded Out Process]
    OUT2[Recorded Out Process]
    PA[Plate Appearance]
    START[Plate Appearance start boundary]
    COUNT[Plate Appearance Start Out Count ICE]
    VALUE[Integer value: 2]

    OUT1 -->|occurrent part of| HALF
    OUT2 -->|occurrent part of| HALF
    OUT1 -->|precedes| START
    OUT2 -->|precedes| START
    PA -->|has temporal part| START
    COUNT -->|is about| HALF
    COUNT -->|is about| PA
    COUNT -->|has integer value| VALUE
```

## Replay history is preserved

```mermaid
flowchart LR
    ORIGINAL[Earlier Decision ICE]
    REVIEW[Replay Review Act]
    RESULT[Replay Review Result ICE]
    LATER[Later Decision ICE]
    HISTORY[Persistent historical graph]

    REVIEW -->|has input| ORIGINAL
    REVIEW -->|has output| RESULT
    REVIEW -->|has output| LATER
    ORIGINAL --> HISTORY
    RESULT --> HISTORY
    LATER --> HISTORY
    LATER -.->|overrides institutional effect;<br/>does not erase| ORIGINAL
```

## Strike-zone structures

```mermaid
flowchart LR
    ZONE[Three-dimensional rulebook Strike Zone Site]
    ABS[Two-dimensional ABS Evaluation Fiat Surface]
    RULE[Applicable Baseball Rule]
    METHOD[Evaluation method and era]

    ZONE -->|has continuant part| ABS
    RULE -->|is about| ZONE
    METHOD -.-> ABS
```

## Season, phases, and offseason segments

```mermaid
flowchart TB
    SEASON[Baseball Season Process]
    PRE[Preseason Process]
    REG[Regular-season Process]
    ALLSTAR[All-Star Game Phase Process]
    POST[Postseason Process]
    OFF[Offseason Process]
    OFFPART[Transaction-relevant Offseason Segment Process]
    GAME[Baseball Game]
    STR[Season Temporal Region]
    PTR[Phase or Segment Temporal Region]

    PRE -->|occurrent part of| SEASON
    REG -->|occurrent part of| SEASON
    ALLSTAR -->|occurrent part of| SEASON
    POST -->|occurrent part of| SEASON
    OFF -->|occurrent part of| SEASON
    OFFPART -->|occurrent part of| OFF
    GAME -->|occurrent part of| REG
    SEASON -->|occupies temporal region| STR
    OFFPART -->|occupies temporal region| PTR
    PTR -->|temporal part of| STR
```
