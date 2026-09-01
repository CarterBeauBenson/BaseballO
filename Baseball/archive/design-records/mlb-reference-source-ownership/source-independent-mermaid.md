# Accepted source-ownership shape

This diagram assigns fact ownership and integration boundaries. It does not
specify any source-specific RDF triple shape.

```mermaid
flowchart LR
    GAME[MLB game module\ngame and event facts]
    ORG[MLB organizations module\norganization and season reference facts]
    PEOPLE[MLB people module\nperson reference facts]
    VENUE[MLB venues module\nvenue and physical facts]
    TX[MLB transactions module\nrecords and supported processes]
    STORE[(Persistent authoritative triple store)]
    DERIVED[Rebuildable indexed RDF and SQL]

    GAME -->|independent validation and promotion| STORE
    ORG -->|independent validation and promotion| STORE
    PEOPLE -->|independent validation and promotion| STORE
    VENUE -->|independent validation and promotion| STORE
    TX -->|independent validation and promotion| STORE
    STORE -->|explicitly scoped SPARQL| DERIVED
```

Every module has a separate NiFi lane, mapping, source SHACL profile, staging,
quarantine, evidence, and graph namespace. Canonical identities meet only in
the triple store. Shared execution code may orchestrate the same lifecycle but
does not own a source's semantics.
