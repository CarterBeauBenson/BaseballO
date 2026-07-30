# Scripts

[`validate_repository.py`](validate_repository.py) checks required paths, parses JSON and Turtle files, verifies local Markdown links and Mermaid fences, and runs the mapping-specific validator against the raw sample.

```powershell
python scripts/validate_repository.py
```

Mapping-specific validation also remains beside the active mapping in [`../mappings/direct/`](../mappings/direct/).

The [`pipeline/`](pipeline/) scripts import locally supplied game JSON, preserve its bytes in a content-addressed archive, execute the pinned RMLMapper, validate generated RDF, and load complete per-game named graphs into Fuseki. Infrastructure scripts create the connected manual-inbox NiFi flow. The earlier external-acquisition flow remains stopped pending an approved data source.
