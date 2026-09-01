# Source-specific Mermaid

Status: **under review — design only**

Solid edges use accepted vocabulary but are not authorized RDF. Dotted lines
terminate in question nodes and do not propose object properties.

## Sweet-spot motion and Process Profile

```mermaid
flowchart LR
    SWING[Swing Act]
    BAT[Baseball Bat]
    POINT[Tracked sweet-spot\ngeneric Fiat Point]
    SELECTOR[Designative ICE]
    TRACKREF[Versioned tracking\nReference System]
    MOTION[Generic Motion\noccurrent part of Swing]
    VELOCITY[Velocity\nProcess Profile]

    SWING -->|has participant| BAT
    SWING -->|has occurrent part| MOTION
    MOTION -->|has participant| BAT
    MOTION -->|has participant| POINT
    MOTION -->|has occurrent part| VELOCITY
    BAT -->|has continuant part| POINT
    SELECTOR -->|designates| POINT
    SELECTOR -->|uses reference system| TRACKREF
```

The particular generic Motion and Fiat Point carry the reality-side structure;
no `AttackAngleRecord` or `SweetSpotVelocityICE` replaces them.

## Attack angle and attack direction

```mermaid
flowchart LR
    VELOCITY[Sweet-spot Velocity\nProcess Profile]
    POINT[Tracked Fiat Point]
    TANGENT[Actual tangent Fiat Line]
    REFERENCE[Actual ground-parallel OR\nhome-to-center Fiat Line]
    ANGLE[Angle Quality]
    MEASURE[Measurement ICE]
    DEGREE[CCO Degree]
    FRAME[Baseball Field Coordinate<br/>Reference System ICE]
    EVAL[Evaluation Temporal Region]
    TANGENTQ[QUESTION\nWhich accepted construction makes this line\ntangent to the profile at this evaluation?]
    REFQ[QUESTION\nWhich projection and field geometry\nground the reference line?]

    TANGENT -->|has continuant part| POINT
    REFERENCE -->|has continuant part| POINT
    TANGENT -->|exists at| EVAL
    REFERENCE -->|exists at| EVAL
    POINT -->|exists at| EVAL
    ANGLE -->|inheres in| TANGENT
    ANGLE -->|inheres in| REFERENCE
    ANGLE -->|exists at| EVAL
    MEASURE -->|is a measurement of| ANGLE
    MEASURE -->|uses measurement unit| DEGREE
    MEASURE -->|uses reference system| FRAME
    VELOCITY -.-> TANGENTQ
    TANGENT -.-> TANGENTQ
    EVAL -.-> TANGENTQ
    REFERENCE -.-> REFQ
    FRAME -.-> REFQ
```

The dotted blockers prevent an ICE from embezzling the tangent, projection,
field direction, or temporal evaluation structure.

## Swing-path tilt remains a separate geometry question

```mermaid
flowchart LR
    OBS[Final-40-ms tracking ICEs]
    ALGORITHM[Versioned Algorithm]
    TRANSFORM[Generic computation Process\nAct and Agent status unresolved]
    FITTED[Actual fitted path geometry\nQUESTION - class/identity unresolved]
    GROUND[Ground reference geometry]
    TARGET[QUESTION\nIs the measured target two Fiat Lines,\na Fiat Surface orientation, or another entity?]
    AGENTQ[QUESTION\nWhat causally active Agent would justify\nan Act of Data Transformation type?]
    MEASURE[Measurement ICE]

    TRANSFORM -->|has input| OBS
    TRANSFORM -->|prescribed by| ALGORITHM
    TRANSFORM -.-> AGENTQ
    FITTED -.-> TARGET
    GROUND -.-> TARGET
    MEASURE -.-> TARGET
```

No output edge or angle measurement is proposed until the fitted world-side
geometry and target are reviewed.
