# Source-independent Mermaid

```mermaid
flowchart LR
    RECORD[Source transaction record ICE]
    CONTRACT[Act of Contract Formation]
    PERSON[Person]
    TEAM[Baseball Team]
    FAROLE[Major League Free Agent Role\nwhen positively evidenced]
    FALOSS[Loss of Role]
    PLAYERROLE[New team Player Role]
    PLAYERGAIN[Gain of Role]
    DATE[Calendar Date Identifier]
    DAY[Canonical Day]
    CREGION[Contract Temporal Region]
    LREGION[Free-agent Loss Region]
    GREGION[Player-role Gain Region]

    RECORD -->|is about| CONTRACT
    CONTRACT -->|has agent| PERSON
    CONTRACT -->|has agent| TEAM
    CONTRACT -->|occupies temporal region| CREGION
    FAROLE -->|inheres in| PERSON
    CONTRACT -.->|when status is established: realizes| FAROLE
    FALOSS -->|has participant| PERSON
    FALOSS -->|affects| FAROLE
    FALOSS -->|occupies temporal region| LREGION
    PLAYERROLE -->|inheres in| PERSON
    PLAYERROLE -->|has organizational context| TEAM
    PLAYERGAIN -->|has participant| PERSON
    PLAYERGAIN -->|affects| PLAYERROLE
    PLAYERGAIN -->|occupies temporal region| GREGION
    CONTRACT -->|precedes| FALOSS
    CONTRACT -->|precedes| PLAYERGAIN
    DATE -->|designates| DAY
    CREGION -->|temporal part of| DAY
    LREGION -->|temporal part of| DAY
    GREGION -->|temporal part of| DAY
```

The free-agent branch is emitted only from affirmative Major League free-agent
evidence. Signing never infers that Role merely because an old team Role is
absent. A generic `Signed` row may support contract formation and Gain of a
team Player Role without supporting the free-agent branch.

