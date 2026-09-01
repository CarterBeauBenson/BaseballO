# Consolidated accepted Mermaid surface

The source-independent graph shape is the union of the nineteen exact Mermaid
artifacts linked from
[`../FINAL-MLB-RML-REVIEW.md`](../FINAL-MLB-RML-REVIEW.md). Each component
package pins its own Mermaid SHA-256 and remains the authoritative diagram for
that modeling boundary.

```mermaid
flowchart LR
    PEOPLE[Persistent Persons and their SDCs]
    ORGS[Persistent Teams, Leagues, and Divisions]
    VENUES[Persistent Venues, parts, Sites, Functions, and Qualities]
    EVENTS[Grounded Acts and Role-transition Processes]
    DAYS[Canonical source-neutral Days]
    INFO[Source records, decisions, descriptions, and measurements]

    INFO -->|is about or designates| PEOPLE
    INFO -->|is about or designates| ORGS
    INFO -->|is about, designates, or measures| VENUES
    INFO -->|is about| EVENTS
    EVENTS -->|occupy temporal regions associated with| DAYS
    PEOPLE -->|bear persistent Roles participating in| EVENTS
    ORGS -->|provide reviewed organizational context for| EVENTS
```

This overview does not replace or broaden any component diagram. It authorizes
only the ontology files named in `review.json`; executable RML remains blocked
until source-specific shapes are accepted.
