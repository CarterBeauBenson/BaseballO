# Accepted resolution and award relations


The new properties below are defined in
[resolution-links.ttl](resolution-links.ttl); their evidence and interpretation
are specified in [resolution-links-review.md](resolution-links-review.md).
This section supersedes the missing award/destination edges in the original
diagrams above. It does not resolve their immediate-before or completeness gaps.

```mermaid
flowchart LR
  W["base:WalkProcess or base:HitByPitchProcess"]
  S["base:SafeProcess: one particular resolution"]
  P["cco:ont00001262: resolved Person"]
  B["base:Base: adjudicated first, second or third"]
  T["obo:BFO_0000008: resolution Temporal Region"]
  E["obo:BFO_0000203: last instant, when supported"]
  J["base:SafeJudgmentAct"]
  D["base:SafeDecisionICE"]
  S -.->|"proposed base:hasResolvedRunner"| P
  S -.->|"proposed base:hasAdjudicatedBase"| B
  S -.->|"proposed base:settlesAwardFrom"| W
  S -->|"obo:BFO_0000057"| P
  S -->|"obo:BFO_0000117"| J
  J -->|"cco:ont00001986"| D
  D -->|"cco:ont00001808"| S
  S -->|"obo:BFO_0000199, if supported"| T
  T -->|"obo:BFO_0000224, if supported"| E
```

The award edge applies only to the supported walk/HBP cases. A Safe Process
following a hit can have the same adjudicated-base and resolved-runner links
without an award edge. A forced scoring arrival uses a distinct Run Process
with a resolved-runner and award link; `hasAdjudicatedBase` is not used as a
substitute for counted-run semantics. Each resolution preserves its existing
PA and Game context. The diagram does not assert an exact timestamp merely
because an enclosing source event has one.

There is no Person-to-Base arrow whose time is supplied only by a label.
The Safe Process is the existing event-scoped intermediary. Its adjudicated
base does not assert continued physical occupancy or continued entitlement
afterward. The original PA-start location stasis is separate.
