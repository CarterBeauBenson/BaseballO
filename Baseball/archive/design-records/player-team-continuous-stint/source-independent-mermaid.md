# Source-independent Mermaid

Status: **under review - design only**

```mermaid
flowchart LR
    PERSON[Person]
    TEAM[Baseball Team]
    ROLE[Player Role\none uninterrupted Person-Team stint]
    GAIN[Gain of Role]
    GREGION[Gain Temporal Region]
    STASIS[Stasis of Role]
    INTERVAL[Continuous Temporal Interval]
    LOSS[Loss of Role]
    LREGION[Loss Temporal Region]
    DAY[Canonical Day]
    DATE[Calendar Date Identifier]
    ACT[Player Act]

    ROLE -->|inheres in| PERSON
    ROLE -->|has organizational context| TEAM
    GAIN -->|has participant| PERSON
    GAIN -->|affects| ROLE
    GAIN -->|occupies temporal region| GREGION
    PERSON -->|participates in| STASIS
    ROLE -->|participates in| STASIS
    STASIS -->|occupies temporal region| INTERVAL
    LOSS -->|has participant| PERSON
    LOSS -->|affects| ROLE
    LOSS -->|occupies temporal region| LREGION
    GAIN -->|precedes| STASIS
    STASIS -->|precedes| LOSS
    DATE -->|designates| DAY
    GREGION -.->|when supported: temporal part of| DAY
    LREGION -.->|when supported: temporal part of| DAY
    ACT -->|realizes| ROLE
    ACT -->|has participant| PERSON
```

The dotted temporal-part edges are guarded assertions, not new properties.
They are emitted only when the owning source supplies Day-level boundary
evidence. A left-censored history may begin with Role and Stasis without an
invented Gain; an open history has no invented Loss. Missing observations do
not end the stint. Leaving and later returning to the same Team creates a new
Role, Stasis, and interval. Stasis never realizes the Role.

