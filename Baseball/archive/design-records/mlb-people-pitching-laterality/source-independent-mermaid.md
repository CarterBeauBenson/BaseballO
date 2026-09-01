# Source-independent Mermaid

```mermaid
flowchart LR
    PERSON[Person]
    LEFT[Throwing Side Disposition<br/>left-side particular]
    RIGHT[Throwing Side Disposition<br/>right-side particular]
    THROW[Throw Act]
    PITCH[Pitch Act<br/>separate pitching grain]
    CLASSIFICATION[Nominal Measurement ICE]
    SYSTEM[Throwing-side Reference System]

    LEFT -->|inheres in| PERSON
    RIGHT -->|inheres in| PERSON
    THROW -->|realizes when evidenced| LEFT
    THROW -->|realizes when evidenced| RIGHT
    PITCH -->|realizes when evidenced| LEFT
    PITCH -->|realizes when evidenced| RIGHT
    CLASSIFICATION -->|is a measurement of| LEFT
    CLASSIFICATION -->|is a measurement of| RIGHT
    CLASSIFICATION -->|uses reference system| SYSTEM
```

The people source asserts the real disposition and its nominal classification,
but it does not invent a realization event. Ambidextrous evidence supports both
particular dispositions.
