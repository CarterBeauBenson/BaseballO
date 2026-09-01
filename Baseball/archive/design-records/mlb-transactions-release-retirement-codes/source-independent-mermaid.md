# Source-independent Mermaid

```mermaid
flowchart LR
    RECORD[Source transaction record ICE]
    TEAM[Baseball Team]
    PERSON[Person]
    RELEASE[Baseball Player Release Act]
    DECISION[Baseball Player Release Decision ICE]
    PLAYERROLE[Team Player Role]
    PLAYERLOSS[Loss of Role]
    FAROLE[Major League Free Agent Role\nonly when independently licensed]
    FAGAIN[Gain of Role]
    RETIRE[Retirement Declaration Act]
    ACTIVE[Exact active Role\nteam Player Role or Free Agent Role]
    RETIRELOSS[Loss of Role]
    DAY[Canonical Day]
    DATE[Calendar Date Identifier]

    RECORD -->|is about| RELEASE
    RELEASE -->|has agent| TEAM
    RELEASE -->|has participant| PERSON
    RELEASE -->|has output| DECISION
    RELEASE -->|precedes| PLAYERLOSS
    PLAYERLOSS -->|affects| PLAYERROLE
    PLAYERLOSS -->|has participant| PERSON
    RELEASE -.->|only when rules and evidence establish free agency| FAGAIN
    FAGAIN -->|affects| FAROLE
    FAGAIN -->|has participant| PERSON

    RECORD -.->|exact retirement evidence| RETIRE
    RETIRE -->|has agent| PERSON
    RETIRE -->|precedes| RETIRELOSS
    RETIRELOSS -->|affects| ACTIVE
    RETIRELOSS -->|has participant| PERSON

    DATE -->|designates| DAY
```

`Baseball Player Release Act` is proposed under `Baseball Roster Status Act`.
It is grounded by the Team's causal agency, its release-decision output, and
the supported downstream Loss of the exact team Player Role. Release does not
automatically establish Major League free agency. Retirement ends only the
exact active Role supported by the evidence; it is not a universal career-wide
loss assertion.

