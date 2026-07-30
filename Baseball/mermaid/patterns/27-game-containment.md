# Game and play containment

\`\`\`mermaid
flowchart TD
    GAME["BaseballGame"] -->|"has occurrent part"| INNING["Inning"]
    INNING -->|"has occurrent part"| HALF["HalfInning"]
    HALF -->|"has occurrent part"| PA["PlateAppearance"]
    PA -->|"has occurrent part"| BATTER["BatterAct"]
    PA -->|"has occurrent part"| PITCH["PitchAct"]
    PA -->|"has occurrent part"| PM["PitchBallMotionProcess"]
    PA -->|"has occurrent part"| PLAY["BattedBallPlayProcess"]
    PA -->|"has occurrent part"| RESULT["counted result"]
    PLAY -->|"has occurrent part"| CONTACT["BatBallContactProcess"]
    PLAY -->|"has occurrent part"| MOTION["BattedBallMotionProcess"]
    PLAY -->|"has occurrent part"| CLASS["fair, foul, foul-tip, or result process"]
\`\`\`

The revised RML emits both parent-to-child has-occurrent-part assertions for the core hierarchy and child-to-parent occurrent-part-of assertions where the component maps have ancestor access.
