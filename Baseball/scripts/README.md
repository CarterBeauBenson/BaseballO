# Scripts

Run project-relative commands in this document from the `Baseball/` project
directory.

These are components for NiFi and focused developer diagnosis, not a manual
release checklist. Follow the [minimal-check policy](../../AGENTS.md#incremental-work-and-minimal-manual-validation).
For documentation, review the diff and run `git diff --check`. For changed code,
run the smallest useful check and leave routine integration, validation, retry, and publication
to NiFi. Read existing failure evidence before running anything again.

[`validate_repository.py`](validate_repository.py) is the aggregate gate run by
NiFi's Repository Evidence observer. Its executable registry and the
[test guide](../tests/README.md) own the component inventory; this directory
index does not duplicate that changing list.

The repository validator includes two
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

`validate_repository.py` is invoked by NiFi's `Repository Evidence` observer;
do not run it by hand as a prerequisite for every edit. The installed pre-push
hook performs its existing semantic-change check during publishing; do not
duplicate that invocation manually. Git publishing to `dev` is authorized.
The user removed GitHub validation on September 17; do not restore it.

Mapping-specific validation remains beside the active mapping in [`../sources/mlb-game/mapping/`](../sources/mlb-game/mapping/).

[`generate_rml_mermaid.py`](generate_rml_mermaid.py) reads the active RML and the MLB game module's reviewed [pattern manifest](../sources/mlb-game/review/rml-mermaid-manifest.json), then generates two small-diagram catalogs: source-independent ontology patterns and MLB game mapping provenance. The manifest uses JSON directly, so generation needs no YAML dependency.

```powershell
python scripts/generate_rml_mermaid.py
python scripts/generate_rml_mermaid.py --check
```

The check fails for unassigned triples maps, nonexistent manifest references, oversized review patterns, extra output files, or generated files that no longer match the RML and manifest. Repository validation runs this check automatically. Use generation only when its owning RML or pattern manifest changes, not for SQL or presentation edits.

The [pipeline component guide](pipeline/README.md) covers RML execution,
source SHACL, graph loading, query indexes, SQL materialization, query routing
and equivalence. Source-specific stages and targeted repairs remain in their
own [source modules](../sources/README.md). The
[NiFi runbook](../infra/nifi/README.md) owns provisioning and submission; the
[serving guide](../serving/README.md) owns SQL publication and route admission.

`pipeline/record-repository-validation.py` is the NiFi-owned wrapper around the
aggregate repository gate. It writes immutable JSON plus separately hashed
stdout and stderr logs. The `Repository Evidence` process group schedules it;
Codex does not reproduce that recurring workflow manually.
It records `deferred` while the Git working tree has uncommitted changes. If
the commit or working tree changes during validation, it preserves the logs
and actual validator exit code but does not certify a pass or failure for that
commit. The existing scheduled/manual trigger retries after publication.
Stable committed failures still fail; a deferral never admits source data.

The aggregate observer does not control, pause or promote source lanes,
authoritative graphs or serving pointers. Do not reconstruct the retired global
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
