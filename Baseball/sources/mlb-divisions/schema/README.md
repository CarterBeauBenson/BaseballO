# Selected MLB Divisions contract

The connector accepts a strict UTF-8 object with a non-empty `divisions`
array. Selected values are root `id/name`, optional `league.id/name`, and the
existing MLB `sport.id` guard. Other response fields remain unmapped.

The execution context is `divisions-context.json`. Invalid selected values are
quarantined before RML; successful raw and context bytes remain transient.
