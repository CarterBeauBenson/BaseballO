# Storage selection inventory

| Artifact family | Placement | Rationale |
|---|---|---|
| Fuseki authoritative RDF | External SSD | Persistent, high-volume semantic record |
| Fuseki indexed RDF | External SSD | High-volume RDF in the same transactional TDB2 store; rebuildable but useful |
| Fuseki RDF backups | External SSD | Owned by the external Fuseki state |
| Transient API payloads | Local transient state | Deleted after validated promotion |
| NiFi repositories and orchestration state | Local state | Operational state, not RDF research record |
| Pipeline RDF staging | Local state | Temporary/rebuildable transformation artifacts |
| Analytical SQLite serving database | Local state | Derived serving layer, not authoritative RDF |
| Repository ontology and mappings | Git repository | Version-controlled semantic definitions, not runtime data |
