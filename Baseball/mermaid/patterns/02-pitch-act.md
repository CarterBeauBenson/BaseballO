# Pitch act

```mermaid
flowchart LR
    SOURCE["PitchSource<br/>playEvents[isPitch = true]"] --> MAP["PitchActMap"]
    MAP --> ACT["/game/{gamePk}/pitch/{playId}<br/>a PitchAct"]

    JOIN["playId = playEvents[*].playId<br/>referencing-object-map join"] --> PA["PlateAppearanceMap"]
    JOIN --> PITCHER["PitcherPersonFromPlayMap"]
    JOIN --> ROLEMAP["PitcherRoleMap"]

    ACT -->|"has agent"| PERSON["/player/{pitcher.id}"]
    ACT -->|"realizes"| ROLE["/player/{pitcher.id}/role/pitcher<br/>a PitcherRole"]
    ROLE -->|"inheres in"| PERSON
    ACT -->|"occurrent part of"| PA

    ACT -->|"occurs at"| FIELD["BaseballFieldSite"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]
    ACT -->|"occupies temporal region"| INTERVAL["Pitch temporal interval"]
    ACT -->|"dcterms:identifier"| PLAYID["playId literal"]

    BALL["Ball / strike / in-play process"] -->|"preceded by"| ACT
    ACT -.->|"PitchBallMotionProcess not mapped"| MOTION["Pitch-ball motion"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,MAP,JOIN source;
    class ACT act;
    class BALL outcome;
    class MOTION gap;
```

## Evaluation

- The pitch act is outcome-neutral. Ball, strike, foul, and in-play status are
  represented by separate downstream process individuals.
- The person, role, and plate appearance depend on a processor-sensitive
  `playId` join. The field location uses the execution harness's materialized
  root venue marker.
- The temporal interval and source `playId` are stronger identity support than
  the other mapped act patterns receive.
- The ontology distinguishes a `PitchAct` from ensuing ball motion, but the RML
  does not instantiate `PitchBallMotionProcess`.
