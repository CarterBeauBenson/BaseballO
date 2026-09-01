# Source-independent Mermaid

```mermaid
flowchart LR
    POSITION[Baseball Position Description]
    PERSON[Person]
    ROLE[Baseball Role]
    DISPOSITION[Baseball Disposition]
    QUALITY[Quality]
    ACT[Player Act]
    SYSTEM[Baseball-position Reference System]

    POSITION -->|describes| PERSON
    POSITION -->|describes| ROLE
    POSITION -->|describes| DISPOSITION
    POSITION -->|describes when evidenced| QUALITY
    POSITION -->|uses reference system| SYSTEM
    ROLE -->|inheres in| PERSON
    DISPOSITION -->|inheres in| PERSON
    QUALITY -->|inheres in| PERSON
    ACT -->|realizes when evidenced| ROLE
    ACT -->|realizes when evidenced| DISPOSITION
```

The position description provides an information-level summary of a real
cluster. It does not replace, realize, or collapse the Roles, Dispositions, and
Qualities it describes. The people source does not invent the Player Act.
