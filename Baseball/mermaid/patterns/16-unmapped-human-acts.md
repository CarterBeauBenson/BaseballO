# Remaining source-supported and source-limited gaps

\`\`\`mermaid
flowchart LR
    CREDIT["fielding credit"] -.->|"no stable ancestor-aware identity"| FIELDING["FieldingAttemptAct, CatchAttemptAct, ThrowAct, TagAttemptAct"]
    PICKOFF["runner event says pickoff"] -.->|"pitcher agent not identified in runner record"| PICKACT["PickoffAttemptAct"]
    FOUL["foul with count.strikes = 2"] -.->|"prior strike count inaccessible to event-local RML"| MAYBE["possibly counted StrikeProcess"]
    XY["coordX and coordY"] -.->|"no approved datatype properties"| COORD["Coordinate ICE exists without raw values"]
    ACTION["non-pitch advisory event"] -.->|"mixed classes and unstable IDs"| UNMAPPED["no act minted"]
\`\`\`

These are explicit mapping boundaries. The RML does not reconstruct fielding, pickoff, tag, throw, or ambiguous foul-strike events merely because they are typical.
