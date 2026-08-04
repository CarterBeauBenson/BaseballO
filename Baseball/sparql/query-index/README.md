# Dehydrated query index

This directory defines a disposable, per-game materialized view of the complete
event graph. The authoritative graph remains unchanged and queryable. The view
exists to shorten common traversals without pretending that the shortcut
triples are the full ontological account.

For game `566279`, the graph contract is:

| Artifact | IRI |
| --- | --- |
| Authoritative graph | `https://w3id.org/baseball/graph/game/566279` |
| Query-index graph | `https://w3id.org/baseball/graph/query-index/game/566279` |
| Build metadata resource | `https://w3id.org/baseball/query-index-build/game/566279` |
| Operational vocabulary | `https://w3id.org/baseball/query-index/` |

The operational vocabulary is deliberately not declared in
[`ontology/`](../../ontology/). Its terms describe an implementation contract,
not new approved BaseballO axioms. In particular, `idx:agent` means that the
complete source pattern proved the named person is the relevant actor for the
indexed fact. It does not replace BFO participation or the contextual role
pattern in the authoritative graph.

## Component catalog

The builder executes the small `CONSTRUCT` queries in [`components/`](components/)
in filename order and merges their results.

| Component | Indexed fact | Evidence required before the shortcut is emitted |
| --- | --- | --- |
| `00-index-metadata.rq` | `idx:QueryIndex` | Game, source-graph, and contract identifiers supplied by the guarded builder |
| `10-game-dimensions.rq` | `idx:GameFact` | Game, mapped start timestamp, field, and venue chain |
| `20-plate-appearance-results.rq` | `idx:PlateAppearanceFact`, `idx:PlateAppearanceResultFact` | Batter act, CCO Person participant, enclosing game, one reviewed result class, and generic adjudication |
| `30-hits.rq` | `idx:HitFact` | Specific hit class, hit judgment, batter act/person, plate appearance/game, field, and venue |
| `40-pitches.rq` | `idx:PitchFact` | Pitch act, CCO Person pitcher, following pitch motion, plate appearance/game, field, and venue |
| `50-pitch-calls.rq` | `idx:PitchCallFact` | Complete pitch pattern, shared record, ball/strike process, and matching judgment |
| `60-batting-acts.rq` | `idx:BattingActFact` | Swing/bunt, CCO Person participant, matching batter role, and plate appearance/game |
| `61-contacts.rq` | `idx:ContactFact` | Swing/bunt, CCO Person participant, contact, batted-ball motion, plate appearance/game, field, and venue |
| `70-runner-resolutions.rq` | `idx:RunnerResolutionFact` | Source record, runner-resolution process, CCO Person participant, enclosing plate appearance and game, and matching safe/out/run judgment |
| `71-stolen-bases.rq` | `idx:StolenBaseFact` | Stolen-base process, CCO Person participant, enclosing plate appearance and game, and stolen-base judgment |
| `80-game-assignments.rq` | `idx:AssignmentFact` | Game-scoped home-team, away-team, umpire, or official-scorer role and its bearer |
| `90-labels.rq` | Labels | Labels already asserted in the authoritative per-game graph |

Every fact type requires `idx:derivedFrom` pointers to decisive source-graph
evidence. The index copies identities and labels but does not copy the evidence
individuals' complete descriptions.

## Building and testing

With loopback Fuseki running and an authoritative game graph loaded:

```powershell
.\scripts\pipeline\build-query-index.ps1 -GamePk 566279
.\scripts\pipeline\test-query-index.ps1 -GamePk 566279 -SkipBuild
```

The builder performs all `CONSTRUCT` requests into a temporary directory,
merges and validates them locally, and replaces the target named graph with one
Graph Store Protocol `PUT`. If generation or loading fails, it removes the
derived target graph so an old index cannot masquerade as current. Before a
build is recorded as current, the builder also runs the complete semantic
row-equivalence suite; a shape-valid but incomplete graph is rejected. The manual
importer rebuilds the index after replacing an authoritative game graph and
uses a hash of the complete generation contract for freshness checks.

The test suite compares exact distinct row sets for all eleven semantic
families in both directions, including a label-fidelity check that detects
encoding changes. The builder writes Fuseki's returned Turtle bytes directly
so UTF-8 labels are never round-tripped through Windows PowerShell's legacy
text decoding. The checked-in fixture currently yields 6,617 index
triples from 28,419 authoritative triples, with equivalent identities for 21
hits, 282 pitches, 185 pitch calls, 134 batting acts, 112 contacts, 113 runner
resolutions, one stolen base, and seven assignments.

## Query shape

The full hit pattern remains available for auditing. A query approved to use
the materialized view can use this smaller shape:

```sparql
PREFIX idx: <https://w3id.org/baseball/query-index/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?season ?venue ?player ?playerLabel (COUNT(DISTINCT ?hit) AS ?hits)
WHERE {
  GRAPH ?indexGraph {
    ?hit a idx:HitFact ;
         idx:agent ?player ;
         idx:game ?game ;
         idx:venue ?venue .
    ?game a idx:GameFact ;
          idx:season ?season .
    ?player rdfs:label ?playerLabel .
  }
}
GROUP BY ?season ?venue ?player ?playerLabel
```

Canonical canned queries and the UI compiler continue to query authoritative
graphs. The separate reviewed operational runner can select indexed companions
without changing either source:

```powershell
.\scripts\pipeline\run-reviewed-query.ps1 `
  -Name hits-by-player-and-venue `
  -Layer Auto
```

[`operational-query-routing.json`](operational-query-routing.json) records ten
measured routes. Auto mode selects the index for seven traversal-heavy pairs
and the authoritative layer for three neutral pairs. Before indexed execution,
the runner scopes the exact loaded graph set and checks every corresponding
contract hash, authoritative/index artifact hash, manifest count, loaded graph
count, and in-graph provenance record. A failed check falls back to
authoritative execution in Auto mode; explicit Indexed mode fails closed.
`-VerifyEquivalent` compares exact runtime rows before returning.

The contract-level classification of every canned query is recorded in
[`query-decision-matrix.md`](query-decision-matrix.md). Contract version 1 can
express 46 queries; `empty-games-prototype.rq` and `game-timeline.rq` remain
authoritative for completeness and temporal-evidence reasons.

Ten indexed companions under [`benchmarks/indexed/`](benchmarks/indexed/) span
all major query families. They are paired with the existing authoritative
queries by [`benchmark-pairs.json`](benchmarks/benchmark-pairs.json) and can be
run through the reproducible workflow documented in
[`benchmarks/query-index/`](../../benchmarks/query-index/).
The eight-game corpus results show meaningful median improvements for seven
traversal-heavy pairs (2.16x to 9.34x) and effectively neutral results for the
three simple lookup pairs. Direct TDB2 execution traces are stored beside the
timing baselines.

## Dehydration and rehydration boundary

The query index alone cannot reconstruct acts, physical processes, judgments,
decisions, records, roles, or temporal structure. Rehydration therefore means
reloading or rematerializing the authoritative graph from the preserved raw
JSON plus the recorded RML, context-builder, mapper, and hash provenance, then
regenerating this index. The content-addressed raw archive and full graph are
never deleted by the index builder.

The executable portable archive and exact-restore contract is documented in
[`dehydration-package.md`](dehydration-package.md). It packages the raw bytes,
both RDF serializations, both build manifests, and all relevant generator and
validation files in a closed SHA-256 inventory.
