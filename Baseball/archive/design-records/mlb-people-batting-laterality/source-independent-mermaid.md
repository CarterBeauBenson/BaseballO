# Source-independent Mermaid

```mermaid
flowchart LR
    PERSON[Person]
    LEFT[Batting Side Disposition<br/>left-side particular]
    RIGHT[Batting Side Disposition<br/>right-side particular]
    ACT[Batter Act]
    CLASSIFICATION[Nominal Measurement ICE]
    SYSTEM[Batting-side Reference System]

    LEFT -->|inheres in| PERSON
    RIGHT -->|inheres in| PERSON
    ACT -->|realizes when evidenced| LEFT
    ACT -->|realizes when evidenced| RIGHT
    CLASSIFICATION -->|is a measurement of| LEFT
    CLASSIFICATION -->|is a measurement of| RIGHT
    CLASSIFICATION -->|uses reference system| SYSTEM
```

An `L` or `R` observation supports one classified disposition. An `S`
observation supports both particular dispositions. The people source does not
invent a Batter Act; realization edges require event evidence at that grain.
