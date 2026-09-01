# Competency questions

| ID | Question | Candidate answer |
| --- | --- | --- |
| COORD-01 | Which point is located? | A provider-selected Baseball Venue Reference Point. Do not specialize it as Home Plate, entrance, or centroid without evidence. |
| COORD-02 | Which CRS interprets the values? | CCO World Geodetic System 1984 (`cco:ont00001630`). |
| COORD-03 | What does the coordinate ICE designate? | The Baseball Venue Reference Point, which is a Geospatial Position and Fiat Point in reality. |
| COORD-04 | How are corrections represented? | Keep the reference-point identity stable when supported and content-version coordinate evidence; conflicting values do not invent motion. |
| COORD-05 | What happens for incomplete or malformed coordinates? | Null/absent pairs emit nothing. Partial, nonnumeric, or out-of-range pairs quarantine before RML. |

## Negative tests

- Latitude/longitude literals are not the physical point.
- The coordinate ICE is not the Venue.
- The reference point is not silently typed as Home Plate, entrance, or centroid.
- A changed response does not imply that the Venue moved.
