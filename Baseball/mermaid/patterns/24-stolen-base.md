# Explicit stolen base with coexisting safe status

\`\`\`mermaid
flowchart LR
    SOURCE["runner details.eventType = stolen_base_2b, stolen_base_3b, or stolen_base_home"] --> ACT["StealAttemptAct"]
    ACT -->|"also a BaserunningAct"| SAFE["SafeProcess"]
    ACT -->|"precedes"| SB["separate StolenBaseProcess"]
    SAFE -->|"has occurrent part"| SJ["SafeJudgmentAct"]
    SJ -->|"has output"| SD["SafeDecisionICE"]
    SB -->|"has occurrent part"| BJ["StolenBaseJudgmentAct"]
    BJ -->|"has participant"| SCORER["Official scorer"]
    BJ -->|"realizes"| ROLE["OfficialScorerRole"]
    BJ -->|"has output"| BD["StolenBaseDecisionICE"]
    BD -->|"is about"| SB
\`\`\`

SafeProcess and StolenBaseProcess are separate. A safe advance does not imply a stolen base.
