# Source and ontology evidence

## Ontologist decision

On 2026-08-28, Carter Beau Benson explicitly decided that a Baseball Game is a
temporally extended Process with Acts as parts, that a Baseball Season is a
Process, and that team membership needed for transaction modeling is expressed
through existing occupation roles with organizational context rather than a
new roster-membership role.

## Existing BaseballO evidence

The active overlay already gives `BaseballGame` occurrent parts from
`BaseballAct`, `BaseballPhysicalProcess`, and
`BaseballInstitutionalProcess`. Those restrictions are consistent with the
accepted Process classification. The active named taxonomy and natural-language
definition instead classify the Game as CCO Planned Act; that is the precise
legacy mismatch authorized for repair.

The accepted `PlayerRole` is an Occupation Role. Its existing overlay uses
`has organizational context` to connect the role to a Baseball Team. Existing
MLB-game mapping also creates a Stasis of Role involving the Person and the
team-scoped Player Role. These accepted structures already supply the intended
team-membership representation.

## Scope boundary

This decision authorizes the active `BaseballGame` taxonomy and definition
repair. It also dictates corrections to the draft Season and transaction
review packages, but does not accept those packages or authorize their
executable implementation. No new object property is required.
