# Scripts

[`validate_repository.py`](validate_repository.py) checks required paths, parses JSON and Turtle files, verifies local Markdown links and Mermaid fences, and runs the mapping-specific validator against the raw sample.

```powershell
python scripts/validate_repository.py
```

Mapping-specific validation also remains beside the active mapping in [`../mappings/direct/`](../mappings/direct/).
