# Swinging strike

```mermaid
flowchart LR
    SOURCE["SwingingStrikeSource<br/>call code S"] --> SWINGMAP["SwingingStrikeSwingActMap"]
    SOURCE --> STRIKEMAP["SwingingStrikeProcessMap"]

    SWINGMAP --> SWING["/process/swing/{playId}<br/>a SwingAct"]
    STRIKEMAP --> STRIKE["/process/strike/{playId}<br/>a StrikeProcess"]
    PITCH["PitchAct"] -.->|"inverse temporal reading: precedes"| SWING
    SWING -->|"asserted: preceded by"| PITCH
    STRIKE -->|"asserted: preceded by"| PITCH

    SWING -->|"has agent"| BATTER["Batter person"]
    SWING -->|"realizes"| ROLE["BatterRole"]
    ROLE -->|"inheres in"| BATTER
    SWING -->|"occurrent part of"| PA["PlateAppearance"]
    SWING -->|"occurs at"| FIELD["BaseballFieldSite"]
    STRIKE -->|"occurrent part of"| PA
    STRIKE -->|"occurs at"| FIELD
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    RECORD["Pitch event record"] -->|"is about"| PITCH
    RECORD -->|"is about"| SWING
    RECORD -->|"is about"| STRIKE
    SWING -.->|"no explicit relation"| STRIKE
    SWING -.->|"no contact individual"| CONTACT["BatBallContactProcess"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,SWINGMAP,STRIKEMAP source;
    class PITCH,SWING act;
    class STRIKE,RECORD outcome;
    class CONTACT gap;
```

## Evaluation

- The failed contact objective is not baked into `SwingAct`; the separate
  `StrikeProcess` carries the institutional outcome.
- The source record is about both individuals, but the RML does not directly
  relate the swing to the strike process. Both are only `preceded by` the pitch
  and are parts of the same plate appearance.
- The absence of a contact individual correctly distinguishes this pattern
  from foul, foul-tip, and in-play swings.
