# In-play swing: shared X, D, and E pattern

```mermaid
flowchart LR
    X["InPlayOutSource<br/>code X"] --> GENERIC["Same structural RML pattern"]
    D["InPlayNoOutSource<br/>code D"] --> GENERIC
    E["InPlayRunsSource<br/>code E"] --> GENERIC

    GENERIC --> SWING["/process/swing/{playId}<br/>a SwingAct"]
    SWING -->|"asserted: preceded by"| PITCH["PitchAct"]
    SWING -->|"has agent"| BATTER["Batter person"]
    SWING -->|"realizes"| ROLE["BatterRole"]
    ROLE -->|"inheres in"| BATTER

    CONTACT["/process/contact/{playId}<br/>a BatBallContactProcess"] -->|"asserted: preceded by"| SWING
    FAIR["/process/fair-ball/{playId}<br/>a FairBallProcess"] -->|"asserted: preceded by"| CONTACT
    CONTACT -->|"precedes"| RESULT["/plate-appearance/{atBatIndex}/result<br/>generic + specific result type"]

    HITDATA["BattedPitchSource<br/>pitch has hitData"] --> MOTION["/process/batted-ball-motion/{playId}<br/>a BattedBallMotionProcess"]
    MOTION -->|"asserted: preceded by"| CONTACT

    SWING -->|"occurs at"| FIELD["BaseballFieldSite"]
    CONTACT -->|"occurs at"| FIELD
    FAIR -->|"occurs at"| FIELD
    MOTION -->|"occurs at"| FIELD
    RESULT -->|"occurs at"| FIELD
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    GENERIC -.->|"X, D, E do not type the swing as success/failure"| NEUTRAL["Outcome remains in result and runner resolutions"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef process fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef note fill:#f3e8ff,stroke:#805ad5,color:#2d1b4e;
    class X,D,E,HITDATA,GENERIC source;
    class PITCH,SWING act;
    class CONTACT,FAIR,MOTION,RESULT process;
    class NEUTRAL note;
```

## Evaluation

The X, D, and E filtered maps are exactly the same RDF design pattern, so one
generic diagram is sufficient. Their source names mention out, no-out, and
runs, but every variant emits the same success-neutral `SwingAct`, contact,
and fair-ball structure. Final institutional success or failure comes from the
plate-appearance result and runner-resolution mappings.

`BattedBallMotionProcess` is selected independently by the presence of
`hitData`; it is not guaranteed solely by membership in an X, D, or E source.

## Identical map variants

| Call code | Swing map | Contact map | Fair-ball map |
| --- | --- | --- | --- |
| `X` | `InPlayOutSwingActMap` | `InPlayOutContactMap` | `InPlayOutFairBallMap` |
| `D` | `InPlayNoOutSwingActMap` | `InPlayNoOutContactMap` | `InPlayNoOutFairBallMap` |
| `E` | `InPlayRunsSwingActMap` | `InPlayRunsContactMap` | `InPlayRunsFairBallMap` |

Each family also has a record-about map using the shared pitch event-record IRI.
`BattedBallMotionMap` is common to any pitch record containing `hitData`.
