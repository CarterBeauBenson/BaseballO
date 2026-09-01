# Field inventory and proposed term

| Field or entity | Disposition | Design consequence |
| --- | --- | --- |
| `batSide.code` | authoritative duplicate; admitted after ownership cutover | Classify one or two particular Batting Side Dispositions under the pinned Reference System. |
| `batSide.description` | code-list evidence | Validate the exact code/description pair; do not turn the prose into a class. |
| Person `id` | identity/join-only | Reuse the canonical Person as bearer. |
| Plate Appearance matchup side | separate event grain | May identify which disposition a particular Batter Act realizes. |
| null or absent side | resolved absence | Emit no disposition or measurement. |
| unknown present code | invalid input | Fail before RML under the pinned code list. |

## Proposed class account

- **IRI:** `https://baseballontology.org/BattingSideDisposition`
- **Named parent:** Disposition (`obo:BFO_0000016`).
- **Aristotelian definition:** A Batting Side Disposition is a Disposition that
  inheres in a Person and is realized in Batter Acts in which that Person bats
  from a consistently preferred side of Home Plate.
- **Necessary axioms proposed for the later overlay:** inheres in some Person;
  has realization some Batter Act.
- **Identity:** bearer plus side under the accepted source-neutral batting-side
  classification. Left and right are distinct particular dispositions. A
  switch hitter bears both.
- **Example:** the right-side batting disposition borne by a switch hitter.

The Nominal Measurement ICE supplies the evidenced left/right classification;
it does not replace the world-side disposition. No object property is proposed.
