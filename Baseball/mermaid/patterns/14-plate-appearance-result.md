# Plate-appearance result: generic identity with specific typing

```mermaid
flowchart LR
    PLAY["PlaySource<br/>every allPlays record"] --> GENERICMAP["PlateAppearanceResultMap"]
    GENERICMAP --> RESULT["/plate-appearance/{atBatIndex}/result<br/>a BaseballInstitutionalProcess"]

    RESULT -->|"occurrent part of"| PA["PlateAppearance"]
    RESULT -->|"has participant"| BATTER["Batter person"]
    RESULT -->|"has participant"| PITCHER["Pitcher person"]
    RESULT -->|"occurs at"| FIELD["BaseballFieldSite"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    PLAY --> RECORDMAP["PlateAppearanceResultRecordMap"]
    RECORDMAP --> RECORD["Result BaseballEventRecord"]
    RECORD -->|"is about"| RESULT
    RECORD -->|"dcterms:identifier"| EVENTTYPE["result.eventType"]
    RECORD -->|"descriptive text"| DESCRIPTION["result.description"]

    FILTERS["11 filtered ResultType maps"] -->|"adds rdf:type to same IRI"| RESULT
    FILTERS --> HITS["SingleProcess<br/>DoubleProcess<br/>HomeRunProcess"]
    FILTERS --> REACH["WalkProcess<br/>FieldersChoiceProcess"]
    FILTERS --> OUTS["BattedBallOutProcess<br/>ForceOutProcess<br/>StrikeoutProcess<br/>GroundedIntoDoublePlayProcess<br/>SacrificeFlyProcess<br/>DoublePlayProcess"]

    ACT["BatterAct / SwingAct"] -.->|"no success class added to act"| RESULT
    UNSEEN["Unseen eventType, including triple"] -.->|"generic result and record survive;<br/>specific class absent"| RESULT

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class PLAY,GENERICMAP,RECORDMAP,FILTERS source;
    class ACT act;
    class RESULT,RECORD,HITS,REACH,OUTS outcome;
    class UNSEEN gap;
```

## Specific-type overlay

| Source `result.eventType` | Additional type on the generic result IRI |
| --- | --- |
| `home_run` | `HomeRunProcess` |
| `double` | `DoubleProcess` |
| `single` | `SingleProcess` |
| `walk` | `WalkProcess` |
| `fielders_choice` | `FieldersChoiceProcess` |
| `field_out` | `BattedBallOutProcess` |
| `force_out` | `ForceOutProcess` |
| `strikeout` | `StrikeoutProcess` |
| `grounded_into_double_play` | `GroundedIntoDoublePlayProcess` |
| `sac_fly` | `SacrificeFlyProcess` |
| `double_play` | `DoublePlayProcess` |

## Evaluation

This is a strong success-neutral identity pattern. Every plate appearance gets
one generic result IRI, and reviewed source values add institutional outcome
types to that same individual. Hits, outs, walks, and productive outs do not
change the identity or class of the batter's act.

The grouping above is descriptive, not a binary success taxonomy. For example,
a sacrifice fly is an out that may achieve the batter's game objective, and a
fielder's choice may be safe for the batter while producing another runner's
out. The RML correctly preserves those as source-specific result processes.
