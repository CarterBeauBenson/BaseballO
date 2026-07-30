# Venue, field, and batted-ball location

\`\`\`mermaid
flowchart LR
    GAME["BaseballGame"] -->|"occurs at"| FIELD["BaseballFieldSite"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]
    OCC["Pitch, swing, contact, motion, judgment, or result"] -->|"occurs at"| FIELD
    CRS["BaseballFieldCoordinateReferenceSystemICE"] -->|"is about"| FIELD
    COORD["BaseballFieldCoordinateICE"] -->|"is about"| CRS
    COORD -->|"designates"| LOCATION["BattedBallLocationSite"]
    MOTION["BattedBallMotionProcess"] -->|"occurs at"| LOCATION
    RECORD["Pitch Event Record"] -->|"is about"| COORD
    RECORD -->|"is about"| LOCATION
\`\`\`

The venue and field site are distinct individuals. When hitData.coordinates exists, the RML creates a coordinate ICE and a designated location site. Raw coordX and coordY values remain deferred because no approved datatype properties represent them.
