# One source record about distinct generated entities

\`\`\`mermaid
flowchart LR
    RECORD["BaseballEventRecord"] -->|"is about"| PITCH["PitchAct"]
    RECORD -->|"is about"| PM["PitchBallMotionProcess"]
    RECORD -->|"is about"| SWING["SwingAct or BuntAct"]
    RECORD -->|"is about"| CONTACT["BatBallContactProcess"]
    RECORD -->|"is about"| BM["BattedBallMotionProcess"]
    RECORD -->|"is about"| PLAY["BattedBallPlayProcess"]
    RECORD -->|"is about"| CLASS["counted classification"]
    RECORD -->|"is about"| J["Judgment Act"]
    RECORD -->|"is about"| D["Decision ICE"]
    RECORD -->|"is about"| CALL["Call Act when mapped"]
    RECORD -->|"is about"| SITE["location Site and coordinate ICE"]
\`\`\`

The record IRI is never reused for an act, physical process, judgment, decision, call, counted process, temporal region, site, role, person, or artifact.
