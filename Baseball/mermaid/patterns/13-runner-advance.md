# Runner advances safely from a recorded base

\`\`\`mermaid
flowchart LR
    ACT["BaserunningAct<br/>source start 1B, 2B, or 3B"] -->|"precedes"| TOUCH["BaseTouchingProcess"]
    TOUCH -->|"has participant"| RUNNER["Runner person"]
    TOUCH -->|"has participant"| BASE["Base identified by movement.end"]
    TOUCH -->|"precedes"| SAFE["SafeProcess"]
    SAFE -->|"has occurrent part"| J["SafeJudgmentAct"]
    J -->|"has output"| D["SafeDecisionICE"]
    D -->|"is about"| SAFE
    SB["explicit stolen-base event"] -.->|"adds separate pattern"| STOLEN["StolenBaseProcess"]
\`\`\`

Ordinary safe advancement does not imply a stolen base. Only explicit stolen_base event types add StealAttemptAct and StolenBaseProcess typing and adjudication.
