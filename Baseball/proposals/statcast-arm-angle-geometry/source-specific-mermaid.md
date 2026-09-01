# Source-specific Mermaid

Status: **under review — design only**

Solid edges use existing vocabulary but are not authorized RDF. Dotted lines
converge on explicit questions and are not proposed relations.

## Release-local motion context

```mermaid
flowchart LR
    PITCH[Pitch Act]
    MOTION[Pitch-Ball Motion Process]
    BALL[Baseball]
    VELOCITY[Velocity\nProcess Profile]
    EVAL[Release evaluation\nTemporal Region]
    SCOPEQ[QUESTION\nIs release a motion segment, Process Boundary,\nshort interval, plane crossing, or fitted value?]

    MOTION -->|preceded by| PITCH
    MOTION -->|has participant| BALL
    MOTION -->|has occurrent part| VELOCITY
    VELOCITY -->|exists at| EVAL
    MOTION -.-> SCOPEQ
    VELOCITY -.-> SCOPEQ
    EVAL -.-> SCOPEQ
```

The `exists at` edge does not determine what the release region is. The dotted
question must be answered from method evidence before execution.

## World-side arm-angle geometry

```mermaid
flowchart LR
    PITCHER[Pitcher Person]
    BODY[Generic Bodily Component]
    SHOULDERPOINT[Selected shoulder\nFiat Point]
    BALL[Baseball]
    BALLPOINT[Selected ball\nFiat Point]
    ARM_LINE[Shoulder-to-ball Fiat Line]
    GROUND_LINE[Ground-parallel Fiat Line]
    ANGLE[Angle Quality]
    MEASURE[Measurement ICE]
    DEGREE[CCO Degree]
    FRAME[Baseball Field Coordinate<br/>Reference System ICE]
    EVAL[Release evaluation\nTemporal Region]
    LANDMARKQ[QUESTION\nWhich anatomical and ball landmarks\ndoes the provider track?]
    GROUNDQ[QUESTION\nWhich shared point, field structure,\nand frame ground the reference line?]

    PITCHER -->|has continuant part| BODY
    BODY -->|has continuant part| SHOULDERPOINT
    BALL -->|has continuant part| BALLPOINT
    ARM_LINE -->|has continuant part| SHOULDERPOINT
    ARM_LINE -->|has continuant part| BALLPOINT
    GROUND_LINE -->|has continuant part| BALLPOINT
    SHOULDERPOINT -->|exists at| EVAL
    BALLPOINT -->|exists at| EVAL
    ARM_LINE -->|exists at| EVAL
    GROUND_LINE -->|exists at| EVAL
    ANGLE -->|inheres in| ARM_LINE
    ANGLE -->|inheres in| GROUND_LINE
    ANGLE -->|exists at| EVAL
    MEASURE -->|is a measurement of| ANGLE
    MEASURE -->|uses measurement unit| DEGREE
    MEASURE -->|uses reference system| FRAME
    BODY -.-> LANDMARKQ
    SHOULDERPOINT -.-> LANDMARKQ
    BALLPOINT -.-> LANDMARKQ
    GROUND_LINE -.-> GROUNDQ
    FRAME -.-> GROUNDQ
```

The choice to draw the ground-parallel line through the ball point is a visible
review question, not a silent claim. If official evidence selects another
shared point, the Mermaid must be revised before approval.
