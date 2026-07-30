# Tests

Repository-level static validation remains in [`../scripts/validate_repository.py`](../scripts/validate_repository.py). The active mapping provides its source and collision validator under [`../mappings/direct/`](../mappings/direct/).

With the local stack running, execute the offline end-to-end acceptance test from the repository root:

```powershell
.\scripts\pipeline\test-manual-vertical-slice.ps1 -ForceRdfLoad
```

The test uses only the checked-in fixture and loopback Fuseki. It checks source/archive byte identity, RML manifest hashes, source-to-RDF counts, and the expected named graph; it makes no external data request.
