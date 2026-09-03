# Reusable DSQ query modules

This package is the reviewed boundary between BaseballO's semantic graph
implementation and new decision-support questions. A DSQ author selects known
grains and dimensions in JSON; the compiler emits complete, reviewable SPARQL.
The author does not need to rediscover the accepted RML and SHACL paths for
every question.

The modules do not replace the ontology, RML, SHACL, or authoritative RDF.
There are two deliberately separate catalogs:

- [`catalog.json`](catalog.json) contains event-analysis consumers over the
  rebuildable MLB-game query index.
- [`authority/catalog.json`](authority/catalog.json) contains identity and
  attribute consumers over independently promoted People, Team, League,
  Division, Venue, and Transaction evidence graphs.

The index catalog is pinned to the query-index semantic contract. The authority
catalog is pinned to each owning source's approved RML and SHACL artifacts and
checks the live source registry and semantic-status record. Both catalogs pin
the exact bytes of every fragment. Contract drift fails closed.

## Version 1 boundary

Version 1 deliberately compiles a small safe subset:

- exactly one primary fact grain per query;
- zero or more explicitly allowlisted game dimensions;
- labels for variables already bound by the selected grain;
- injection-safe `VALUES` restrictions;
- `COUNT(DISTINCT ...)` measures only;
- additive SQL merge contracts over disjoint game-graph partitions.

It will not silently compose two event grains, accept arbitrary SPARQL text,
calculate an average inside a batch, or query a source/layer not named in the
catalog. A DSQ needing a fact-to-fact join must first receive an explicit,
tested bridge module. A rate or average must persist its additive numerator and
denominator and calculate the final value after the partitions are combined in
SQL.

The 15 index modules expose every fact grain in
[`query-index/semantic-contract.json`](../query-index/semantic-contract.json),
plus the index scope and reusable season, venue, and game-start dimensions.
The three specifications under [`specs/`](specs/) prove the initial shape with
hits, plate appearances, and team assignments. Existing canned queries remain
unchanged and authoritative/index routing remains governed by its existing
equivalence evidence.

The 18 authority modules expose Person, Organization, Venue, and Day primary
grains plus reusable Proper Name, Nickname, provider identifier, height, mass,
decimal/integer measurement, batting-side, throwing-side, nominal
classification, position-description, venue-coordinate, venue-capacity, and
playing-surface patterns. They preserve the world-side Quality, Disposition,
Site, and entity plus the measurement or classification ICE; a field value is
never substituted for that structure. See [`authority/`](authority/).
The 16 checked authority specifications cover reusable names, nicknames,
provider identifiers, height, mass, batting and throwing sides, positions,
venue coordinates, capacities, playing surfaces, and calendar days.

## Compiling a DSQ

From the `Baseball/` directory, validate the reusable contract:

```powershell
python scripts/pipeline/compile-dsq-query.py --validate-catalog
```

Compile a reviewable query:

```powershell
python scripts/pipeline/compile-dsq-query.py `
  --spec sparql/query-modules/specs/hits-by-season.json `
  --output $env:TEMP/hits-by-season-modular.rq `
  --manifest $env:TEMP/hits-by-season-modular.manifest.json
```

For a one-game proof, pass one exact index graph. The compiler writes a concrete
named-graph clause, avoiding the expensive variable-graph plan observed during
serving-layer diagnosis:

```powershell
python scripts/pipeline/compile-dsq-query.py `
  --spec sparql/query-modules/specs/hits-by-season.json `
  --index-graph https://w3id.org/baseball/graph/query-index/game/566279 `
  --output $env:TEMP/hits-by-season-566279.rq
```

NiFi may pass multiple disjoint game graph IRIs for a bounded backfill batch.
The compiler emits a validated `VALUES ?indexGraph` scope. Batch size is an
operational parameter selected from current measurements; it is not embedded
in the semantic query specification. The optional deterministic manifest pins
the DSQ, module catalog, fragments, query-index semantic contract, selected
graphs, reducer, and compiled query for downstream provenance.

Authority grains use the same compiler with their own catalog. For example:

```powershell
python scripts/pipeline/compile-dsq-query.py `
  --catalog sparql/query-modules/authority/catalog.json `
  --spec sparql/query-modules/authority/specs/people-heights.json `
  --authority-graph https://w3id.org/baseball/graph/authority/mlb-people/2026 `
  --output $env:TEMP/people-heights.rq `
  --manifest $env:TEMP/people-heights.manifest.json
```

An authority result always includes `authorityGraph`. Its SQL partition is
replaced atomically when that source graph is rematerialized. Names remain Name
ICE evidence, and measurements retain the Quality, Measurement ICE, value, and
unit. Downstream SQL may choose a display label, but that presentation rule is
not embedded in the semantic consumer.

## Adding a question

1. State the DSQ's human claim and result grain.
2. Choose the index or authority catalog and select one admitted primary module
   plus only its allowlisted enrichments.
3. For index aggregates, persist additive sufficient statistics rather than a
   batch average. For authority attributes, persist graph-scoped evidence rows
   and replace the complete source-graph partition.
4. Compile and inspect the generated SPARQL.
5. Run it in bounded game partitions through NiFi and store its reusable rows
   in the analytical database.
6. Prove its RDF result and SQL reduction equivalent before admitting a UI
   route.

If no module represents the needed evidence, that is useful information. Add
an accepted RDF/index/serving grain and its validation evidence first; do not
smuggle a new semantic assumption into a query fragment.
