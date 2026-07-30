# Pitch act and pitch-ball motion

\`\`\`mermaid
flowchart LR
    PITCHER["Pitcher person"] --> ROLE["game-scoped PitcherRole"]
    PITCH["PitchAct"] -->|"has participant"| PITCHER
    PITCH -->|"realizes"| ROLE
    PITCH -->|"has participant"| BALL["pitch-scoped Baseball"]
    PITCH -->|"precedes"| MOTION["PitchBallMotionProcess"]
    MOTION -->|"preceded by"| PITCH
    MOTION -->|"has participant"| BALL
    PITCH -->|"occurrent part of"| PA["PlateAppearance"]
    MOTION -->|"occurrent part of"| PA
    PITCH -->|"occupies temporal region"| INTERVAL["Pitch temporal interval"]
    RECORD["Pitch Event Record"] -->|"is about"| PITCH
    RECORD -->|"is about"| MOTION
    RECORD -->|"is about"| BALL
\`\`\`

Every source pitch now produces both the intentional PitchAct and the distinct physical PitchBallMotionProcess.
