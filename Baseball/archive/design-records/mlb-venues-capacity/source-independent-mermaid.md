# Source-independent Mermaid

```mermaid
flowchart LR
    VENUE[Baseball Venue]
    SEAT[Spectator Seat]
    SITFUNC[Sitting Artifact Function]
    STANDING[Standing-Room Spectator Site]
    AMOUNT[Spectator Accommodation Amount]
    MEASUREMENT[Measurement Information Content Entity]
    VALUE[positive integer value]
    USE[Person-support or spectator-use Process]
    PERSON[Person]

    SEAT -->|continuant part of| VENUE
    STANDING -->|continuant part of| VENUE
    SITFUNC -->|inheres in| SEAT
    USE -->|realizes| SITFUNC
    USE -->|has participant| PERSON
    AMOUNT -->|inheres in| VENUE
    MEASUREMENT -->|is a measurement of| AMOUNT
    MEASUREMENT -->|has integer value| VALUE
```

The Venue may be empty while the Amount and Functions continue to exist. The
source measurement does not assert that the use Process is occurring, and it
does not enumerate accommodation parts from the numeric total.
