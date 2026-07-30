# Called ball and ball-in-dirt pattern

```mermaid
flowchart LR
    B["BallBSource<br/>call code B"] --> MAP1["BallProcessMap"]
    DIRT["BallDirtSource<br/>call code *B"] --> MAP2["BallInDirtProcessMap"]

    MAP1 --> BALL["/process/ball/{playId}<br/>a BallProcess"]
    MAP2 --> BALL

    PITCH["PitchAct<br/>has pitcher agent<br/>realizes PitcherRole"] -.->|"inverse temporal reading: precedes"| BALL
    BALL -->|"asserted: preceded by"| PITCH
    BALL -->|"occurrent part of"| PA["PlateAppearance"]
    BALL -->|"occurs at"| FIELD["BaseballFieldSite"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    RECORD["/event-record/pitch/{playId}"] -->|"is about"| PITCH
    RECORD -->|"is about"| BALL
    BALL -.->|"BallJudgmentAct required by class meaning<br/>but no instance mapped"| JUDGMENT["BallJudgmentAct"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class B,DIRT,MAP1,MAP2 source;
    class PITCH act;
    class BALL,RECORD outcome;
    class JUDGMENT gap;
```

## Evaluation

Codes `B` and `*B` use exactly the same RDF identity and relation pattern, so
they are shown once. The pitcher remains agent of the neutral `PitchAct`, not
agent of the institutional `BallProcess`. This separation is sound. The missing
judgment-act instance means the ABox does not explicitly realize the ontology's
full institutional classification pattern.
