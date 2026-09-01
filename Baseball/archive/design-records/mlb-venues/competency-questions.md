# Competency questions

## Source ownership and accepted central entities

1. Which venue fields already occur in the authoritative MLB game payload?
2. Would a standalone venue endpoint add semantic evidence, or only widen
   coverage and alter refresh cadence?
3. Which independently identified Baseball Venue is designated by the MLB
   venue identifier and Proper Name?
4. Which Baseball Venue and Baseball Field Site each environs a Baseball Game,
   without asserting an unreviewed direct relation between the material venue
   and spatial site?
5. Which source record and retrieval context support each assertion without
   confusing the record, physical venue, and spatial field site?

## Deliberately unresolved bindings

6. What Geospatial Position is represented by the default coordinates, which
   physical point is located there, and which Coordinate Reference System
   supplies their interpretation?
7. What two Fiat Points stand in each reported Distance Quality, along what
   intended field path or boundary, and in which unit?
8. What two Fiat Lines intersect at the shared Fiat Point of the reported
   Angle Quality for azimuth, in which reference frame and unit?
9. What Altitude inheres in which entity, relative to which vertical datum,
   and in which unit?
10. What entity or configuration is counted by capacity, at what time?
11. Does `turfType` classify a Baseball Field Site, a material surface layer,
    a playing-surface artifact, or something else?
12. Does `roofType` classify a Baseball Venue, an enclosure design, a roof
    artifact, or a temporary state?
13. Are time-zone offsets response-time observations, game-time facts, or
    claims scoped to a requested season?

Questions 6–13 remain design blockers. Generic Measurement or Classification
ICEs must not replace their missing world-side targets.
