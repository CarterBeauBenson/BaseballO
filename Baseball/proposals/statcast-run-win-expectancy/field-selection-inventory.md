# Field selection inventory

| Field or evidence | Accepted classification | Draft treatment |
| --- | --- | --- |
| `delta_run_exp` | genuinely additional | Retain for review; block until before/after semantics, actual-runs treatment, target, and model version are accepted. |
| `home_win_exp` | genuinely additional | Retain for review; block until state boundary and possible home-win Process target are accepted. |
| `delta_home_win_exp` | deterministically derivable | Exclude from Statcast mapping; derive only after approved before/after home-win semantics. |
| `bat_win_exp` | deterministically derivable | Exclude; derive from home-team expectancy plus batting side. |
| inning, outs, base occupancy, scores, batting side | already supplied or derivable from MLB-game | Exclude; use only after promotion for explanation/equivalence. |
| actual Run Processes and game result | already supplied/derived by MLB-game | Exclude; do not substitute them for possible model targets. |
| model version/training population/state definition | genuinely required provenance; incomplete | Block timeless Algorithm identity. |
| game/pitch/PA identifiers | already supplied or join-only | Resolve canonical world entities without duplicating structure. |
| null/unavailable value | missingness | Emit no estimate and preserve reason/method-era evidence when supplied. |

No new ontology IRI is proposed. Each retained output ICE would be keyed by
canonical event/state scope, output kind, model version, and source response
hash; the actual game entities retain MLB ownership and identity.
