# Repository layout contract

BaseballO has two explicit roots:

- The Git root contains repository controls: `.git/`, `.github/`,
  `.editorconfig`, `.gitattributes`, `AGENTS.md`, and the public `README.md`.
- `Baseball/` is the project root. All application, ontology, pipeline,
  evidence, and technical documentation paths are relative to it.

GitHub Actions resolves paths from the Git root. Project scripts resolve their
own project root and may be launched from the Git root with a `Baseball/`
prefix. Subsystem documentation may use project-relative links but must state
that command examples begin in the `Baseball/` project directory when they omit
that prefix.

## Ownership map

| Path | Owns | Must not own |
| --- | --- | --- |
| `ontology/` | Authoritative TBox, reviewed axioms, pinned ontology dependencies, ontology authoring rules | Source schemas, RML, source proposals |
| `governance/` | Machine-readable semantic freeze/debt controls, review schemas, and repository-level semantic audit records | Authoritative ontology terms, executable mappings, active proposals |
| `proposals/` | The only active review catalog | Accepted designs, executable contracts |
| `sources/<id>/` | One detachable source's schema, RML, source-field IRI policy, SHACL, review manifest, and source contract | Another source's fields or validation |
| `mappings/policies/` | Source-neutral realist modeling policy | Source fields, processor constraints, executable RML |
| `sparql/` | Single-source, multi-source, and derived integration/query contracts | Ingestion transformations |
| `shacl/` | Source-neutral derived-layer shapes | Source-authoritative shapes |
| `serving/` | Rebuildable analytical SQL contract | Authoritative facts |
| `web/` | Explorer application and allowlisted query builders | Ontology or ingestion semantics |
| `infra/` | Versioned NiFi/Fuseki configuration and operational contracts | Pipeline implementation code |
| `scripts/` | Executable bootstrap, pipeline, reasoning, and validation code | Mutable runtime state |
| `data/` | Checked-in immutable evidence fixtures only | Future API accumulation or generated RDF |
| [`benchmarks/`](benchmarks/) | Versioned immutable performance and equivalence captures | Runtime databases or relabeled historical measurements |
| `reasoning/` | Bounded profiles and proof evidence | Authoritative inferred replacement graphs |
| `mermaid/` | Shared diagrams and generated cross-model review catalogs | Proposal-only designs |
| `archive/` | Historical, accepted, rejected, or superseded records | Active executable dependencies |

## Rules against layout drift

- Do not add a new project-root directory when an owner already exists.
- Do not use `generated/`, `source-schema/`, `mappings/direct/`, or nested
  proposal directories; those are retired layouts.
- Do not put repository-wide controls under `Baseball/`; nested controls leave
  Git-root documentation and CI files outside the same formatting contract.
- Do not use provider-wide modules. `mlb-game`, MLB reference APIs, Statcast,
  weather, and derived travel/rest evidence remain separate.
- Generated artifacts must identify their generator and are changed through
  that generator.
- Runtime state stays under the configured local state root, not in Git or
  OneDrive.
- Any intentional layout change updates this contract and repository
  validation in the same commit.
