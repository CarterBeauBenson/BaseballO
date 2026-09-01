# Selected MLB Leagues contract

The connector accepts a strict UTF-8 object with a non-empty `leagues` array.
Selected values are root `id/name`, optional nested `divisions[].id/name`, MLB
`sport.id`, `season`, `seasonDateInfo.seasonId`, and valid non-null one-level
`seasonDateInfo.*Date` values. Conflicting season values or malformed selected
dates quarantine the response.

The execution context is `leagues-context.json`. It is transient; the source
payload and every executable mapping and validation artifact remain owned by
this connector.
