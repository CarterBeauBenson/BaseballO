# Foul swing

```mermaid
flowchart LR
    SOURCE["FoulSource<br/>call code F"] --> SWINGMAP["FoulSwingActMap"]
    SOURCE --> CONTACTMAP["FoulContactMap"]
    SOURCE --> FOULMAP["FoulBallProcessMap"]
    SOURCE --> STRIKEMAP["FoulStrikeProcessMap"]

    PITCH["PitchAct"] -.->|"inverse reading: precedes"| SWING["SwingAct"]
    SWING -->|"asserted: preceded by"| PITCH
    SWING -->|"has agent"| BATTER["Batter person"]
    SWING -->|"realizes"| ROLE["BatterRole"]
    ROLE -->|"inheres in"| BATTER

    SWING -.->|"inverse reading: precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"asserted: preceded by"| SWING
    CONTACT -->|"precedes"| RESULT["Plate-appearance result process"]
    CONTACT -.->|"inverse reading: precedes"| FOUL["FoulBallProcess"]
    FOUL -->|"asserted: preceded by"| CONTACT

    STRIKE["StrikeProcess"] -->|"asserted: preceded by"| PITCH
    FOUL -.->|"no explicit relation"| STRIKE

    SWING -->|"occurs at"| FIELD["BaseballFieldSite"]
    CONTACT -->|"occurs at"| FIELD
    FOUL -->|"occurs at"| FIELD
    STRIKE -->|"occurs at"| FIELD
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    RECORD["One pitch event record"] -->|"is about"| PITCH
    RECORD -->|"is about"| SWING
    RECORD -->|"is about"| CONTACT
    RECORD -->|"is about"| FOUL
    RECORD -->|"is about"| STRIKE

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef process fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,SWINGMAP,CONTACTMAP,FOULMAP,STRIKEMAP source;
    class PITCH,SWING act;
    class CONTACT,RESULT,FOUL,STRIKE,RECORD process;
```

## Evaluation

- Contact success is represented by a separate physical process; the swing
  remains the same intentional act class used for a miss or a fair ball.
- Foul and strike are separate institutional process individuals, which avoids
  conflating the physical contact with either counted status.
- The graph does not directly connect `FoulBallProcess` to `StrikeProcess`.
  Their shared source record is the only explicit common node.
- The contact is also asserted to precede the eventual plate-appearance result,
  which may occur several pitches later.
- Review whether separate foul and strike process individuals are the intended
  two institutional classifications or whether one should be explicitly
  related to the other. Counting both generically as pitch outcomes could
  otherwise double-count one source pitch.
