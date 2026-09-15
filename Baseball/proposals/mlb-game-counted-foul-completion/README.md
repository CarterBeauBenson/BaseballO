# M3/M4: complete the next counted-foul cases

Status: draft for ontologist review. No implementation or acceptance is
recorded here. No new class, object property, data property, formula, source
module, or pipeline topology is proposed.

The current real-game pitch audit found four missing counted Strike Processes
in game 824087: ordinary second-strike fouls after a steal, an initial pitching
change, and a completed pitch review; and a first-strike foul bunt. This is
present source evidence with bounded mapping coverage, not absent provider data.

**M3** extends the existing counted-foul prefix gate across three positively
accounted-for cases described in [the contract](mapping-contract.md). **M4**
maps an explicitly counted foul bunt through the existing full
Strike Process / Strike Judgment Act / Strike Decision ICE pattern.

The earlier [M1 contract](../../archive/design-records/mlb-game-metric-mapping-completion/mapping-contract.md)
explicitly kept foul bunts outside its scope and blocked substitutions and
unresolved reviews in the prefix. These extensions therefore need a named
decision before the source selection, RML or source SHACL changes. The
repository guardrail prohibits silently expanding a frozen semantic surface
or weakening its validator. Existing implementations and NiFi remain active.

Review the [source evidence](source-evidence.md), [field inventory](field-selection-inventory.md),
[world-side shape](source-independent-mermaid.md), and
[source-specific projection](source-specific-mermaid.md). Approval would cover
M3/M4 only, including their source-owned context/RML/SHACL and scoped proof-pin
consequences. It would not accept new vocabulary or globally ratify the freeze.

Recovery Quality still needs full ordered-event and reference-population
admission after these four cases. This package does not promise that four
additional strikes complete every metric or populate the dashboard by themselves.
