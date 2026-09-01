# Source-independent Mermaid

The solid shape is already accepted ontology. The dashed temporal branch is the
source-evidence gap.

```mermaid
flowchart LR
    ACT[Uniform Number Assignment Act]
    TEAM[Baseball Team]
    CODE[Code Identifier]
    ROLE[team-scoped Player Role]
    PERSON[Person]
    STASIS[Stasis of Role]
    INTERVAL[Temporal Interval]

    ACT -->|has agent| TEAM
    ACT -->|has output| CODE
    CODE -->|designates| ROLE
    ROLE -->|has organizational context| TEAM
    ROLE -->|inheres in| PERSON
    STASIS -->|has participant| PERSON
    STASIS -->|has participant| ROLE
    STASIS -->|occupies temporal region| INTERVAL
    ACT -.->|assignment-to-stint boundary evidence unresolved| INTERVAL
```

The Stasis does not realize the Role. It represents persistence while the Role
and bearer participate.
