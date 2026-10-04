# Reused counted-foul pattern

No new relation or class is proposed. Substitutions and review records are
evidence for selecting a supported strike, not replacements for the actual act.

```mermaid
graph LR
  pitch[Pitch Act] -->|occurrent part of| pa[Plate Appearance Process]
  strike[Strike Process] -->|occurrent part of| pa
  judgment[Judicative Act] -->|has output| decision[Decision ICE]
  decision -->|is about| strike
```

The exact executable predicates and classes remain those of the accepted
`FoulStrikeProcessMap`, `FoulStrikeProcessMapRecordAboutMap`,
`CountedFoulStrikeAdjudicationMap`, `CountedFoulStrikeDecisionMap` and
`CountedFoulStrikeProcessPartMap`. This diagram does not authorize changing
the earlier pitch's participant or combining separately reviewed acts.
