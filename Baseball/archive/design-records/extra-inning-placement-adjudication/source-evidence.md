# Source evidence and selection inventory

The [2026 Official Baseball Rules](https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf),
7.01(b)(2), printed pages 92–93, require an extra-inning runner at second and
assign the plate umpire verification of the proper runner. Rule 5.09(e),
printed page 52, ends the offensive side after three legal outs. These support
the user's placement decision and the terminal-state tracker repair.

Checked-in source bytes remain unchanged:

- `data/raw/samples/2026-08-25/823585.json`: top 10, PA 74, event 1 explicitly
  places David Hamilton (666152) on second. Three strikeouts follow without
  any Hamilton movement row. The personal lifetime must not disappear.
- `data/raw/samples/2026-08-25/823826.json`: top 8, PA 61, event 5 records Wilyer
  Abreu's third-out force at third and Monasterio reaching first. Gasper has no
  movement row. His prior first-base observation is not a post-third-out claim.

| Field | Selection |
| --- | --- |
| gamePk; inning; half; player.id | Already authoritative; existing C3 identity/join only |
| runner_placed eventType; base=2 | Existing C3 placement evidence; additional adjudication coverage in owning MLB-game lane |
| counts; flags; event bounds; regular-season type | Already supplied; reconciliation and selection only |
| description | Supporting evidence; no new ICE subclass or text-derived predicate |
| runner movement rows; outNumber | Already supplied; preserve episode selection and exact out reconciliation |
| missing Gasper row | Unknown movement, not an inferred advance or final base |
| named adjudicator | Unresolved in action record; do not invent a Person or Role |

No new endpoint, source lane or source family is introduced.
