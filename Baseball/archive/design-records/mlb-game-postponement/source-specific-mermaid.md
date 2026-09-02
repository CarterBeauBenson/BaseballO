# MLB schedule source-specific Mermaid

```mermaid
flowchart LR
    A["schedule row: detailedState = Postponed"]
    B["schedule row: same gamePk, detailedState = Final"]
    PK[stable MLB gamePk Identifier]
    ACT[Baseball Game Postponement Act]
    OLD[Input Baseball Game Schedule Plan]
    NEW[Output Baseball Game Schedule Plan]
    GAME[one Baseball Game]
    REASON["Nominal Measurement ICE: Inclement Weather"]
    MLB[MLB Organization]

    A -->|evidence for| OLD
    A -->|evidence for| ACT
    B -->|evidence for| NEW
    A -->|same value| PK
    B -->|same value| PK
    PK -->|designates| GAME
    ACT -->|has agent| MLB
    ACT -->|has input| OLD
    ACT -->|has output| NEW
    OLD -->|prescribes| GAME
    NEW -->|prescribes| GAME
    REASON -->|is a measurement of| ACT
```

The operational completed-game seed is deduplicated by `gamePk`. Detailed state
and revision fields determine which schedule occurrence supplies the revised
plan; abstract state `Final` is not sufficient.
