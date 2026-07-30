# Scripts

[`validate_repository.py`](validate_repository.py) checks required paths, parses JSON and Turtle files, verifies local Markdown links and Mermaid fences, and runs the mapping-specific validator against the raw sample.

```powershell
python scripts/validate_repository.py
```

Mapping-specific validation also remains beside the active mapping in [`../mappings/direct/`](../mappings/direct/).

The [`pipeline/`](pipeline/) scripts execute the pinned RMLMapper, validate generated RDF, and load a complete per-game named graph into Fuseki. Infrastructure scripts also create an idempotent, deliberately stopped NiFi processor skeleton for that tested boundary.
