# K1 candidate graph using accepted terms

```mermaid
flowchart LR
    PA[Plate Appearance]
    BA[Batter Act] -->|occurrent part of / BFO_0000132| PA
    BA -->|realizes / BFO_0000055| BR[Batter Role]
    BR -->|inheres in / BFO_0000197| Batter[Person: batter]
    DP[Double Play Process: existing combined result] -->|occurrent part of / BFO_0000132| PA
    DP -->|has process part / ont00001777| O1[Out Process: batter]
    DP -->|has process part / ont00001777| O2[Out Process: runner]
    O1 -->|has participant / BFO_0000057| Batter
    O2 -->|has participant / BFO_0000057| Runner[Person: runner]
    J[Baseball Adjudication Act] -->|occurrent part of / BFO_0000132| DP
    J -->|has output / ont00001986| D[Baseball Decision ICE]
    D -->|is about / ont00001808| DP
    R[Baseball Event Record] -->|is about / ont00001808| DP
    R -->|is about / ont00001808| J
    R -->|is about / ont00001808| D
```

The proposed additions are the Double Play classification of the existing
result and its two process-part links. Both Out Processes retain their existing
adjudication/decision/record structures and identities. The Mermaid omits those
repeated substructures for readability, not from the required conformance check.
The combined result must include exactly two distinct counted Out Processes
from the same continuous play. No new predicate or Strikeout constituent is
introduced. PA qualification, runner-out ownership, pitch ordering and complete
season reference populations remain distinct requirements.
