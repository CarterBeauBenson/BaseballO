# Field selection and de-duplication inventory

| MLB schedule evidence | Disposition | Proposed use |
| --- | --- | --- |
| `gamePk` | identity/join-only | Identifies the same Baseball Game across schedule revisions; never mints one Game per row. |
| schedule container `date` | genuinely additional revision evidence | Supplies a Calendar Date Identifier associated with the plan represented by that schedule occurrence. |
| `gameDate` | genuinely additional revision evidence | Supplies a timestamp identifier for the planned interval represented by that schedule occurrence. |
| `officialDate` | duplicate of the owning `feed/live` Game evidence | Do not use schedule data to assert a second actual Game date; use it only as consistency evidence. |
| `status.abstractGameState` | operationally useful but insufficient | Never use abstract `Final` alone to select the completed occurrence. |
| `status.detailedState` = `Postponed` | genuinely additional institutional evidence | Supports a Postponement Act only with same-`gamePk` revision evidence. |
| `rescheduleDate` / `rescheduledFrom` | genuinely additional revision evidence | Connect the input and output schedule plans and their planned intervals. |
| `status.reason` = `Inclement Weather` | genuinely additional nominal classification | Generic Nominal Measurement ICE about the Postponement Act under an MLB postponement-reason Reference System. |
| teams, venue, season, game type | authoritative duplicates | Do not remap merely because the schedule repeats them. |
| schedule description text | provenance/evidence only | May remain on a source record; it does not license new world-side entities by parsing prose. |

The schedule payload remains transient. Accepted RDF extracted from these fields
would be persistent MLB-game source evidence.
