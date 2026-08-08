# Scripts

[`validate_repository.py`](validate_repository.py) checks required paths,
parses JSON, Turtle, and all 96 SPARQL files, verifies local Markdown links and
Mermaid fences, validates the 288-game raw-corpus identity/date contract, runs
the mapping-specific validators against the fixture and accepted baseline,
checks challenge versus umpire-review context, executes web tests, and verifies the current query audit, index,
operational-routing, algebra, and TDB2 evidence artifacts.
It also meta-validates both SHACL profiles and proves with negative smoke graphs
that incomplete authoritative and index structures are rejected.
It also runs the selective-reasoning tests for slice isolation, positive and
negative entailments, computational budgets, deterministic output, and CLIF
translation.

```powershell
python scripts/validate_repository.py
```

Mapping-specific validation also remains beside the active mapping in [`../mappings/direct/`](../mappings/direct/).

[`generate_rml_mermaid.py`](generate_rml_mermaid.py) reads the active RML and the reviewed [pattern manifest](../mermaid/rml-mermaid-manifest.yaml), then generates two small-diagram catalogs: source-independent ontology patterns and MLB-direct mapping provenance. The manifest uses JSON syntax, which is valid YAML 1.2, so generation needs no YAML dependency.

```powershell
python scripts/generate_rml_mermaid.py
python scripts/generate_rml_mermaid.py --check
```

The check fails for unassigned triples maps, nonexistent manifest references, oversized review patterns, extra output files, or generated files that no longer match the RML and manifest. Repository validation runs this check automatically.

The [`pipeline/`](pipeline/) scripts import locally supplied game JSON,
preserve its bytes in a content-addressed archive, execute the pinned RMLMapper,
validate generated RDF procedurally and with SHACL, load complete per-game
named graphs, build and SHACL-check disposable query indexes, audit 48 canned
and 17 advanced queries, benchmark 18 reviewed
pairs, and enforce 15 indexed plus three authoritative routes. Infrastructure
scripts create the connected manual-inbox NiFi flow. Command-line external
acquisition requires an explicit approval switch; the unattended NiFi
acquisition flow remains stopped.

[`pipeline/submit-game-corpus-to-nifi.ps1`](pipeline/submit-game-corpus-to-nifi.ps1)
turns a checked-in date range into one deduplicated, monitored NiFi run. NiFi
owns staging, guarded RML execution, validation, indexing, loading, quarantine,
and provenance for every submitted game. Its companion
[`pipeline/monitor-nifi-corpus-submission.ps1`](pipeline/monitor-nifi-corpus-submission.ps1)
can reattach to a recorded run without enqueueing duplicate FlowFiles.

The [`reasoning/`](reasoning/) scripts fetch checksum-pinned BFO CLIF modules,
extract exactly one plate-appearance slice, apply one allowlisted reasoning
profile, emit deterministic inferred RDF and CLIF proof inputs, and optionally
prove the translated obligations before optionally loading the disposable named
graph. They expose no full-game mode.
