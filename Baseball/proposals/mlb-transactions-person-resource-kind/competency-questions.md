# Competency questions

## Decision requested

1. What establishes the canonical Person IRI for a transaction row's
   non-null `person.id`?

   - **Option A — provider guarantee:** accepted source evidence proves that
     this endpoint's Person is always player-kind, so the deterministic target
     is `data/player/{id}`.
   - **Option B — authority resolution:** NiFi resolves the ID through the
     promoted canonical Person identifier pattern and passes the unique
     `player` or `person` IRI into the source-local execution context.

2. Under Option A, what happens if corpus inspection discovers a transaction
   Person represented canonically as `data/person/{id}`?

   **Candidate consequence:** fail the identity gate and quarantine the row;
   do not mint a second `data/player/{id}` Person by assumption.

3. Under Option B, what happens when no promoted canonical Person is found?

   **Decision needed:** either quarantine pending authority acquisition, or
   preserve the information-layer row without Person aboutness while keeping
   `person.id` in its content hash. Do not invent an `unknown` Person.

4. Under Option B, what happens when both path kinds resolve for one provider
   ID?

   **Candidate consequence:** treat it as an identity conflict requiring
   review. Do not select a path by ordering, string preference, or current
   source status.

5. May transaction RML query or validate the MLB people source directly?

   **Candidate answer:** no. Authority resolution, if selected, is a NiFi
   identity-input step against already promoted authoritative RDF. The
   transaction RML and SHACL remain source-owned and receive only the resolved
   canonical IRI in their execution contract.

6. When may a row-scoped Death use that Person as participant?

   **Candidate answer:** only after the existing exact Death-code gate and the
   selected unique Person-resolution gate both pass. Source dates still do not
   become Death boundaries.

7. Does resolving a player-kind IRI create or evidence a Player Role?

   **Candidate answer:** no. Resource-kind identity resolution does not infer
   occupation, team context, role history, or participation in a game.
