# Assertion-selection inventory

| Candidate assertion | Status | Modeling consequence |
| --- | --- | --- |
| Plate Appearance Process | accepted source assertion | Reuse `PlateAppearance`; retain one game-scoped IRI per `atBatIndex`. |
| Plate Appearance has batter participant | accepted source assertion | Link the Process to the batter Person with `has participant`. |
| Career-persistent Batter Role | accepted identity policy | Reuse one `BatterRole` IRI per Person across games and Plate Appearances. |
| Batter Role inheres in Person | accepted world-side assertion | Assert `inheres in` from the persistent Role to its bearer. |
| Plate Appearance realizes Batter Role | rejected redundant assertion | The Plate Appearance contains the Batter Act; the Batter Act supplies the realization edge. |
| Swing or Bunt realizes Batter Role | accepted when event detail supports the Act | Retain the actual Act, its participant, Plate Appearance context, and realization edge. |
| Generic Batter Act for every Plate Appearance | accepted common realization grain | Retain one game-scoped Batter Act per Plate Appearance; it has the batter as participant, realizes the persistent Batter Role, and supports counting across all outcomes. |
| Batter Role Stasis | accepted persistence pattern | It may have the Role and bearer as participants and occupy an interval, but it must not realize the Role. |
| Plate-appearance-specific Batter Role | rejected duplicate identity | Do not mint it; the Role inheres in the Person across the career. |
| Official statistical at-bat from `atBatIndex` | unresolved/derivable only with rules | Do not infer it merely from the source index name. |

This is a correction within the existing MLB-game source lane. It does not add
a source, create provider-specific classes, or change the authoritative
integration boundary.
