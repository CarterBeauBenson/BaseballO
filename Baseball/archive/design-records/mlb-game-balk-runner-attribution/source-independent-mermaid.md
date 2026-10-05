# BK1 review pattern

All named classes and relations already exist. This diagram proposes their
application to a separately recorded balk; it is not executable authorization.

```mermaid
flowchart LR
    P[Plate Appearance]
    B[Balk Process]
    J[Umpire Judgment Act]
    D[Baseball Decision ICE]
    R[Balk Rule]
    A[Baserunning Act]
    E[Existing runner event record]
    B -->|occurrent part of — BFO_0000132| P
    B -->|has occurrent part — BFO_0000117| J
    B -->|is prescribed by — ont00001920| R
    J -->|occurrent part of — BFO_0000132| B
    J -->|has input — ont00001921| R
    J -->|has output — ont00001986| D
    D -->|is about — ont00001808| B
    E -->|is about — ont00001808| B
    E -->|is about — ont00001808| J
    E -->|is about — ont00001808| D
    E -->|is about — ont00001808| A
    A -->|occurrent part of — BFO_0000132| P
```

The existing record joins the independently evidenced running act to the
adjudicated balk. This does not assert that every part of the PA caused every
other part. Existing runner, role, origin, safe/run resolution and episode
patterns remain in place. The final batting result is not the Balk Process.
No umpire bearer is invented when the source does not identify the caller.
