# Implemented corrections and retained boundaries

\`\`\`mermaid
flowchart TD
    OLD1["Act has-agent Person"] --> NEW1["Act has-participant Person"]
    OLD2["career-scoped player roles"] --> NEW2["game-scoped player roles"]
    OLD3["runner-act/out or score paths"] --> NEW3["runner-act/movement paths"]
    OLD4["Pitch directly before counted result"] --> NEW4["PitchAct to PitchBallMotionProcess to result"]
    OLD5["Contact directly before PA result"] --> NEW5["Contact to BattedBallMotion to fair/foul to result"]
    OLD6["FoulTipProcess and StrikeProcess had separate IRIs"] --> NEW6["one IRI with both types"]
    OLD7["counted processes lacked judgments"] --> NEW7["Judgment Act to Decision ICE; optional Call Act"]
    OLD8["in-play always asserted SwingAct"] --> NEW8["sac_bunt uses BuntAct"]
\`\`\`

The remaining boundaries are documented in 16-unmapped-human-acts.md and in the mapping coverage files. This diagram describes completed RML changes, not proposed future corrections.
