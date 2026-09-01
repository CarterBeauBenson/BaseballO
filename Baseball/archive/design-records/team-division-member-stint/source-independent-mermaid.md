# Source-independent Mermaid

Status: **under review - design only**

```mermaid
flowchart LR
    TEAM[Baseball Team]
    DIVISION[Division Organization]
    ROLE[Organization Member Role\none uninterrupted Team-Division stint]
    GAIN[Gain of Role]
    GREGION[Gain Temporal Region]
    STASIS[Stasis of Role]
    INTERVAL[Continuous Temporal Interval]
    LOSS[Loss of Role]
    LREGION[Loss Temporal Region]
    EVIDENCE[Season-scoped organization evidence]

    ROLE -->|inheres in| TEAM
    ROLE -->|has organizational context| DIVISION
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

The Team is not a continuant part of the Division. The organizations lane may
create this history only from its own season-scoped corpus after the known
historical-change tests pass. The first observation may be left-censored and
does not invent a Gain. An explicit change to another Division supports Loss
of the old Role and Gain of a new Role at the precision actually supplied.
Missing observations do not end a Role. Stasis never realizes it.

