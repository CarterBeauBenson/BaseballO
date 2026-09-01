# Source-independent Mermaid

Status: **under review — design only**

These diagrams describe named-graph product choices. A box's placement does
not change its ontology type. Dashed arrows are pipeline routing, not RDF
object properties.

## Option A — source-owned authority record

```mermaid
flowchart LR
    SOURCE[Reference-source module]
    GRAPH[(Source authority graph)]
    PERSON[Person\npersistent continuant]
    ORG[Organization\npersistent continuant]
    BIRTH[Birth\none-time Process]
    SEASON[Baseball Season\nProcess]
    EVIDENCE[Source-owned ICEs]

    SOURCE -.-> GRAPH
    GRAPH -.-> PERSON
    GRAPH -.-> ORG
    GRAPH -.-> BIRTH
    GRAPH -.-> SEASON
    GRAPH -.-> EVIDENCE
```

Here `authority` means the authoritative reference record owned by the source.
It is not an assertion that every graph member is a persistent continuant.

## Option B — two products in one detachable module

```mermaid
flowchart LR
    SOURCE[One detachable\nsource module]
    RML[Source-owned mapping]
    AUTHSTAGE[Authority staging product\npersistent continuant facts]
    EVENTSTAGE[Event/evidence staging product\none-time Process facts]
    AUTHSHACL[Source-owned authority-product SHACL]
    EVENTSHACL[Source-owned event-product SHACL]
    PROMOTE[Atomic source-run promotion]
    AUTH[(Authority graph)]
    EVENT[(Event/evidence graph)]

    SOURCE --> RML
    RML -.-> AUTHSTAGE --> AUTHSHACL --> PROMOTE
    RML -.-> EVENTSTAGE --> EVENTSHACL --> PROMOTE
    PROMOTE --> AUTH
    PROMOTE --> EVENT
```

The products validate separately but succeed or fail as one module run. The
module remains independently stoppable, retryable, and removable without
affecting another source lane.

## Shared evidence placement still requires an answer

```mermaid
flowchart LR
    RESPONSE[Response Descriptive ICE]
    PLAN[Baseball Season Plan\ncontinuant]
    PERSON[Person]
    SEASON[Baseball Season\nProcess]
    AUTH[(Authority graph)]
    EVENT[(Event/evidence graph)]
    QUESTION[QUESTION\nOne non-duplicating home and\ncross-graph reference policy]

    RESPONSE -->|is about| PERSON
    RESPONSE -->|is about| SEASON
    PLAN -->|prescribes| SEASON
    RESPONSE -.-> QUESTION
    PLAN -.-> QUESTION
    QUESTION -.-> AUTH
    QUESTION -.-> EVENT
```

The Plan and response are continuants even when they are about or prescribe a
Process. Their graph placement must not be inferred from the type of a related
entity.
