# Source-independent Mermaid

Status: **review only**

Every solid edge below names an existing BFO or CCO relation. Dotted edges are
explicitly unresolved conceptual dependencies and are not object-property
proposals. Source field names appear only in explanatory text, never as world
classes. Solid value, unit, and reference-system edges still depend on prior
acceptance of `ice-direct-values-and-units`; their property IRIs exist now, but
their pinned IBE domains are part of that separate repair.

## 1. Record, measurement, and reality remain distinct

```mermaid
flowchart LR
    WORLD[World-side entity, quality, configuration, or process profile]
    MICE[Measurement or Classification ICE]
    RECORD[Descriptive Information Content Entity]
    ACT[Act of Measuring or Data Transformation]
    UNIT[Measurement Unit]
    REF[Reference System]

    MICE -->|is a measurement of| WORLD
    MICE -->|uses measurement unit| UNIT
    MICE -->|uses reference system| REF
    RECORD -->|describes| MICE
    RECORD -->|is about| WORLD
    ACT -->|has output| MICE
```

A numerical literal belongs to the ICE. It does not turn the record, pitch,
ball, bat, or player into the measured quality.

## 2. Arm-angle geometry

```mermaid
flowchart LR
    PITCHER[Pitcher Person]
    SHOULDER[Shoulder Bodily Component\nUNRESOLVED - no class proposed]
    SHOULDER_POINT[Shoulder Reference Fiat Point\nUNRESOLVED identity]
    BALL[Baseball]
    BALL_POINT[Ball Reference Fiat Point\nUNRESOLVED identity]
    ARM_LINE[Shoulder-to-Ball Fiat Line]
    GROUND_LINE[Ground-Parallel Fiat Line]
    ANGLE[Angle Quality\nowned by geometry proposal]
    MEASURE[Measurement ICE]
    DEGREE[Degree Measurement Unit]
    REF[Spatial Reference System]

    PITCHER -->|has continuant part| SHOULDER
    SHOULDER -->|has continuant part| SHOULDER_POINT
    BALL -->|has continuant part| BALL_POINT
    ARM_LINE -->|has continuant part| SHOULDER_POINT
    ARM_LINE -->|has continuant part| BALL_POINT
    GROUND_LINE -->|has continuant part| SHOULDER_POINT
    ANGLE -->|inheres in| ARM_LINE
    ANGLE -->|inheres in| GROUND_LINE
    MEASURE -->|is a measurement of| ANGLE
    MEASURE -->|uses measurement unit| DEGREE
    MEASURE -->|uses reference system| REF
```

The anatomical landmark and the tracked Fiat Point of the Baseball remain
ontology-review questions. No `ArmAngle` ICE is proposed as a substitute for
the two Fiat Lines, their shared Fiat Point, or the Angle Quality.

## 3. Sweet-spot motion, attack geometry, and swing-path tilt

```mermaid
flowchart LR
    SWING[Swing Act]
    BAT[Baseball Bat]
    SWEET[Baseball Bat Sweet-Spot Fiat Point]
    PROFILE[Unresolved sweet-spot\nmotion-profile structure]
    EVAL_INSTANT[Evaluation Temporal Instant\ncontact OR path crossing\nUNRESOLVED identity]
    TANGENT[Sweet-Spot Motion Fiat Line]
    REFERENCE[Ground or Home-to-Center Reference Fiat Line]
    ANGLE[Angle Quality\ngeometry-proposal dependency]
    MEASURE[Measurement ICE]

    SWING -->|has participant| BAT
    BAT -->|has continuant part| SWEET
    PROFILE -.->|must connect profiled Process,\npoint, and change of location| SWING
    PROFILE -. determines tangent at evaluation instant .-> TANGENT
    SWEET -->|exists at| EVAL_INSTANT
    TANGENT -->|has continuant part| SWEET
    REFERENCE -->|has continuant part| SWEET
    TANGENT -->|exists at| EVAL_INSTANT
    REFERENCE -->|exists at| EVAL_INSTANT
    ANGLE -->|inheres in| TANGENT
    ANGLE -->|inheres in| REFERENCE
    MEASURE -->|is a measurement of| ANGLE
```

Attack angle uses a vertical motion direction and ground reference. Attack
direction uses a horizontal motion direction and home-to-center-field
reference. In each case the reference Fiat Line is constructed through the
tracked sweet-spot Fiat Point at the evaluation Temporal Instant, so it and the
tangent have the shared Fiat Point required by the Angle Quality proposal.
Swing-path tilt additionally requires a reviewed construction of a plane or
canonical line from the last 40 milliseconds of the motion profile. The source
evidence does not justify that construction yet.

The pinned BFO defines a Process Profile intensionally but exposes no accepted
relation that connects this proposed profile to the profiled Swing, the Fiat
Point, and the change in that point's Location. The former class and
`occurrent part of Swing Act` restriction did not supply that differentia and
are removed. The dashed profile node is an ontology gap; it does not authorize
RML or a replacement object property.

## 4. Defensive configuration and nominal alignment

```mermaid
flowchart LR
    FIELDER_A[Fielder Person A]
    FIELDER_B[Fielder Person B]
    SITE_A[Player Site A]
    SITE_B[Player Site B]
    FIELD[Baseball Field Site]
    CONFIG[Unresolved defensive spatial\nconfiguration structure]
    INTERVAL[Pitch Temporal Interval]
    PITCH[Pitch Act]
    CLASS[Generic Nominal Measurement ICE]
    SCHEME[Provider Reference System instance]
    RECORD[Descriptive Information Content Entity]

    FIELDER_A -.->|located at| SITE_A
    FIELDER_B -.->|located at| SITE_B
    SITE_A -.->|spatial relations required| CONFIG
    SITE_B -.->|spatial relations required| CONFIG
    FIELD -.->|field reference required| CONFIG
    CONFIG -.->|must exist at| INTERVAL
    PITCH -->|occupies temporal region| INTERVAL
    CLASS -.->|target unresolved| CONFIG
    CLASS -->|uses reference system| SCHEME
    RECORD -->|describes| CLASS
    RECORD -->|is about| PITCH
```

Provider category symbols may classify an actual configuration, but the
current proposal does not model the player Sites, relative spatial relations,
or configuration identity criterion. The former Relational Quality class is
removed. The symbols are not classes of players, pitches, or field sites, and
their nominal ICEs remain blocked until the world-side target is expressible.

## 5. Barrel as a derived nominal classification

```mermaid
flowchart LR
    MOTION[Batted Ball Motion Process]
    SPEED[Speed Process Profile]
    ANGLE[Launch Angle Quality\ngeometry-proposal dependency]
    SPEED_M[Speed Measurement ICE]
    ANGLE_M[Angle Measurement ICE]
    ALGORITHM[Versioned Algorithm instance]
    CALC[Act of Data Transformation]
    CLASS[Generic Nominal Measurement ICE]
    SCHEME[Provider Reference System instance]

    SPEED -->|occurrent part of| MOTION
    SPEED_M -->|is a measurement of| SPEED
    ANGLE_M -->|is a measurement of| ANGLE
    CALC -->|has input| SPEED_M
    CALC -->|has input| ANGLE_M
    CALC -->|prescribed by| ALGORITHM
    CALC -->|has output| CLASS
    CLASS -->|is a nominal measurement of| MOTION
    CLASS -->|uses reference system| SCHEME
```

Barrel is one symbol under the classification reference system. The RDF must
not assert a `BarrelProcess` or duplicate the launch measurements from
Statcast.

## 6. Analytical estimates and probabilities

```mermaid
flowchart LR
    ACTUAL[Actual Pitch, Batted-Ball Motion, Game, or Game State]
    INPUTS[Event Records and Measurement ICEs]
    ALGORITHM[Versioned Algorithm instance]
    CALC[Act of Data Transformation]
    OUTPUT[Estimate or Probability Measurement ICE]
    TARGET[Possible Outcome Target\nUNRESOLVED]
    RECORD[Descriptive Information Content Entity]

    INPUTS -->|is about| ACTUAL
    CALC -->|has input| INPUTS
    CALC -->|prescribed by| ALGORITHM
    CALC -->|has output| OUTPUT
    OUTPUT -->|is about| ACTUAL
    OUTPUT -. measurement target requires modal review .-> TARGET
    RECORD -->|describes| OUTPUT
```

This pattern covers xBA, xwOBA, run expectancy, and win expectancy without
asserting a provider score as a physical quality. xBA and home win expectancy
remain blocked until the measured possible process or process aggregate is
accepted.

## 7. Signed intercept components remain blocked

```mermaid
flowchart LR
    BATTER[Batter Person]
    COM[Center of Mass Fiat Point]
    INTERCEPT[Bat-Ball Intercept Fiat Point\nUNRESOLVED]
    XAXIS[X Coordinate System Axis]
    YAXIS[Y Coordinate System Axis]
    XQUALITY[Signed X Displacement Quality\nUNRESOLVED - no class proposed]
    YQUALITY[Signed Y Displacement Quality\nUNRESOLVED - no class proposed]
    XM[Measurement ICE]
    YM[Measurement ICE]
    REF[Cartesian Coordinate System]

    BATTER -->|has continuant part| COM
    INTERCEPT -. geometric relatum .-> XQUALITY
    COM -. geometric relatum .-> XQUALITY
    XAXIS -. sign and direction .-> XQUALITY
    INTERCEPT -. geometric relatum .-> YQUALITY
    COM -. geometric relatum .-> YQUALITY
    YAXIS -. sign and direction .-> YQUALITY
    XM -. blocked is-a-measurement-of edge .-> XQUALITY
    YM -. blocked is-a-measurement-of edge .-> YQUALITY
    XM -->|uses reference system| REF
    YM -->|uses reference system| REF
```

The field names imply subtraction while the CSV prose says distance. Actual
values and official coordinate conventions must resolve that conflict before
an ontology class or measurement mapping is proposed.
