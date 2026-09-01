# Source-independent Mermaid

This diagram is independent of MLB JSON, Statcast CSV, RML, and storage
technology. It shows the proposed world/content/bearer separation.

```mermaid
flowchart LR
    WORLD[World-side entity, quality, relation, site, or process profile]
    MICE[Measurement Information Content Entity]
    UNIT[Measurement Unit\nInformation Content Entity]
    REF[Reference System\nInformation Content Entity]
    LIT[xsd:decimal literal]
    IBE[Optional Information Bearing Entity\nmaterial bearer]

    MICE -->|is a measurement of| WORLD
    MICE -->|has decimal value| LIT
    MICE -->|uses measurement unit| UNIT
    MICE -->|uses reference system| REF
    IBE -->|is carrier of| MICE

    classDef world fill:#e8f5e9,stroke:#2e7d32
    classDef ice fill:#e3f2fd,stroke:#1565c0
    classDef bearer fill:#fff3e0,stroke:#ef6c00
    class WORLD world
    class MICE,UNIT,REF ice
    class IBE bearer
```

The carrier edge is optional and semantically independent. A source record,
database row, file, or message may be an IBE that carries an ICE, but no such
material entity is asserted solely because the ICE has a literal value.

## Geographic specialization

```mermaid
flowchart LR
    POSITION[Geospatial Position]
    COORD[Designative Information Content Entity]
    GEOREF[Geospatial Coordinate Reference System]
    LAT[Latitude literal]
    LON[Longitude literal]
    ALT[Optional altitude literal]

    COORD -->|designates| POSITION
    COORD -->|uses geospatial coordinate reference system| GEOREF
    COORD -->|has latitude value| LAT
    COORD -->|has longitude value| LON
    COORD -.->|has altitude value when supplied| ALT
```

This does not license field-relative baseball coordinates to masquerade as
geographic latitude/longitude. A Baseball Field Coordinate Reference System
must state its own standards and the coordinate ICE must be about a real site
or spatial entity.

## Prohibited collapse

```mermaid
flowchart LR
    MICE[Measurement ICE]
    FAKE[IBE invented only as a value holder]
    LIT[Literal]
    UNIT[Measurement Unit]

    MICE -. prohibited .-> FAKE
    FAKE -. prohibited value indirection .-> LIT
    FAKE -. prohibited unit indirection .-> UNIT
```
