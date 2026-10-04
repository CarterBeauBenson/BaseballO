# Existing participation and realization pattern

```mermaid
graph LR
  earlier[Earlier Pitch Act] -->|has participant| outgoing[Outgoing Person]
  later[Later Pitch Act] -->|has participant| incoming[Incoming Person]
  earlier -->|realizes| oldrole[Outgoing person's persistent Pitcher Role]
  later -->|realizes| newrole[Incoming person's persistent Pitcher Role]
  oldrole -->|inheres in| outgoing
  newrole -->|inheres in| incoming
  earlier -->|occurrent part of| pa[Plate Appearance]
  later -->|occurrent part of| pa
  pa -->|has participant| outgoing
  pa -->|has participant| incoming
```

This reuses BFO participation, realization, inherence and occurrent parthood.
It creates no new relation, role identity or temporal-order assertion.
The existing Stasis of Role pattern persists; a stasis does not realize a Role.
