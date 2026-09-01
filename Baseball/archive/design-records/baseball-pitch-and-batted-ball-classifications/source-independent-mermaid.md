# Source-independent Mermaid

```mermaid
flowchart LR
    HISTORY[Persistent historical<br/>classification evidence]
    CURRENT[Rebuildable current-state<br/>reasoning graph]
    PITCH[Pitch Act]
    PTYPE[Pitch-type-specific Pitch Act class]
    PICE[Reusable pitch-type Nominal Measurement ICE]
    PSYS[Versioned MLB Pitch-Type<br/>Reference System]
    PMOTION[Pitch Ball Motion Process]
    BATTED[Batted-Ball Motion Process]
    BTYPE[Trajectory-classified Batted-Ball Motion class]
    BICE[Reusable trajectory Nominal Measurement ICE]
    BSYS[Versioned MLB Batted-Ball<br/>Trajectory Reference System]

    HISTORY -->|preserves| PICE
    PICE -->|is a nominal measurement of| PITCH
    PICE -->|uses reference system| PSYS
    CURRENT -->|explicit rdf:type| PTYPE
    PTYPE -->|subclass of| PITCH
    PITCH -->|precedes| PMOTION
    HISTORY -->|preserves| BICE
    BICE -->|is a nominal measurement of| BATTED
    CURRENT -->|explicit rdf:type| BTYPE
    BTYPE -->|subclass of| BATTED
    BICE -->|uses reference system| BSYS
```

```mermaid
flowchart TB
    PITCH[Pitch Act]
    PITCH --> FF[Four-Seam Fastball Pitch Act]
    PITCH --> SI[Sinker Pitch Act]
    PITCH --> FC[Cutter Pitch Act]
    PITCH --> SL[Slider Pitch Act]
    PITCH --> ST[Sweeper Pitch Act]
    PITCH --> SV[Slurve Pitch Act]
    PITCH --> CU[Curveball Pitch Act]
    PITCH --> KC[Knuckle-Curve Pitch Act]
    PITCH --> CS[Slow Curve Pitch Act]
    PITCH --> CH[Changeup Pitch Act]
    PITCH --> FS[Splitter Pitch Act]
    PITCH --> FO[Forkball Pitch Act]
    PITCH --> SC[Screwball Pitch Act]
    PITCH --> KN[Knuckleball Pitch Act]
    PITCH --> EP[Eephus Pitch Act]
```

```mermaid
flowchart TB
    MOTION[Batted-Ball Motion Process]
    MOTION --> GB[Ground-Ball Motion Process]
    MOTION --> LD[Line-Drive Motion Process]
    MOTION --> FB[Fly-Ball Motion Process]
    MOTION --> PU[Pop-Up Motion Process]
```

The subclass arrows describe the proposed ontology taxonomy. A promotion rule
selects the currently authoritative provider classification and explicitly
types the instance in the rebuildable current-state graph. Historical nominal
measurements remain in persistent evidence but cannot infer old class types.
Velocity and movement thresholds never determine these classes.
