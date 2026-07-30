# Plate-appearance batter activity

\`\`\`mermaid
flowchart LR
    PA["PlateAppearance"] -->|"has occurrent part"| BATTERACT["BatterAct"]
    BATTERACT -->|"has participant"| BATTER["Batter person"]
    BATTERACT -->|"realizes"| ROLE["game-scoped BatterRole"]
    ROLE -->|"inheres in"| BATTER
    BATTERACT -->|"occurs at"| FIELD["BaseballFieldSite"]
    SWING["SwingAct"] -->|"occurrent part of"| BATTERACT
    BUNT["BuntAct"] -->|"occurrent part of"| BATTERACT
    SWING -->|"occurrent part of"| PA
    BUNT -->|"occurrent part of"| PA
\`\`\`

The plate-appearance BatterAct is the aggregate batter activity. Each source-supported SwingAct or BuntAct is a separate, more specific act and an occurrent part of that aggregate.
