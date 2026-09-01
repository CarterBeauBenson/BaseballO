# Competency questions and accepted answers

1. Which module owns baseball games, plays, pitches, roles used in games, and
   other event facts?
   **Accepted:** `mlb-game`.
2. What may the game graph retain about reference entities?
   **Accepted:** canonical identity links needed to identify participating
   teams, people, and venues; reference descriptions belong to their owning
   modules after cutover.
3. Which module owns team, league, division, and season reference facts?
   **Accepted:** `mlb-organizations`.
4. Which module owns person reference and descriptive facts?
   **Accepted:** `mlb-people`.
5. Which module owns venue reference and physical facts?
   **Accepted:** `mlb-venues`.
6. Which module owns transaction records and supported world-side transaction
   processes?
   **Accepted:** `mlb-transactions`.
7. Where are facts from independently promoted sources joined?
   **Accepted:** in the authoritative triple store, through canonical
   identities and explicitly scoped SPARQL.
8. May one module's RML or source SHACL validate another source?
   **Accepted:** no. Each module owns an independent NiFi lane, RML, SHACL,
   staging, quarantine, evidence, and graph namespace.
9. May the ownership cutover remove existing authoritative MLB-game RDF?
   **Accepted:** no. Existing promoted RDF persists unless the ontologist later
   authorizes removal.
10. When may duplicate reference assertions be removed from future game RDF?
    **Accepted:** only after reference graphs are populated and integrated
    query, index, serving, and disconnect behavior pass equivalence review.
