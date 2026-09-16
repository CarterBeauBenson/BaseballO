# Source evidence and field selection

Read from unchanged checked-in fixtures on September 16, 2026. All paths are
under `data/raw/samples/2026-08-25/`; PA/event indexes below locate evidence
and are not proposed identity components.

| Fixture | Source SHA-256 | Concrete observation |
| --- | --- | --- |
| `824233.json`, PA 8/event 3 | `aeb5a4c4f0ba59bf73af79427d943137bb573412d9d5ca655f0d107694667abc` | Chandler Simpson (802415), caught stealing second, movement starts first, first out. No `playId`; `actionPlayId=d9c8510c-a2da-3bc8-b8a2-799b8271921e`. Action outs=1; a later batter strikeout is out 2. |
| `823259.json`, PA 64/event 0 | `b5b826832364a092e279a223c29f41dee4d52e65e72002b7c80c3280ca7a0be1` | Explicit PR Jase Bowen (687749) for Ty France (664034), base 1, bottom ninth. Neither stable ID field exists. Bowen later has a supported first-to-second steal episode. |
| `823585.json`, PA 74/event 1 | `9bc6c0423abeea6adee187b4299ce70573aff6b8e71e158c7a42118d84139699` | Explicit David Hamilton (666152) placement at second, top tenth, no pitch ID. The post-PA report also names Hamilton at second. |
| `823826.json`, PA 61 | `1c2f05b2a5dc3a806a348ff45bed3e1b2d8d1e32c70d7f52509bec6c15d9237e` | Third-out force at third and batter safe at first, with no movement for the previously first-base runner. This separate state gap is not repaired by C3 identity tokens. |

The substitution/placement observation bounds begin before the PA header in
these fixtures. C3 does not turn those bounds into exact physical instants or
claim that complete PA-start projections follow from admitting C1 histories.

MLB distinguishes pinch-running substitutions; removed players cannot return.
[MLB substitutions](https://www.mlb.com/glossary/rules/substitutions).
Regular-season extra innings begin with a runner at second, possibly a pinch
runner. [MLB automatic runner](https://www.mlb.com/glossary/rules/designated-runner).
These rules corroborate lifecycle distinctions. The anchor serialization is
our proposed identity policy, not a rule supplied by MLB.

## Field-level selection inventory

| Field | Classification | Bounded use |
| --- | --- | --- |
| `gamePk`, inning, half, Person IDs | Identity/join-only | Existing game, half and persistent Persons |
| `playId` | Already supplied / identity join | Preserve existing admitted pitch anchors |
| `actionPlayId` | Already supplied; owning-lane mapping-coverage debt | Association component of a unique action token; never alias blindly to `playId` |
| `eventType`, PR position, `isSubstitution` | Already supplied | Reconcile exact supported boundary kind, not ontology classes per source code |
| `player.id`, `replacedPlayer.id` | Already supplied / identity join | Incoming/outgoing Persons; no transfer of their prior episodes |
| administrative `base` | Already supplied | Cross-check entry/replacement state; no new physical location assertion |
| runner `start`, `end`, `isOut`, `outNumber`, scoring flag | Already supplied | Existing episode/outcome evidence and distinct-out reconciliation |
| action and PA counts | Already supplied | Reconcile field-specific pre/post scope; do not infer an extra out from labels |
| event bounds and complete intervening inventory | Already supplied | Detect uncertainty and contradictory boundary order |
| composite token / history hash | Deterministically derivable after C3 acceptance | Serialize the accepted particular, retaining source witnesses |
| zero-episode lifetime and ambiguous corrections | Unresolved | Withhold; no replacement graph term or synthetic episode |

No additional endpoint, provider, duplicated measurement or new source lane
is proposed. Raw source bytes remain unchanged.
