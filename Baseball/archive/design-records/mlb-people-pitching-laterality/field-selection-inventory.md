# Field inventory and proposed term

| Field or entity | Disposition | Design consequence |
| --- | --- | --- |
| `pitchHand.code` | authoritative duplicate; admitted after ownership cutover | Classify one or two particular Throwing Side Dispositions. |
| `pitchHand.description` | code-list evidence | Validate the exact code/description pair; do not create prose-shaped classes. |
| Person `id` | identity/join-only | Reuse the canonical Person as bearer. |
| observed Throw Act | separate event grain | May establish a realization and test the persistent classification. |
| null or absent code | resolved absence | Emit no disposition or measurement. |
| unknown present code | invalid input | Quarantine before RML under the pinned code list. |

## Proposed class account

- **IRI:** `https://baseballontology.org/ThrowingSideDisposition`
- **Named parent:** Disposition (`obo:BFO_0000016`).
- **Aristotelian definition:** A Throwing Side Disposition is a Disposition that
  inheres in a Person and is realized in Throw Acts or Pitch Acts in which that
  Person preferentially throws a Baseball from a consistent bodily side.
- **Necessary axioms proposed for the later overlay:** inheres in some Person;
  has realization some union of Throw Act and Pitch Act.
- **Identity:** bearer plus side under the accepted source-neutral throwing-side
  classification. An ambidextrous player bears two particular dispositions.
- **Example:** the right-side throwing disposition borne by a shortstop.

No pitcher restriction and no new object property are proposed.
