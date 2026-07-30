# Joins and identity strategy

\`\`\`mermaid
flowchart LR
    ROOT["guarded root markers"] --> GAME["gamePk-scoped IRIs"]
    PLAY["allPlays record"] --> PA["plate appearance by atBatIndex"]
    EVENT["pitch event by playId"] -->|"join playId to playEvents[*].playId"| PA
    EVENT --> PITCH["PitchAct"]
    EVENT --> PM["PitchBallMotionProcess"]
    EVENT --> ACT["SwingAct or BuntAct"]
    EVENT --> CONTACT["BatBallContactProcess"]
    EVENT --> MOTION["BattedBallMotionProcess"]
    EVENT --> PLAYPROC["BattedBallPlayProcess"]
    EVENT --> RECORD["Pitch Event Record"]
    RUNNER["runner record composite"] --> RUNACT["runner-act/movement/..."]
    RUNNER --> RESOLUTION["runner-resolution/out, reach, advance, or score"]
    ROLE["gamePk + personId + role type"] --> ACT
\`\`\`

The execution harness materializes safe numeric root markers for game, venue, teams, official scorer, and home-plate umpire into an isolated mapping copy. If an optional adjudicator is absent, marker-bearing participant and role assertions are removed from that temporary copy; the raw JSON and checked-in RML remain unchanged.

Runner objects still lack ancestor atBatIndex and an array index. Their documented source-field composite remains game-scoped and collision-validated, but runner acts cannot yet be linked safely to one plate appearance.
