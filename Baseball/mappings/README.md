# Shared mapping policies

Executable RML is source-owned. The active MLB game mapping is in
[`../sources/mlb-game/mapping/`](../sources/mlb-game/mapping/). Future source
families receive sibling modules under `sources/`; they do not add files to a
shared direct-mapping directory.

[`policies/`](policies/) contains only source-neutral realist modeling patterns
that source modules may reuse. Source-field IRI templates and processor
constraints belong to the module that owns those fields.

The former enriched Stage 1 prototype is retained under [`../archive/stage1-preprocessing-prototype/`](../archive/stage1-preprocessing-prototype/) for history only. It is not part of the active pipeline.

Source-specific counts, behavior, and semantic audit findings are documented by
the owning module under [`../sources/mlb-game/`](../sources/mlb-game/).

## Extension gate

RML is the final binding of source evidence to an accepted semantic pattern;
it is not a mechanical JSON/CSV serializer. A new source family must first have
an explicit de-duplication inventory and approved source-independent Mermaid
shapes. No executable map may reference proposal vocabulary or invent a
field-specific ICE to stand in for an unmodeled quality, relation, geometry, or
process profile. After approval, source-specific Mermaid must identify the
logical source, field conditions, IRI scope, null behavior, emitted entities,
and every intentionally withheld claim.
