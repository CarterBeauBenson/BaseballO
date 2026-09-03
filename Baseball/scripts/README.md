# Scripts

Run project-relative commands in this document from the `Baseball/` project
directory.

[`validate_repository.py`](validate_repository.py) checks required paths,
parses JSON, Turtle, and every registered SPARQL file, verifies local Markdown links and
Mermaid fences, validates 546 distinct completed-game identities including the
separately scoped 2026 All-Star Game identity/date contract, runs
the mapping-specific validators against the fixture and accepted baseline,
checks challenge versus umpire-review context, executes web tests, and verifies the current query audit, index,
operational-routing, algebra, and TDB2 evidence artifacts.
It also meta-validates all three SHACL profiles and proves with negative smoke
graphs that incomplete authoritative, index, and reasoning-output structures
are rejected.
It also runs the selective-reasoning tests for slice isolation, positive and
negative entailments, computational budgets, deterministic output, and CLIF
translation.

Before those integration checks, the repository validator now runs two
fail-closed curation controls:

- [`validate_ontology_curation.py`](validate_ontology_curation.py) enforces the
  local class-authoring contract and requires every current exception to match
  the explicitly unaccepted debt manifest exactly; and
- [`validate_semantic_change_control.py`](validate_semantic_change_control.py)
  pins the frozen ontology, RML, source SHACL, semantic context, review, and
  reasoning surface and rejects active-proposal IRI leakage.

The frozen hashes are reproducibility controls, not semantic acceptance.
Changing either a protected artifact or a debt entry requires a prior archived
ontologist decision; an agent must never refresh those files merely to make a
check pass.

[`infra/launch-explorer.ps1`](infra/launch-explorer.ps1) is the idempotent local
entry point for Fuseki, the always-on NiFi service, the Explorer server, and the
default browser. [`infra/install-explorer-shortcut.ps1`](infra/install-explorer-shortcut.ps1)
installs that entry point as **BaseballO Explorer** on the current Windows
Desktop. The Explorer publishes a startup fingerprint for its server and query
builder sources. The launcher reuses a matching process and restarts only the
Explorer Node process when repository code has changed; it does not restart or
monitor a healthy NiFi instance to refresh the UI.

```powershell
python scripts/validate_repository.py
```

The checked-in pre-push hook runs the focused semantic gate before publishing.
Enable it once in a clone with `git config core.hooksPath .githooks` from the
Git root. CI repeats the history-aware comparison with full Git history.

Mapping-specific validation remains beside the active mapping in [`../sources/mlb-game/mapping/`](../sources/mlb-game/mapping/).

[`generate_rml_mermaid.py`](generate_rml_mermaid.py) reads the active RML and the MLB game module's reviewed [pattern manifest](../sources/mlb-game/review/rml-mermaid-manifest.json), then generates two small-diagram catalogs: source-independent ontology patterns and MLB game mapping provenance. The manifest uses JSON directly, so generation needs no YAML dependency.

```powershell
python scripts/generate_rml_mermaid.py
python scripts/generate_rml_mermaid.py --check
```

The check fails for unassigned triples maps, nonexistent manifest references, oversized review patterns, extra output files, or generated files that no longer match the RML and manifest. Repository validation runs this check automatically.

The [`pipeline/`](pipeline/) scripts are versioned components invoked by the
source-owned NiFi lanes. They run RML, validate generated RDF with source
SHACL, promote complete named graphs, build the Game query index, materialize
approved SQL grains, audit 51 canned and 17 advanced queries, benchmark 19
reviewed pairs, and enforce 16 indexed plus three authoritative routes. The
direct game importer is a developer fallback; there is no active NiFi manual
inbox. External API responses are staged transiently and removed after the
owning promotion and cleanup gates.

`pipeline/verify-explorer-serving.py` is the fail-closed black-box suite used
when admitting Explorer families to SQL. It probes every routine family and
sends `X-BaseballO-Require-Materialized: true`, so the current contract is
expected to reject families that have not yet passed equivalence. A future
full-family acceptance run must retain one consistent SQL build ID, corpus
fingerprint, coverage tuple, row count, and duration per probe.

`pipeline/prove-serving-equivalence.py` closes the pre-admission gap. NiFi
uses its isolated `query-serving-candidate.py` adapter to compare pending SQL
with a forced authoritative Explorer response before any route status is
changed. The comparison requires exact RDF terms, rows, ordering, corpus
fingerprint, and one immutable SQL build. It records evidence but cannot admit
a route.

`pipeline/record-repository-validation.py` is the NiFi-owned wrapper around the
aggregate repository gate. It writes immutable JSON plus separately hashed
stdout and stderr logs. The `Repository Evidence` process group schedules it;
Codex does not reproduce that recurring workflow manually.

The clean NiFi runtime is provisioned per source module. Seven detachable
process groups own Games, Teams, Leagues, Divisions, People, Venues, and
Transactions. Each has independent acquisition, RML, source SHACL,
authoritative promotion, cleanup, retry, quarantine, and provenance. The Game
lane additionally owns atomic authoritative/index graph-pair promotion and
batch-aware SQL materialization. The shared source-stage dispatcher is
[`pipeline/process-source-stage.ps1`](pipeline/process-source-stage.ps1);
NiFi owns its scheduling and dependency order.

The aggregate repository-validation stage is a separate asynchronous observer.
It does not control, pause, or promote any source lane, authoritative graph, or
serving pointer. Do not invoke retired configurators or reconstruct the deleted
control plane around it.

[`infra/migrate-rdf-storage.ps1`](infra/migrate-rdf-storage.ps1) performs the
one-time, stopped-store migration of Fuseki/TDB2 state to a guarded external
volume. It verifies source and target SHA-256 inventories before switching the
machine-local storage pointer and never moves transient API payloads or the SQL
serving database with the authoritative RDF.

The [`reasoning/`](reasoning/) scripts fetch checksum-pinned BFO CLIF modules,
extract exactly one plate-appearance slice, apply one allowlisted reasoning
profile, emit deterministic inferred RDF and CLIF proof inputs, and optionally
prove the translated obligations before optionally loading the disposable named
graph. They expose no full-game mode.
`reasoning/evaluate-reviewed-samples.py` runs all three profiles over the
reviewed simple/complicated real-game pair and records explicit-versus-closure
query hashes without loading any inferred graph.
