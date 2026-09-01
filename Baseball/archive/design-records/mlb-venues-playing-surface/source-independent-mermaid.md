# Source-independent Mermaid

```mermaid
flowchart LR
    VENUE[Baseball Venue]
    FIELD[Baseball Field Site]
    SURFACE[Baseball Playing Surface<br/>Material Artifact]
    FUNCTION[Structural Support Artifact Function]
    SUPPORT[Physical support Process]
    CLASS[Nominal Measurement ICE]
    SYSTEM[Surface-type Reference System]

    SURFACE -->|continuant part of| VENUE
    FUNCTION -->|inheres in| SURFACE
    SUPPORT -->|realizes when occurring| FUNCTION
    SUPPORT -->|occurs at| FIELD
    CLASS -->|is a measurement of| SURFACE
    CLASS -->|uses reference system| SYSTEM
```

The source does not assert the support Process or a validity interval. The
diagram keeps the material surface, Field Site, Function, realization, and
classification evidence distinct.
