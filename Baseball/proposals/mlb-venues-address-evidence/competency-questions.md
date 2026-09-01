# Decisions needed

| ID | Question | Decision options |
| --- | --- | --- |
| ADDRESS-01 | What is an address in the graph? | Candidate Designative ICE that designates a delivery/location Site, not the material Venue itself. |
| ADDRESS-02 | Which components are semantic parts versus display text? | Review address lines, city, administrative region, postal code, and country independently. |
| ADDRESS-03 | How are geographic entities identified? | Require independent identifiers/reference systems; matching strings do not establish identity. |
| ADDRESS-04 | How are historical addresses scoped? | Content-version the Address ICE and require evidence before asserting a validity interval. |
| ADDRESS-05 | What relates the Venue to the addressed Site/content? | Reuse an accepted relation only after the target is selected; do not invent an address convenience property. |

