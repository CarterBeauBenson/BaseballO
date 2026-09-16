# Live refresh performance and upheld runner reviews

This follow-up implements E1 final-state reconciliation within the accepted
C1/C3 personal-history pattern and optimizes the existing NiFi SQL stage.
The C3 decision was published in `06cc732` before implementation. No RML
templates, ontology terms, object properties, review identities, review
mechanisms or metric meanings change. The global freeze remains unratified.

## Publication delay

The live August 25 dashboard request rejected the stale SQL build with HTTP
503. NiFi's current source proof had passed RML/SHACL and promotion; its SQL
build was checking a corpus of 2,732 promoted game directories. Fuseki logs
showed repeated 30-second timeouts in the grouped source-count query, followed
by smaller-batch retries. These were query execution delays, not an absence
of source data or permission to omit games.

The replacement uses fixed named-graph aggregate branches. Empty or missing
graphs still yield no row. Every index branch still requires its exact index
resource, source graph and game identity. The same independent promotion
inventory, exact counts, before/after corpus checks and atomic publication
remain required. The helper participates in loaded-code validation and the
source recovery revision, so changed code cannot silently enter an old build.

- Six real games: identical old/new bindings; source count 3.8471 seconds to
  0.2375 seconds, index count 0.2147 seconds to 0.0831 seconds.
- A 200-game live batch: source counts in 8.2268 seconds and index counts in
  2.5227 seconds. All 400 counts matched the retained promotion records.
- These are bounded measurements on the current machine and data, not a
  guaranteed full-build duration. No complete corpus build was run manually.

See [six-game equivalence](query-equivalence.json) and
[200-game count evidence](query-batch.json).

## Runner effects

Two unchanged source records explicitly describe completed, upheld tag reviews:

| Game / PA / event | Source outcome | Admitted history effect |
| --- | --- | --- |
| 823826 / 68 / 3 | Eli White caught stealing second; `MA`, completed, not overturned | End White's distinct pinch-runner history at its existing C3 action boundary. |
| 825042 / 70 / 4 | Jose Fernandez steals second; `MA`, completed, not overturned | Retain Fernandez's own existing advance episode before his later scoring episode. |

The parser requires agreement among the explicit narrative, runner name,
movement identity and bases, review disposition, event/out flags, and ball,
strike and out counts. It rejects pending, overturned, contradictory,
duplicated and unaccounted records. Existing C1/C3 time, entry/termination and
episode checks remain separate requirements. No review is added to RDF and
no original decision, affected batter or challenge mechanism is inferred.

MLB distinguishes unchanged and overturned replay outcomes; tag plays are
reviewable. [MLB replay reference](https://www.mlb.com/glossary/rules/replay-review).
The exact records above supply the disposition used here; the reference does
not independently establish their event identities or a complete review census.

The [15-game source comparison](coverage.json) increases complete personal
histories from **12 to 13 games**, and supported histories from **404 to 409**.
Every previously selected lifetime and episode allocation is preserved.

The [two isolated RML cases](one-history-rml.json) pass exact source-bound
SHACL. Whole game **825042** then passes authoritative Jena SHACL with
**29,498 triples**, **22 personal histories** and **41 episode memberships**;
its complete history population is [admitted](history-admission.json).
The [canonical Jena-to-SQL proof](scoring-sql.json) resolves all **nine runs**
for both **Scoring History Length** and **Run Contributors**, with exact SQL
retention and isolated one-game player means. The public date-range request
still requires independent schedule admission. [RML proof](rml-proof.json);
[source census](source-census.json).

**109 focused tests passed**, including five actual-RML subcases in one test,
the negative runner/review cases, existing runner-history regressions,
materializer checks, grouped/fixed-graph query equivalence, and recovery
fingerprint/idempotency tests. These are component checks; NiFi owns the full
repository gate.

## Remaining scope

- Game 823585 still has an explicitly placed runner with no recorded episode;
  C3's accepted one-or-more-episodes requirement still withholds that half.
- Game 823826 PA 61 still has the third-out base-state conflict. No missing
  advance, final base or physical location is invented.
- PA-start boundaries, complete defensive populations, review producers and
  complete reference-season admissions remain separate release requirements.

NiFi owns the existing asynchronous retry, refresh and repository gate. Its
acquisition and recovery schedules are unchanged. This evidence does not
claim that the live dashboard is fully populated.
