# Source evidence

The user supplied a mounted Samsung T5 EVO SSD and explicitly directed BaseballO to store as much RDF on it as makes operational sense. The existing architecture identifies persistent authoritative RDF as the semantic research record and indexed RDF as a rebuildable RDF acceleration layer. Both are held by the same Fuseki/TDB2 state and therefore move together.

Transient API payloads, NiFi orchestration state, pipeline work, and the derived SQL serving database remain under the local BaseballO state root. The external store is identified by a machine-local pointer and a unique marker on the target volume; neither contains or changes ontology semantics.
