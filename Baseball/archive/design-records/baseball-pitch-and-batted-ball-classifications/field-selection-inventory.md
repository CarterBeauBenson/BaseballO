# Field-selection inventory

| Provider content | Disposition | World-side target |
| --- | --- | --- |
| `FF`, `SI`, `FC`, `SL`, `ST`, `SV`, `CU`, `KC`, `CS`, `CH`, `FS`, `FO`, `SC`, `KN`, `EP` | classification evidence | persistent reusable Nominal Measurement ICE; explicit current Pitch Act subtype only in the rebuildable current-state graph |
| `FA`, `Other`, `Unknown`, obsolete/empty code | unresolved provider information | no world-side subtype |
| intentional-ball and pitchout tokens | separate modeling question | objective/tactical Pitch Act subtype, not pitch-type taxonomy |
| `ground_ball`, `line_drive`, `fly_ball`, `popup` | classification evidence | persistent reusable Nominal Measurement ICE; explicit current Batted-Ball Motion Process subtype only in the rebuildable current-state graph |
| velocity, spin, break, grip, hold, and trajectory measurements | already owned or deferred measurements | separate Process Profiles, geometry, and evidence; never class-defining literals |

All listed new universals are source-independent BaseballO classes. A
versioned provider Reference System supplies evidence for selecting the
current explicit class assertion, but its historical classifications do not
drive OWL inference. Provider codes and Reference Systems are individuals, not
one class per field.
