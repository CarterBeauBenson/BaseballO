# Source-independent Mermaid

Status: **under review — design only**

Solid arrows name accepted BFO, CCO, or BaseballO relations. Dotted arrows
terminate in unresolved questions and are not proposed object properties.
Source fields never replace the world entities shown here.

## 1. The physical process chain already exists

```mermaid
flowchart LR
    GAME[Baseball Game]
    PA[Plate Appearance]
    PITCH[Pitch Act]
    PMOTION[Pitch-Ball Motion Process]
    SWING[Swing Act]
    CONTACT[Bat-Ball Contact Process]
    BMOTION[Batted-Ball Motion Process]
    BALL[Baseball]
    BAT[Baseball Bat]

    GAME -->|has occurrent part| PA
    PA -->|has occurrent part| PITCH
    PA -->|has occurrent part| SWING
    PMOTION -->|preceded by| PITCH
    CONTACT -->|preceded by| PMOTION
    CONTACT -->|preceded by| SWING
    BMOTION -->|preceded by| CONTACT
    PMOTION -->|has participant| BALL
    CONTACT -->|has participant| BALL
    CONTACT -->|has participant| BAT
    BMOTION -->|has participant| BALL
    SWING -->|has participant| BAT
```

No Statcast-specific Game, Plate Appearance, Pitch, contact, or ball-motion
universal is needed. A swing-and-miss follows the left side of this history but
does not instantiate the contact or batted-ball branches.

## 2. Changing motion is represented by Process Profiles

```mermaid
flowchart LR
    MOTION[Pitch-Ball or Batted-Ball Motion Process]
    OBJECT[Participating Baseball]
    SPEED[CCO Speed Process Profile]
    VELOCITY[CCO Velocity Process Profile]
    ACCEL[CCO Acceleration Process Profile]
    MICE[Measurement ICE]
    VALUE[Decimal value]
    UNIT[Measurement Unit]
    FRAME[Reviewed Reference System ICE]
    EVAL[Candidate evaluation Temporal Region]
    PROFILEQ[QUESTION: one changing profile or local profiles?]
    SCOPEQ[QUESTION: Process part, boundary, interval, or model evaluation?]

    MOTION -->|has participant| OBJECT
    MOTION -->|has occurrent part| SPEED
    MOTION -->|has occurrent part| VELOCITY
    MOTION -->|has occurrent part| ACCEL
    MICE -->|is a measurement of| SPEED
    MICE -->|has decimal value| VALUE
    MICE -->|uses measurement unit| UNIT
    MICE -->|uses reference system| FRAME
    SPEED -.-> PROFILEQ
    VELOCITY -.-> PROFILEQ
    ACCEL -.-> PROFILEQ
    EVAL -.-> SCOPEQ
    MOTION -.-> SCOPEQ
    PROFILEQ -.-> SCOPEQ
```

The Measurement ICE targets exactly one reviewed profile. The diagram does not
assert that every profile is present for every motion, that one value is
constant throughout the motion, or that an undocumented evaluation is an
instant. Scalar speed uses Speed; Velocity requires direction and a frame.

## 3A. Throwing-arm angle requires actual geometry

```mermaid
flowchart LR
    PITCHER[Pitcher Person]
    BODY[Bodily Component]
    SHOULDER[Selected shoulder Fiat Point]
    BALL[Baseball]
    BALLPOINT[Selected ball Fiat Point]
    ARM[Shoulder-to-ball Fiat Line]
    GROUND[Ground-parallel Fiat Line]
    ANGLE[Angle Quality]
    MICE[Measurement ICE]
    DEGREE[Degree Measurement Unit]
    FRAME[Baseball Field Coordinate<br/>Reference System ICE]
    EVAL[Pitch-release evaluation Temporal Region]

    PITCHER -->|has continuant part| BODY
    BODY -->|has continuant part| SHOULDER
    BALL -->|has continuant part| BALLPOINT
    ARM -->|has continuant part| SHOULDER
    ARM -->|has continuant part| BALLPOINT
    GROUND -->|has continuant part| SHOULDER
    ANGLE -->|inheres in| ARM
    ANGLE -->|inheres in| GROUND
    MICE -->|is a measurement of| ANGLE
    MICE -->|uses measurement unit| DEGREE
    MICE -->|uses reference system| FRAME
```

The shoulder Fiat Point is the shared point required by `AngleQuality`; the
geometry is evaluated at pitch release.

## 3B. Bat tracking requires motion, points, lines, and evaluation scope

```mermaid
flowchart LR
    SWING[Swing Act]
    BAT[Baseball Bat]
    SWEET[Selected sweet-spot Fiat Point]
    SELECTOR[Designative ICE]
    TRACKREF[Tracking Reference System]
    MOTION[Motion occurrent part of Swing]
    VPROFILE[Velocity Process Profile]
    TANGENT[Actual sweet-spot path tangent Fiat Line]
    VTANGENT[Vertical-plane projected tangent Fiat Line]
    HTANGENT[Horizontal-plane projected tangent Fiat Line]
    GROUND[Ground-parallel Fiat Line]
    CENTER[Local Fiat Line through sweet spot\nparallel to home-to-center direction]
    AANGLE[Attack Angle Quality]
    DANGLE[Attack Direction Angle Quality]
    EVAL[Contact or reviewed path-crossing evaluation]
    MISSQ[QUESTION: what is the real path-crossing evaluation on a miss?]

    SWING -->|has participant| BAT
    SWING -->|has occurrent part| MOTION
    MOTION -->|has participant| BAT
    MOTION -->|has participant| SWEET
    MOTION -->|has occurrent part| VPROFILE
    BAT -->|has continuant part| SWEET
    SELECTOR -->|designates| SWEET
    SELECTOR -->|uses reference system| TRACKREF
    TANGENT -->|has continuant part| SWEET
    VTANGENT -->|has continuant part| SWEET
    HTANGENT -->|has continuant part| SWEET
    GROUND -->|has continuant part| SWEET
    CENTER -->|has continuant part| SWEET
    AANGLE -->|inheres in| VTANGENT
    AANGLE -->|inheres in| GROUND
    DANGLE -->|inheres in| HTANGENT
    DANGLE -->|inheres in| CENTER
    EVAL -.-> MISSQ
```

At actual contact, the Bat-Ball Contact Process can supply reviewed temporal
context. A swing-and-miss must not create contact merely to support a metric.
The comparison line is local to the sweet-spot evaluation point; the sweet spot
is not asserted as part of the actual home-to-center field line. Only the
swing-and-miss path-crossing entity remains unresolved here.

## 4. Independent evidence converges on shared world entities

```mermaid
flowchart LR
    WORLD[Canonical Game, Plate Appearance, Persons, and Processes]
    EVENTREC[Event-source Descriptive ICE]
    TRACKREC[Tracking-source Descriptive ICE]
    EVENTM[Event-source Measurement ICE]
    TRACKM[Tracking-source Measurement ICE]
    EVENTGRAPH[Independently validated event graph]
    TRACKGRAPH[Independently validated tracking graph]
    STORE[(Authoritative triple store)]
    QUERY[Explicit single-source or multi-source SPARQL]

    EVENTREC -->|is about| WORLD
    TRACKREC -->|is about| WORLD
    EVENTREC -->|has continuant part| EVENTM
    TRACKREC -->|has continuant part| TRACKM
    EVENTGRAPH --> STORE
    TRACKGRAPH --> STORE
    STORE --> QUERY
```

Identity/join keys are used transiently to resolve `WORLD`; they do not license
duplicate world assertions. Each source keeps its own record, measurement,
provenance, RML, SHACL, NiFi lane, and promoted graph. Integration occurs only
after independent validation and promotion.
