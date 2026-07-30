# Baserunning to out

\`\`\`mermaid
flowchart LR
    RUNNER["Runner person"] --> ROLE["game-scoped BaserunnerRole"]
    ACT["outcome-neutral BaserunningAct IRI"] -->|"has participant"| RUNNER
    ACT -->|"realizes"| ROLE
    ACT -->|"precedes"| OUT["OutProcess"]
    OUT -->|"has participant"| RUNNER
    OUT -->|"has occurrent part"| J["OutJudgmentAct"]
    J -->|"has input"| RULE["OutRule"]
    J -->|"has output"| D["OutDecisionICE"]
    D -->|"is about"| OUT
    RECORD["Runner Event Record"] -->|"is about"| OUT
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
\`\`\`

The act path begins runner-act/movement rather than runner-act/out. The source does not identify which umpire made a runner out call, so no Person or role individual is attached to this judgment.
