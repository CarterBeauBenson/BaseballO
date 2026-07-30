# Joins and Identity Shape

## Pitch-to-play joins

All 44 referencing-object-map joins use the same equality condition. Thirty-nine connect pitch-derived structures to their enclosing play context; five additionally connect contact processes to the plate-appearance result.

```mermaid
flowchart LR
    PITCH["Nested pitch or filtered pitch record<br/>child: playId"]
    PLAY["Canonical allPlays record<br/>parent: playEvents[*].playId"]

    PITCH -->|"playId equality join"| PLAY
    PLAY --> PA["PlateAppearanceMap"]
    PLAY --> PITCHER["Pitcher person and career role"]
    PLAY --> BATTER["Batter person and career role"]
    PLAY --> PA_TIME["Plate-appearance interval"]
    PLAY --> RESULT["Plate-appearance result"]

    PITCH -.->|"materialized root marker"| GAMEPK["$.gamePk"]
    PITCH --> PITCH_IRI["/game/{gamePk}/pitch/{playId}"]
    PITCH -->|"contact filters: precedes"| RESULT

    classDef stable fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef test fill:#fff2cc,stroke:#997a00,color:#3d3100;
    class PITCH_IRI stable;
    class PITCH,PLAY,GAMEPK test;
```

The execution harness resolves the root marker in its temporary mapping copy because mapper references are relative to the current iterator record. The remaining processor-sensitive feature is the join whose parent reference yields the `playEvents[*].playId` collection.

## Runner identity

Runner records expose neither a stable record ID nor their array index as a JSON value. The direct mapping therefore partitions records into five patterns and builds composite IRIs from fields present in each record.

```mermaid
flowchart TB
    RUNNER["allPlays[*].runners[*]"] --> OUT{"movement.isOut?"}
    OUT -->|"true"| OUTKEY["out key<br/>runner + playIndex + eventType<br/>+ outBase + outNumber"]
    OUT -->|"false"| SCORE{"end = score?"}
    SCORE -->|"yes, start null"| ORIGIN["score-origin key<br/>runner + playIndex + eventType"]
    SCORE -->|"yes, start set"| BASE["score-base key<br/>runner + playIndex + eventType + start"]
    SCORE -->|"no, start null"| REACH["reach key<br/>runner + playIndex + eventType + end"]
    SCORE -->|"no, start set"| ADVANCE["advance key<br/>runner + playIndex + eventType + start + end"]

    OUTKEY --> THREE["Baserunning Act<br/>Resolution Process<br/>Event Record"]
    ORIGIN --> THREE
    BASE --> THREE
    REACH --> THREE
    ADVANCE --> THREE

    THREE --> GAME["asserted as occurrent part of Game"]
    THREE -.->|"parent context unavailable"| PA["not explicitly linked to Plate Appearance"]

    classDef current fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef risk fill:#fde2e2,stroke:#a33,color:#4a1111;
    class OUTKEY,ORIGIN,BASE,REACH,ADVANCE,THREE current;
    class PA risk;
```

The sample validator found 113 unique composite keys for 113 runner records. That proves collision freedom only for the development feed, not for every MLB game.
