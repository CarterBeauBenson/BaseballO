# Dehydration package contract

Package version 1 is a portable, closed inventory for one completed game. It
preserves both exact graph serializations and the materials needed to audit or
regenerate them. The smaller query index is never treated as sufficient to
reconstruct the authoritative event graph.

## Contents

| Package area | Purpose |
| --- | --- |
| `raw/` | Byte-identical completed-game JSON that remains the ultimate instance-data source |
| `rdf/authoritative-*.ttl` | Exact validated full event graph |
| `rdf/query-index-*.nt` | Exact disposable shortcut graph |
| `provenance/` | Original RML and query-index build manifests |
| `contracts/repository/` | RML, execution-context, validation, version-lock, and query-index generation files |
| `manifest.json` | Portable relative paths, SHA-256 hashes, byte counts, graph IRIs, triple counts, generator hashes, repository commit, and load order |

The embedded historical build manifests may contain original absolute paths.
They are retained as provenance only. `manifest.json` uses package-relative
paths and is the portable restoration contract.

## Export and validation

Choose a new, nonexistent target directory:

```powershell
.\Baseball\scripts\pipeline\export-dehydration-package.ps1 `
  -GamePk 566279 `
  -PackageDirectory C:\BaseballO-exports\game-566279
```

The exporter refuses stale build contracts or hash mismatches, copies every
artifact, writes a closed file inventory, and runs
`validate-dehydration-package.py`. The validator rejects missing, additional,
modified, path-traversing, unparsable, wrong-game, wrong-graph, or inconsistent
files.

Validation can be repeated without changing Fuseki:

```powershell
.\Baseball\scripts\pipeline\restore-dehydration-package.ps1 `
  -PackageDirectory C:\BaseballO-exports\game-566279
```

## Rehydration

After validation, explicit `-Load` replaces the authoritative and query-index
named graphs with the exact packaged RDF:

```powershell
.\Baseball\scripts\pipeline\restore-dehydration-package.ps1 `
  -PackageDirectory C:\BaseballO-exports\game-566279 `
  -Load
```

The restorer removes the disposable index first, loads the authoritative graph,
then loads the matching index and verifies both counts and metadata. Therefore
a failed restore cannot leave an older index presented beside newly loaded
authoritative data. Loading does not enable acquisition and does not rewrite
the packaged or repository raw JSON.

The offline regression suite also includes:

- `test-dehydration-package.ps1`, which proves a one-byte source change is
  rejected without changing the original package; and
- `test-query-index-failure.ps1`, which injects malformed `CONSTRUCT` text,
  proves the authoritative graph survives and the stale index is absent, then
  rebuilds and revalidates the canonical index.

For rematerialization rather than exact RDF restoration, start from the
packaged raw JSON and use the recorded mapper/version plus the packaged RML and
execution-context contracts. Regenerate the authoritative graph before the
query index, then compare the new manifests and semantic equivalence results.
