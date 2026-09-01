# Source-independent Mermaid

Status: **under review - design only**

```mermaid
flowchart LR
    TEAM[Baseball Team]
    LEAGUE[League Organization]
    ROLE[Organization Member Role\none uninterrupted Team-League stint]
    GAIN[Gain of Role]
    GREGION[Gain Temporal Region]
    STASIS[Stasis of Role]
    INTERVAL[Continuous Temporal Interval]
    LOSS[Loss of Role]
    LREGION[Loss Temporal Region]
    EVIDENCE[Season-scoped organization evidence]

    ROLE -->|inheres in| TEAM
    ROLE -->|has organizational context| LEAGUE
    GAIN -->|has participant| TEAM
    GAIN -->|affects| ROLE
    GAIN -->|occupies temporal region| GREGION
    TEAM -->|participates in| STASIS
    ROLE -->|participates in| STASIS
    STASIS -->|occupies temporal region| INTERVAL
    LOSS -->|has participant| TEAM
    LOSS -->|affects| ROLE
    LOSS -->|occupies temporal region| LREGION
    GAIN -->|precedes| STASIS
    STASIS -->|precedes| LOSS
    EVIDENCE -.->|after corpus proves historical semantics| ROLE
```

League membership is asserted independently of Division membership and never
through aggregate parthood. The first observation may be left-censored. A
supported League change ends the old Member Role and begins a new one; a later
return creates another Role individual. Missing observations do not end a
Role, and Stasis never realizes it.

