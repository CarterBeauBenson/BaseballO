# Relation directions

```mermaid
flowchart LR
    SOURCE["JSON source record"] --> MAP["rr:TriplesMap"]
    MAP --> ACT["Act individual"]

    ACT -->|"has agent<br/>cco:ont00001833"| PERSON["Person / Agent"]
    PERSON -.->|"agent in<br/>cco:ont00001787<br/>inverse; not emitted"| ACT

    ACT -->|"realizes<br/>BFO_0000055"| ROLE["Player role"]
    ROLE -->|"inheres in<br/>BFO_0000197"| PERSON

    ACT -->|"occurs at<br/>cco:ont00001918"| FIELD["BaseballFieldSite"]
    FIELD -->|"located in<br/>BFO_0000171"| VENUE["BaseballVenue"]

    ACT -->|"occurrent part of<br/>BFO_0000132"| CONTEXT["Plate appearance or game"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef role fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef context fill:#f3e8ff,stroke:#805ad5,color:#2d1b4e;
    class SOURCE,MAP source;
    class ACT act;
    class ROLE role;
    class PERSON,FIELD,VENUE,CONTEXT context;
```

## Direction assessment

| Assertion emitted by RML | Assessment |
| --- | --- |
| `act cco:ont00001833 person` | Correct: `has agent` has a process subject and agent object. |
| `act obo:BFO_0000055 role` | Correct: an occurrent realizes a realizable entity. |
| `role obo:BFO_0000197 person` | Correct: the specifically dependent role inheres in its bearer. |
| `act cco:ont00001918 fieldSite` | Correct: the process occurs at a site. |
| `fieldSite obo:BFO_0000171 venue` | Directionally valid: the field site is located in the material venue. |
| `act obo:BFO_0000132 context` | Correct subject direction for `occurrent part of`; runner acts use a coarser context than the other acts. |

The person-centric `person agent in act` direction is available as the inverse
of `has agent`, but the active instance graph emits only `act has agent person`.
Without inference, person-centric queries must use the inverse property path or
reverse triple pattern. Flipping the current assertion would be incorrect.
