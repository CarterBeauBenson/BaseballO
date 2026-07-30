# Foul-tip swing

```mermaid
flowchart LR
    SOURCE["FoulTipSource<br/>call code T"] --> SWINGMAP["FoulTipSwingActMap"]
    SOURCE --> CONTACTMAP["FoulTipContactMap"]
    SOURCE --> TIPMAP["FoulTipProcessMap"]
    SOURCE --> STRIKEMAP["FoulTipStrikeProcessMap"]

    PITCH["PitchAct"] -.->|"inverse reading: precedes"| SWING["SwingAct"]
    SWING -->|"asserted: preceded by"| PITCH
    SWING -->|"has agent"| BATTER["Batter person"]
    SWING -->|"realizes"| ROLE["BatterRole"]
    ROLE -->|"inheres in"| BATTER

    SWING -.->|"inverse reading: precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"asserted: preceded by"| SWING
    CONTACT -->|"precedes"| RESULT["Plate-appearance result process"]
    CONTACT -.->|"inverse reading: precedes"| TIP["FoulTipProcess"]
    TIP -->|"asserted: preceded by"| CONTACT

    STRIKE["StrikeProcess"] -->|"asserted: preceded by"| PITCH
    TIP -.->|"no explicit relation"| STRIKE
    TIP -.->|"required catching/judgment detail not mapped"| CATCH["Catching and FoulTipJudgment acts"]

    SWING -->|"occurs at"| FIELD["BaseballFieldSite"]
    CONTACT -->|"occurs at"| FIELD
    TIP -->|"occurs at"| FIELD
    STRIKE -->|"occurs at"| FIELD
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    RECORD["One pitch event record"] -->|"is about"| PITCH
    RECORD -->|"is about"| SWING
    RECORD -->|"is about"| CONTACT
    RECORD -->|"is about"| TIP
    RECORD -->|"is about"| STRIKE

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef process fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,SWINGMAP,CONTACTMAP,TIPMAP,STRIKEMAP source;
    class PITCH,SWING act;
    class CONTACT,RESULT,TIP,STRIKE,RECORD process;
    class CATCH gap;
```

## Evaluation

This pattern is structurally close to the ordinary foul pattern but is kept
separate because `FoulTipProcess` has materially different rule content: the
ball remains in play and the ontology definition refers to catching and an
authorized foul-tip judgment. Neither the catching process/act nor the
judgment act is instantiated by the RML.

The same source pitch also creates a separate `StrikeProcess`, even though the
`FoulTipProcess` definition already says it is institutionally counted as a
strike. That may be intentional decomposition, but the two status processes
currently have no explicit relation and should be reviewed for duplication.
