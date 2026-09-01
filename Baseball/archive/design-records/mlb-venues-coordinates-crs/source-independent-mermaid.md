# Source-independent Mermaid

```mermaid
flowchart LR
    VENUE[Baseball Venue]
    POINT[Baseball Venue Reference Point<br/>Geospatial Position]
    COORD[Designative Information Content Entity]
    WGS[World Geodetic System 1984]
    LAT[latitude decimal]
    LON[longitude decimal]

    POINT -->|continuant part of| VENUE
    COORD -->|designates| POINT
    COORD -->|uses geospatial coordinate reference system| WGS
    COORD -->|has latitude value| LAT
    COORD -->|has longitude value| LON
```

The coordinate ICE identifies and locates a real Fiat Point without becoming
that point or the Venue. Response versioning belongs to the evidence, not the
world-side identity.
