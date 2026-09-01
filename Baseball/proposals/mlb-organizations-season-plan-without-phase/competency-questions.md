# Competency questions

## Decision requested

1. When an MLB league response supplies a valid league ID and season code but
   no complete accepted regular-season or postseason date pair, which policy
   applies?

   - **Option A — complete-pair gate:** this response does not yet warrant an
     emitted Baseball Season or Baseball Season Plan subgraph.
   - **Option B — season-code evidence:** this response warrants the Baseball
     Season and Baseball Season Plan even though its promoted graph may omit a
     Baseball Season Phase that exists but is not evidenced in this response.

2. Under Option A, what happens to isolated valid date fields from an
   incomplete pair?

   **Candidate consequence:** retain them only in transient acquisition and
   persistent provenance evidence for this release. The accepted Date
   Identifier is a continuant part of the Baseball Season Plan, so it must not
   be emitted after the Plan subgraph is withheld.

3. Under Option B, does the absence of a Phase triple assert that the Plan has
   no Phase?

   **Candidate answer:** no. RDF and OWL remain open world. The source graph is
   incomplete with respect to the Plan's Phase, and source SHACL must permit
   zero locally asserted Phase values while still allowing at most the two
   reviewed phase keys.

4. Does either option permit a Phase from a partial boundary pair?

   **Candidate answer:** no. A regular-season Phase still requires both
   `regularSeasonStartDate` and `regularSeasonEndDate`; a postseason Phase
   still requires both `postSeasonStartDate` and `postSeasonEndDate`.

5. Does either option add a Date-to-Phase or Day-to-Phase relation?

   **Candidate answer:** no. Those relations remain blocked.

## SHACL consequences

- **Option A:** retain `sh:qualifiedMinCount 1` for a Plan's prescribed Phase;
  add source-context and regression checks proving that zero or partial pairs
  emit no Season/Plan subgraph.
- **Option B:** change the Plan's Phase constraint to allow zero and at most
  two locally asserted reviewed Phases; retain the Phase-to-Season and
  Plan-to-Phase constraints whenever a Phase is present. Add a negative test
  proving that zero does not become an explicit absence claim.
- Under both options, malformed present dates fail before RML, while null or
  absent dates are not treated as malformed.
