# Source-independent Mermaid

```mermaid
flowchart LR
    PERSON[Person]
    ROLE[Major League Free Agent Role\none uninterrupted interval]
    RULE[Baseball Rule\nAction Permission]
    CONTRACT[Act of Contract Formation]
    TEAM[Baseball Team]

    GAIN[Gain of Role]
    GAINREGION[Gain Temporal Region]
    STASIS[Stasis of Role]
    INTERVAL[Continuous Temporal Interval]
    LOSS[Loss of Role]
    LOSSREGION[Loss Temporal Region]

    ROUTE[Supported entry route\nautomatic boundary, release/non-tender,\nor confirmed election]
    RETIRE[Supported retirement route]
    TEAMROLE[New team-context Player Role]
    TEAMGAIN[Gain of Role for Player Role]

    ROLE -->|inheres in| PERSON
    ROLE -->|has realization| CONTRACT
    RULE -->|permits| CONTRACT
    CONTRACT -->|has participant| PERSON
    CONTRACT -->|has participant| TEAM

    GAIN -->|has participant| PERSON
    GAIN -->|affects| ROLE
    GAIN -->|occupies temporal region| GAINREGION
    ROLE -->|participates in| STASIS
    PERSON -->|participates in| STASIS
    STASIS -->|occupies temporal region| INTERVAL
    LOSS -->|has participant| PERSON
    LOSS -->|affects| ROLE
    LOSS -->|occupies temporal region| LOSSREGION
    GAIN -->|precedes| STASIS
    STASIS -->|precedes| LOSS

    ROUTE -.->|when exact evidence licenses it| GAIN
    CONTRACT -->|precedes| LOSS
    RETIRE -.->|when exact evidence licenses it| LOSS
    CONTRACT -->|precedes| TEAMGAIN
    TEAMGAIN -->|affects| TEAMROLE
```

The Rule is the institutional grounding and permission; it is not a process
that repeatedly maintains the Person's status. Persistence is represented by
the Stasis of Role involving both the Person and exact Role. Contract formation
may realize the free-agent Role and then precede its Loss and the Gain of a new
team-context Player Role.

The dashed entry and retirement edges are guarded consequences. A provider
label does not select one route, and absence of a team-context Player Role does
not create the free-agent Role.

