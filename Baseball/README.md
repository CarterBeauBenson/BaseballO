# BaseballO Knowledge Graph

BaseballO transforms untouched completed-game JSON into ontology-aligned RDF. The active implementation accepts a file supplied through a local manual inbox and maps the raw JSON directly with RML; it does not flatten, normalize, enrich, or store derived statistics.

## Active pipeline

```mermaid
flowchart LR
    SOURCE[Manually supplied game JSON] --> INBOX[Local NiFi inbox]
    INBOX --> RAW[Immutable raw game JSON]
    RAW --> RML[Direct RML mapping]
    RML --> RDF[Validated Turtle RDF]
    RDF --> FUSEKI[Apache Jena Fuseki / TDB2]
    FUSEKI --> SPARQL[Canned full-pattern SPARQL]
    FUSEKI --> CONSTRUCT[Reviewed CONSTRUCT components]
    CONSTRUCT --> INDEX[Disposable per-game query index]
    INDEX --> FAST[Future accelerated queries]
    SPARQL --> WEB[Local BaseballO Explorer]
    FAST --> WEB
```

The first proof-of-concept query is **Empty Games**: games in which a player participated offensively without a qualifying offensive contribution. That result must be derived with SPARQL, never stored during ingestion.

## Repository map

| Path | Purpose | Status |
| --- | --- | --- |
| [`ontology/`](ontology/) | BaseballO taxonomic backbone, optional axiom overlay, and dependency snapshots | Active |
| [`mappings/direct/`](mappings/direct/) | Direct raw-JSON-to-RDF RML and validator | Active |
| [`mappings/policies/`](mappings/policies/) | Approved modeling and IRI policies | Active |
| [`source-schema/`](source-schema/) | Observed schema and JSONPath inventory for the sample feed | Active reference |
| [`mermaid/`](mermaid/) | Visual review of the RML source, map, join, and identity shapes | Active review |
| [`data/`](data/) | Raw development inputs | Development only |
| [`archive/`](archive/) | Superseded preprocessing prototype and prior ontology snapshot | Historical |
| [`sparql/`](sparql/) | Canned and advanced semantic queries plus reviewable components for the disposable query-index graph | Active query library and acceleration contract |
| [`web/`](web/) | Playable local analytics explorer and allowlisted query compiler | Local MVP active |
| [`scripts/`](scripts/) | Acquisition, RML execution, validation, and infrastructure automation | Active |
| [`tests/`](tests/) | Offline integration and future regression tests | Active |
| [`infra/`](infra/) | Pinned local NiFi and Fuseki development stack | Active |

## Validate the active mapping

Install the validation dependency and check the entire repository:

```powershell
python -m pip install -r requirements-dev.txt
python scripts/validate_repository.py
```

The same command runs automatically through [GitHub Actions](.github/workflows/validate.yml) on pushes and pull requests.

To run only the mapping-specific validation, use the following command.

From `mappings/direct`:

```powershell
python validate_direct_mapping.py ../../data/raw/game-566279.json
```

The validator checks the mapping's Turtle structure, locally declared BaseballO classes, the completed-game precondition, source identifiers, observed result coverage, and sample-specific IRI collision risks. It is a static check; successful execution by an RML processor is still required.

## Modeling guardrails

- Treat the MLB JSON as authoritative and leave it unchanged.
- Model people, roles, acts, processes, temporal regions, sites, and information content entities—not stored statistics.
- Reuse canonical `allPlays`; do not remap duplicate API views as new events.
- Build deterministic IRIs from source identifiers.
- Use temporal precedence unless genuine causation is supported.
- Record ontology gaps explicitly. Do not add classes, properties, or shortcuts
  to the ontology without approval; operational query-index terms must remain
  isolated from the authoritative graph.

## RML visual review

Start with the [Mermaid review index](mermaid/README.md). It separates the intended pipeline from the implemented RML shape and highlights places requiring processor tests or modeling decisions.

## Execute the local vertical slice

After bootstrapping and starting the free local stack, follow the [manual game import runbook](scripts/pipeline/README.md). It archives untouched completed-game JSON, executes the pinned RMLMapper, validates source-to-RDF record counts, and loads complete named graphs into Fuseki with idempotent `PUT` requests.

Automated external acquisition is parked pending an approved data-access source. The active NiFi flow makes no MLB or other external HTTP request.

## Next phase

Use [`NEXT-PHASE.md`](NEXT-PHASE.md) as the single current continuation plan.
It begins with owner review of the now-exposed advanced semantic analytics,
followed by evidence-driven index coverage; completed historical work is listed
there only to prevent accidental repetition.
