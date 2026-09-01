# MLB people batting-side disposition

Status: **accepted 2026-08-30 — source-independent design**

This package models the real batting-side disposition reported by MLB. The
Person bears the disposition; Batter Acts realize it. The provider code is a
Nominal Measurement ICE about that disposition, not the disposition itself
and not a claim that every Plate Appearance used the reported side.

The source-independent proposal adds one class, `BattingSideDisposition`.
Left- and right-side capabilities are particular dispositions classified
under the accepted batting-side Reference System. A switch hitter bears both
particular dispositions; `S` is not a third anatomical or spatial side.

The field already occurs in the MLB game payload. A later people-lane mapping
must replace duplicate ownership only after equivalence is proven. No new
object property is proposed, and this review authorizes no executable mapping.
