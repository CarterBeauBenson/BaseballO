# Source-independent review shapes

All nodes denote particular instances of existing classes. Edge labels name
existing relations; no diagram label introduces a predicate. These shapes are
proposed, not accepted. They show M1/M2 only, not unresolved inventory entries.

## M1: one additional counted strike after a supported foul

```mermaid
flowchart LR
  PA[Plate Appearance]
  F[Foul Ball Process]
  S[Strike Process]
  J[Strike Judgment Act]
  D[Strike Decision ICE]
  R[Strike Rule]
  E[Baseball Event Record]
  S -->|occurrent part of| PA
  F -->|occurrent part of| PA
  S -->|has occurrent part| J
  J -->|has input| R
  J -->|has output| D
  D -->|is about| S
  E -->|is about| F
  E -->|is about| S
  E -->|is about| J
  E -->|is about| D
```

This reuses the existing counted-foul pattern, whose full admitted relations
remain in effect. The source increment selects when the particular Strike
Process exists in the mapped institutional history. The number in the source
is not a newly modeled quality, state, or process. No precedence between
separate pitch events follows from an ordinal or the layout of this diagram.

## M2: distinct original and operative judgments about one pitched motion

```mermaid
flowchart LR
  O[Original Baseball Institutional Process]
  J[Reviewed On-Field Umpire Judgment Act]
  D[Reviewed On-Field Baseball Decision ICE]
  M[Pitch Ball Motion Process]
  P[Pitch Act]
  U[Person: on-field umpire]
  UR[Umpire Role]
  A[Baseball Replay Review Act: operative Ball or Strike Judgment Act]
  C[Operative Ball or Strike Process]
  V[Operative Ball or Strike Decision ICE: Baseball Replay Decision ICE]
  S[Affirming Baseball Replay Review Disposition ICE]
  E[Baseball Replay Review Event Record]
  O -->|has occurrent part| J
  J -->|has agent| U
  J -->|realizes| UR
  J -->|has output| D
  J -->|precedes| A
  D -->|is about| O
  D -->|is about| M
  P -->|precedes| M
  A -->|has input| D
  A -->|has output| V
  A -->|has output| S
  C -->|has occurrent part| A
  V -->|is about| C
  V -->|is about| M
  S -->|is about| D
  S -->|is about| V
  E -->|is about| A
  E -->|is about| D
  E -->|is about| V
  E -->|is about| S
  E -->|is about| P
```

J and A are different acts; D and V are different ICEs with the same affirmed
Ball/Strike content. C is the existing single operative counted process. The
Pitch Act and motion use their existing accepted relation. Review timing is
not assigned the pitch's exact interval, and the review is not an occurrent
part of the Pitch Act. The on-field umpire does not become the review agent
without evidence. No software agent, challenger agent or new persistent role
is inferred by this shape. Public affected-player attribution follows existing
actual batting participation at this pitch, with substitutions reconciled.
