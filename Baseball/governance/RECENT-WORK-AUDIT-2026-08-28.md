# Recent semantic work audit: 2026-08-28

## Scope and method

This is a read-only Git-history audit of `dev` from 2026-08-21 through commit
`cb16a8e`. The repository has no commits dated August 21 through August 25; the
reviewed change sequence begins on August 26. The audit compared ontology,
overlay, mapping, semantic context, SHACL, Mermaid, proposal, SPARQL, serving,
and UI history.

This report distinguishes executable semantic changes from documentation and
infrastructure. It does not declare work invalid merely because it occurred in
the same time window.

## Verdict

The Statcast chain bypassed the required ontology-curation lifecycle and was
semantically unsound. It reached every downstream layer before the first
source-independent Mermaid review. Its active repository implementation has
now been removed.

The active MLB game mapping, source SHACL, and semantic context builder were
not rewritten by that chain. They are byte-identical to their pre-Statcast
versions, but they carry 13 older semantic blockers and therefore remain frozen
and unratified.

The acquisition, detachable-module, NiFi, persistence, benchmarking, and SQL
serving work is not automatically invalid. Its technical controls require
their own verification, and any derived data that depends on blocked RDF must
be rebuilt after semantic correction.

## Rejected Statcast chain

The order of these commits demonstrates that implementation preceded review:

| Commit | Executable effect | Audit disposition |
| --- | --- | --- |
| `1253bdd` | Proved a transient CSV-to-MLB pitch join without changing the ontology or authoritative RDF mapping | Technical feasibility evidence, not semantic approval; later removed so the Statcast restart would not inherit its assumptions |
| `07a428f` | Added 16 Statcast/provider-field ICE classes to `BaseballO.ttl`, 15 overlay axiom blocks, a JSON direct-mapping contract, a Python N-Triples renderer and graph loader, Statcast-aware SPARQL, and UI changes | Rejected: field-specific ICEs hid unmodeled world-side qualities and geometry; direct rendering replaced the reviewed RML lifecycle |
| `a6e13f4` | Folded rejected Statcast vocabulary and evidence into the shared plate-appearance query | Rejected downstream dependency |
| `9d9d5de` | Added a 278-line Statcast SHACL profile and procedural validators around the rejected model | Rejected: structural consistency did not establish semantic correctness |
| `42fbdc1` | Exposed the unified Statcast evidence in Explorer | Rejected downstream exposure |
| `b32281a` | Added a source-coverage inventory after implementation | Useful postmortem material, but not prior review |
| `b7fef83` | Added source-independent and source-specific Mermaid after implementation | Too late to serve as the required design gate |
| `927219a` | Documented active defects in the implemented graph | Confirmed the rejection evidence |
| `0cd639f` | Removed rejected Statcast ontology terms, mapping, SHACL, acquisition, graph-audit, serving fields, tests, evidence, SPARQL branches, and UI exposure | Removal commit |

The decisive failure was not merely that some class definitions needed
editing. One source row was treated as a compact semantic schema: speed,
angle, distance, expected outcomes, and contact classifications were placed in
provider-specific ICE classes without first modeling the qualities, relations,
geometry, processes, estimates, and measurement acts in reality.

The implementation used `mappings/statcast/statcast-direct.json` plus direct
Python triple construction rather than approved Mermaid followed by RML. SHACL
then enforced the shape of that flattened account. The proposal and diagrams
arrived only after ontology, RDF generation, query, and UI work had already
been published.

### Removal confirmation

At `cb16a8e`, Git contains no active Statcast ontology vocabulary, RML or direct
mapping, source SHACL, acquisition/graph-validation implementation, semantic
SPARQL branch, serving column, UI field, or registered source module. Remaining
uses of the word "Statcast" are planning, audit, source-boundary documentation,
or observed MLB schema fields; they are not an active Statcast implementation.

This statement confirms repository state. It does not independently attest to
the contents of an external or previously running Fuseki dataset.

## Ontology release-metadata residue

The rejection commit removed the Statcast class and axiom bodies but retained
six release-metadata edits introduced with them:

- `BaseballO.ttl`: `owl:versionIRI`, `owl:versionInfo`, and
  `dcterms:modified`; and
- `BaseballO-axioms-overlay.ttl`: the same three properties.

The files still declare version `0.5.0` and date `2026-08-26`. Compared with
the parent of `07a428f`, their class and axiom bodies are identical; only those
six metadata lines differ.

This audit does not choose between restoring `0.4.1`, issuing a corrective
version, or retaining `0.5.0` with an explicit release explanation. That is an
ontology-release decision for the ontologist. Automation must not silently
edit it.

## Active MLB semantic baseline

The following active files have the same Git blob as immediately before the
rejected Statcast implementation:

| Artifact | Current path | Git blob |
| --- | --- | --- |
| MLB game RML | `sources/mlb-game/mapping/mlb-game.rml.ttl` | `15dc0ed4ab9da45a096de04e2cfdce954615dfb7` |
| MLB authoritative SHACL | `sources/mlb-game/shacl/authoritative.ttl` | `09d57d360ac117c14a04defa0b5c6335d6123209` |
| RML context builder | `scripts/pipeline/prepare-rml-context.py` | `64354c7deac525bc7a1faf3edfebabf5c3d1521d` |

The files were relocated into a detachable `mlb-game` module and their paths
and ownership documentation were updated. Relocation did not correct their
older semantics.

### Thirteen active blockers

The detailed evidence and migration implications are in
[`../sources/mlb-game/SEMANTIC-AUDIT.md`](../sources/mlb-game/SEMANTIC-AUDIT.md).
Its blockers are:

1. `PitchActMap` uses a direct identifier instead of the accepted Identifier
   ICE pattern.
2. the plate-appearance start-out-count ICE has no approved world-side count or
   counting pattern;
3. coordinate and location individuals are emitted without coordinate values;
4. overturned replay reviews synthesize an opposite original decision despite
   that inference remaining unresolved in the accepted design record;
5. shared event, review-status, and pitch-call tokens are used as record
   identifiers or types without an accepted classification/data-element
   account;
6. runner classifications and nearest-pitch association are treated as
   evidence for a physical pitch-ball control failure;
7. broad event-record aboutness can substitute for missing real-world
   relations;
8. pitch and batted-ball measurements remain deferred pending an approved
   world-side pattern;
9. the sacrifice-bunt gate misclassifies non-sacrifice bunts as swings and
   omits observed `W`, `L`, and `M` pitch-call evidence;
10. unfiltered `PlaySource` creates a plate appearance and result from an
    incomplete rain `game_advisory` record;
11. institutional `movement.end` is treated as evidence of a physical
    `BaseTouchingProcess`;
12. the last `allPlays` member's end time is treated as the game end, including
    when that member is an administrative advisory; and
13. game type is absent from authoritative RDF, so current SQL game-set
    classification still depends on acquisition and schedule evidence.

These blockers predate the August 26-28 Statcast chain. Their age does not make
them accepted. They prevent the current mapping from serving as a clean
template for MLB-game expansion or another source.

## Derived-query impact

The PAQ-1.0 formula was a user-directed analytical design, not an ontology
class. Its current inputs are nevertheless contaminated by blockers 9 and 10:

- grind counts consume swing, contact, and foul facts whose bunt/call coverage
  is known to be wrong; and
- the plate-appearance population can include an incomplete administrative
  advisory as a completed plate appearance and terminal result.

The same call-modeling issue affects whiff/take analysis. Empty Games depends
on the unresolved plate-appearance start-out-count pattern. Therefore a query
or SQL implementation can reproduce current RDF exactly and still reproduce a
semantic error.

The source-scope catalog also remains incomplete as an enforcement boundary:
35 static single-source SPARQL files use unrestricted `GRAPH ?graph`. The
Explorer's compiled fallback has a separate MLB graph guard, but the static
artifacts do not yet prove source isolation.

## Work not automatically rejected

The following work should be evaluated on its own contracts rather than swept
into the Statcast rejection:

- transient API acquisition and the daily schedule;
- asynchronous NiFi submission, retry, quarantine, provenance, and atomic
  promotion controls;
- detachable source-module layout and graph ownership;
- indexed-RDF and benchmark evidence controls;
- SQLite build integrity, atomic pointer promotion, and rebuildability; and
- Explorer layout, Unicode corrections, and desktop-launcher maintenance that
  do not assert rejected semantic content.

This is not blanket approval. In particular, current SPARQL-to-SQL equivalence
is still pending for routes beyond the admitted visible slice, and materialized
rows must be regenerated after authoritative RDF corrections.

## Governance disposition

| Category | Current disposition |
| --- | --- |
| Rejected Statcast ontology and ingestion | Removed; do not restore or imitate |
| Six ontology release-metadata edits | Awaiting explicit ontologist decision |
| Active MLB semantic baseline | Frozen and unratified; expansion blocked |
| PAQ, whiff/take, and Empty Games claims | Retained for research continuity but semantically qualified until upstream corrections |
| Infrastructure and serving mechanics | Retained, subject to their technical validation and later RDF rebuilds |
| New source work | Proposal and source-independent Mermaid first; no executable implementation before acceptance |
