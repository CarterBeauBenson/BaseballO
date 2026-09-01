# Stale-material audit — 2026-08-31

## Scope

This pass reviewed active repository documentation, proposal diagrams and
evidence, MLB-game semantic status prose, source-module registration, retired
layout boundaries, and local Markdown links. Archived design records and
vendored ontology snapshots were treated as historical evidence and were not
rewritten to match current terminology.

## Corrected in this pass

- Replaced active proposal dependencies on CCO Spatial Reference System,
  Spatial Region, and Geospatial Region with the reviewed continuant-side
  geometry pattern or an explicit unresolved question.
- Recorded the repository-wide rule that BaseballO domain models do not use
  Spatial Region classes.
- Updated the MLB-game audit and top-level project documentation from thirteen
  historical findings to seven currently tracked blockers, distinguishing
  accepted designs awaiting implementation from unresolved semantics.
- Replaced the roadmap's superseded six release-metadata findings, which no
  longer describe the current ontology headers, with the three currently
  frozen structural findings for
  `GroundedIntoDoublePlayProcess`.
- Removed the obsolete claim that replay handling still synthesizes an
  opposite original decision.
- Updated the field-coordinate coverage gap to reflect the completed generic
  Reference System repair while preserving the unresolved provider contract
  and coordinate-literal gate.
- Replaced human-run aggregate-validation and production-materialization
  instructions with the NiFi-owned evidence and promotion lifecycle. Focused,
  non-promoting developer diagnostics remain documented as such.

## Structural checks

- Exactly one active proposal directory exists: `Baseball/proposals/`.
- Retired `generated/`, `source-schema/`, `mappings/direct/`, and nested
  proposal locations are absent.
- The source-module registry and the seven module directories with semantic
  status contracts agree: `mlb-game`, `mlb-teams`, `mlb-leagues`,
  `mlb-divisions`, `mlb-people`, `mlb-venues`, and `mlb-transactions`.
- The active Markdown link scan found no missing local targets.
- Active review text contains no affirmative use of Spatial Reference System,
  Spatial Region, or Geospatial Region. Remaining mentions state the rejected
  pattern or a negative constraint.

## Resolved protected-control defect

`validate_semantic_change_control.py --print-manifest` validates the current
five-module freeze and can now regenerate it. The builder preserves the exact
module admissions already pinned in the current freeze, refreshes only their
declared artifact hashes, and rejects catalog additions or removals until a
separate decision explicitly changes the admitted set. The repair was
authorized by the accepted 2026-08-31 MLB-game measurement, classification,
and lifecycle decision and is covered by focused multi-module regression tests.

## Evidence boundary

This was a focused documentation and contract-consistency review. The
aggregate repository validation remains NiFi-owned; this pass did not manually
reproduce that workflow or watch NiFi.
