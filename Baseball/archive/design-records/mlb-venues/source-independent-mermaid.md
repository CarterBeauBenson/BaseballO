# Source-independent semantic shapes

These shapes contain no source keys. Solid edges use accepted relations;
dashed edges are unresolved questions and never executable claims.

## Venue, field site, and game

```mermaid
flowchart LR
    RECORD[Descriptive Information Content Entity]
    IDENTIFIER[Venue Identifier]
    NAME[Proper Name]
    VENUE[Baseball Venue]
    FIELD[Baseball Field Site]
    GAME[Baseball Game]

    RECORD -->|is about| VENUE
    IDENTIFIER -->|designates| VENUE
    NAME -->|designates| VENUE
    VENUE -->|environs| GAME
    FIELD -->|environs| GAME
```

The physical Venue, spatial Field Site, and information about them remain
distinct. The accepted ontology currently relates each of the two continuants
to a Baseball Game through `environs`; this proposal does not invent a direct
Venue-to-Field-Site relation.

## Nominal classifications with withheld targets

```mermaid
flowchart LR
    CLASS[Generic Nominal Measurement ICE]
    REF[Reference System instance]
    FIELD[Baseball Field Site]
    SURFACE[Material surface or playing-surface artifact]
    VENUE[Baseball Venue]
    ROOF[Roof artifact, design, or state]

    CLASS -->|uses reference system| REF
    CLASS -.->|possible turf target| FIELD
    CLASS -.->|possible turf target| SURFACE
    CLASS -.->|possible roof target| VENUE
    CLASS -.->|possible roof target| ROOF
```

The solid reference-system edge depends on acceptance of the shared
ICE-direct-value foundation. No provider label creates a surface or roof.

## Geographic position and elevation gaps

```mermaid
flowchart LR
    COORD[Geospatial Coordinate ICE]
    POSITION[Geospatial Position]
    CRS[Coordinate Reference System]
    TARGET[Unresolved physical target point]
    ALTITUDE[Altitude]
    ENTITY[Unresolved altitude bearer]
    MEASURE[Measurement ICE]
    UNIT[Measurement Unit]
    DATUM[Unresolved vertical datum]

    COORD -->|designates| POSITION
    COORD -->|uses coordinate reference system| CRS
    TARGET -.->|located at| POSITION
    ALTITUDE -.->|inheres in| ENTITY
    MEASURE -->|is a measurement of| ALTITUDE
    MEASURE -->|uses measurement unit| UNIT
    DATUM -.-> ALTITUDE
```

Coordinate/reference/unit edges depend on the shared ICE foundation; the
source bindings remain withheld.

## Distance and azimuth gaps

```mermaid
flowchart LR
    P1[Fiat Point 1]
    P2[Fiat Point 2]
    DIST[Distance Quality]
    DM[Distance Measurement ICE]
    L1[Fiat Line 1]
    L2[Fiat Line 2]
    SHARED[Shared Fiat Point]
    ANGLE[Angle Quality]
    AM[Angle Measurement ICE]

    DIST -->|inheres in| P1
    DIST -->|inheres in| P2
    DM -->|is a measurement of| DIST
    L1 -->|has continuant part| SHARED
    L2 -->|has continuant part| SHARED
    ANGLE -->|inheres in| L1
    ANGLE -->|inheres in| L2
    AM -->|is a measurement of| ANGLE
```

Exact dimension endpoints and azimuth lines are unresolved. `Angle Quality`
and `Distance Quality` depend on the separate geometry proposal.

## Capacity remains an unmodeled question

```mermaid
flowchart LR
    VALUE[Source-reported number]
    SEATS[Possible seat aggregate]
    PEOPLE[Possible spectator count]
    PERMISSION[Possible permitted occupancy]
    CONFIG[Possible venue configuration]

    VALUE -.-> SEATS
    VALUE -.-> PEOPLE
    VALUE -.-> PERMISSION
    VALUE -.-> CONFIG
```

No Capacity class or Capacity Measurement ICE is proposed.

## Source ownership

```mermaid
flowchart LR
    GAME[MLB game payload\ncurrent assertion owner]
    VENUEAPI[Standalone venue endpoint\ncoverage candidate only]
    DECISION[Future explicit ownership decision]
    STORE[Authoritative triple store]

    GAME --> STORE
    VENUEAPI -.-> DECISION -.-> STORE
```
