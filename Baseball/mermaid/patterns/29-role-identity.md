# Game-scoped role identity

\`\`\`mermaid
flowchart LR
    PERSON["globally identified Person"] -->|"bearer inverse of inheres in"| ROLE["game-scoped BatterRole, PitcherRole, BaserunnerRole, FielderRole, UmpireRole, or OfficialScorerRole"]
    ROLE -->|"inheres in"| PERSON
    ACT1["Act in game A"] -->|"realizes"| ROLE
    GAME["BaseballGame"] -.->|"scope encoded in role IRI"| ROLE
    TEAM["BaseballTeam"] -->|"bears"| TEAMROLE["game-scoped HomeTeamRole or AwayTeamRole"]
\`\`\`

Player and official identities remain global. Contextual role IRIs include the game identifier so they are not reused across unrelated games.
