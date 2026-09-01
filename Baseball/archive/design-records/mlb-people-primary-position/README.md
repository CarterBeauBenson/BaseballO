# MLB people baseball-position description

Status: **accepted 2026-08-30 — source-independent design**

This package follows the reviewed Football Ontology pattern: a position is a
Descriptive Information Content Entity about a Person and a cluster of Roles,
Dispositions, and Qualities borne by that Person. It is not itself a Role,
Disposition, intrinsic Person kind, or claim about every Game.

The package proposes `BaseballPositionDescription` and the supporting
`BaseballFieldingDisposition`. Existing Batter, Pitcher, Catcher, and Fielder
Roles remain career-persistent realizable entities. Accepted batting- and
throwing-side dispositions contribute to the cluster. Source-specific code
rules must enumerate the minimum cluster licensed by each position code.

The field is already in the MLB game payload. A later people-lane ownership
cutover must prove equivalence. No new object property is proposed and no
executable mapping is authorized here.
