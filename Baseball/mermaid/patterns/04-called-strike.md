# Called strike without a swing

```mermaid
flowchart LR
    SOURCE["CalledStrikeSource<br/>call code C"] --> MAP["CalledStrikeProcessMap"]
    MAP --> STRIKE["/process/strike/{playId}<br/>a StrikeProcess"]

    PITCH["PitchAct<br/>has pitcher agent<br/>realizes PitcherRole"] -.->|"inverse temporal reading: precedes"| STRIKE
    STRIKE -->|"asserted: preceded by"| PITCH
    STRIKE -->|"occurrent part of"| PA["PlateAppearance"]
    STRIKE -->|"occurs at"| FIELD["BaseballFieldSite"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    RECORD["/event-record/pitch/{playId}"] -->|"is about"| PITCH
    RECORD -->|"is about"| STRIKE
    STRIKE -.->|"StrikeJudgmentAct not instantiated"| JUDGMENT["StrikeJudgmentAct"]
    SOURCE -.->|"no SwingAct map for code C"| NOSWING["No batter swing"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,MAP source;
    class PITCH act;
    class STRIKE,RECORD outcome;
    class JUDGMENT,NOSWING gap;
```

## Evaluation

This is materially different from a swinging strike: the mapping creates no
`SwingAct`. The batter therefore has no agent relation for this pitch event,
which is appropriate if the source code reliably means the batter did not
swing. The institutional strike status remains separate from the pitcher's act.
