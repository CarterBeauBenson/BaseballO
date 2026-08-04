# Scripts

[`validate_repository.py`](validate_repository.py) checks required paths,
parses JSON, Turtle, and all 95 SPARQL files, verifies local Markdown links and
Mermaid fences, runs the mapping-specific validators against all checked-in
games, executes web tests, and verifies the current query audit, index,
operational-routing, algebra, and TDB2 evidence artifacts.

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
validate generated RDF, load complete per-game named graphs, build disposable
query indexes, audit 48 canned and 16 advanced queries, benchmark 18 reviewed
pairs, and enforce 15 indexed plus three authoritative routes. Infrastructure
scripts create the connected manual-inbox NiFi flow. The earlier
external-acquisition flow remains stopped pending an approved data source.
