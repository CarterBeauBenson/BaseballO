# Source-independent Mermaid

```mermaid
flowchart LR
    RECORD[Source transaction record ICE]
    TYPE[Nominal Measurement ICE]
    SYSTEM[MLB transaction-type Reference System]
    PERSON[Canonical Person]
    TEAM[Canonical Baseball Team\nwhen structured ID is present]
    DATE[Calendar Date Identifier]
    DAY[Canonical Day]
    BLOCK[No specific Process or temporary Role\nuntil realizability and identity are grounded]

    RECORD -->|has continuant part| TYPE
    TYPE -->|uses reference system| SYSTEM
    RECORD -->|is about| PERSON
    RECORD -.->|structured team aboutness only| TEAM
    RECORD -->|has continuant part| DATE
    DATE -->|designates| DAY
    RECORD -.-> BLOCK
```

DFA, Waiver, Suspension, Status Change, Acquired, and Obtained remain
information-only in the first RML pass. No DFA Role, Suspended Player Role,
Waiver Status Role, or source-code Act subclass is admitted until an accepted
realization process, identity criterion, and exact institutional consequence
provide an independent semantic anchor.

