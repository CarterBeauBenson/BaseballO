# Source-independent Mermaid

```mermaid
flowchart LR
    RECORD[Source transaction record ICE]
    TYPE[Nominal Measurement ICE]
    SYSTEM[MLB transaction-type Reference System]
    PERSON[Canonical Person]
    TEAM[Canonical Baseball Team\nwhen structured ID is present]
    DAY[Canonical Day]
    DATE[Calendar Date Identifier]
    BLOCK[No world Act or Role consequence\nuntil independently grounded]

    RECORD -->|has continuant part| TYPE
    TYPE -->|uses reference system| SYSTEM
    RECORD -->|is about| PERSON
    RECORD -.->|structured team aboutness only| TEAM
    DATE -->|designates| DAY
    RECORD -->|has continuant part| DATE
    RECORD -.-> BLOCK
```

Assigned, Recalled, Optioned, Outrighted, and Selected remain information-only
in the first RML pass. The provider code does not establish a specific Act,
temporary Role, Gain/Loss consequence, or team-stint boundary. This prevents a
source-code taxonomy from becoming the ontology.

