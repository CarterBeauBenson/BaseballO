# Source-independent Mermaid

Status: **under review — design only**

Solid edges show the candidate minimum graph using accepted BFO/CCO/BaseballO
relations. They are not authorized RDF while the package is active. Dotted
lines terminate in explicit question nodes; they are not proposed properties.

## Scalar pitch speed

```mermaid
flowchart LR
    PITCH[Pitch Act]
    MOTION[Pitch-Ball Motion Process]
    BALL[Baseball]
    SPEED[Speed\nProcess Profile]
    MEASUREMENT[Measurement ICE]
    VALUE[xsd:decimal\nfor example 90.0]
    MPH[CCO Miles Per Hour\nMeasurement Unit]
    RECORD[Source record\nDescriptive ICE]

    MOTION -->|preceded by| PITCH
    MOTION -->|has participant| BALL
    MOTION -->|has occurrent part| SPEED
    MEASUREMENT -->|is a measurement of| SPEED
    MEASUREMENT -->|has decimal value| VALUE
    MEASUREMENT -->|uses measurement unit| MPH
    RECORD -->|is about| MOTION
    RECORD -->|has continuant part| MEASUREMENT
```

The Process Profile is the world-side measurement target. The decimal and unit
belong to the Measurement ICE. No mph literal is attached to the Pitch Act,
Baseball, or Pitch-Ball Motion Process. No Act of Measuring is asserted from
the result alone.

## The evaluation "time shot" remains unresolved

```mermaid
flowchart LR
    MOTION[Pitch-Ball Motion Process]
    SPEED[Speed Process Profile]
    RELEASE[Provider release-speed evidence]
    END[Provider end/plate-speed evidence]
    WINDOWQ[QUESTION\nIs each value a sample of one changing\nprofile, a local profile of a motion segment,\na plane crossing, or a fitted estimate?]
    TIMEQ[QUESTION\nWhat Temporal Region or Process Boundary\nis actually supported, and at what precision?]

    MOTION -->|has occurrent part| SPEED
    RELEASE -.-> WINDOWQ
    END -.-> WINDOWQ
    SPEED -.-> WINDOWQ
    WINDOWQ -.-> TIMEQ
```

No `release profile`, `plate profile`, evaluation instant, plane-crossing, or
source-field class is proposed. The missing evaluation structure cannot be
hidden in the Measurement ICE label or IRI.

## Conditional directional Velocity shape

This diagram is conditional: it becomes eligible only after direction and
frame semantics are accepted. The solid relations themselves are existing
vocabulary, but the graph is not approved by this draft.

```mermaid
flowchart LR
    MOTION[Pitch-Ball Motion Process]
    VELOCITY[Velocity\nProcess Profile]
    VMEASUREMENT[Measurement ICE]
    MPH[CCO Miles Per Hour\nMeasurement Unit]
    FRAME[Cartesian Coordinate System\nReference System]
    COMPONENTS[Source directional components]
    DIRECTIONQ[QUESTION\nWhich axes, origin, signs, ordered components,\nand evaluation period constitute direction?]

    MOTION -->|has occurrent part| VELOCITY
    VMEASUREMENT -->|is a measurement of| VELOCITY
    VMEASUREMENT -->|uses measurement unit| MPH
    VMEASUREMENT -->|uses reference system| FRAME
    COMPONENTS -.-> DIRECTIONQ
    FRAME -.-> DIRECTIONQ
    VELOCITY -.-> DIRECTIONQ
```

A scalar `release_speed` value uses the first diagram, not this one. A
direction-bearing Velocity cannot be recovered by renaming the scalar field.

## Detachable source ownership

```mermaid
flowchart LR
    MLB[MLB-game source lane]
    STATCAST[Future Statcast source lane]
    MLBGRAPH[Promoted MLB graph]
    STATGRAPH[Promoted Statcast graph]
    STORE[(Authoritative triple store)]
    COMPARE[Explicit cross-source\nequivalence SPARQL]
    DECISION[Reviewed ownership/non-equivalence decision]

    MLB --> MLBGRAPH --> STORE
    STATCAST --> STATGRAPH --> STORE
    STORE --> COMPARE --> DECISION
```

The diagram contains no RML or SHACL edge between sources. Until the comparison
and ontologist decision are complete, `release_speed` remains excluded from
Statcast mapping as an unresolved duplicate.
