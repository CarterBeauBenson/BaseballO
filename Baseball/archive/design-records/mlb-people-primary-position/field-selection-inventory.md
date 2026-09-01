# Field inventory and proposed terms

| Field or entity | Disposition | Design consequence |
| --- | --- | --- |
| `primaryPosition.code` | authoritative duplicate; admitted after ownership cutover | Classify a response-versioned Baseball Position Description under the pinned MLB position Reference System. |
| `primaryPosition.name`, `type`, `abbreviation` | code-list/display evidence | Validate the code tuple; do not mint parallel world entities from each string. |
| Person `id` | identity/join-only | The description is about the canonical Person. |
| accepted Role/Disposition/Quality cluster | real-world target | The description is also about every evidenced cluster member. |
| game position evidence | separate event grain | May provide realizations and regression evidence without rewriting the people assertion. |
| null or absent position | resolved absence | Emit no position description or cluster assertion. |

## Proposed class accounts

- **Baseball Position Description**
  - IRI: `https://baseballontology.org/BaseballPositionDescription`
  - Named parent: Descriptive Information Content Entity
    (`cco:ont00000853`).
  - Definition: A Descriptive Information Content Entity that describes a
    Person and describes one or more Roles, Dispositions, or Qualities that
    inhere in that Person and are characteristic of a baseball position.
  - Necessary axioms: describes some Person; describes some union of Role,
    Disposition, and Quality.
  - Identity: position concept, described Person, provider assertion content,
    and response version; it is not identified with any cluster member.

- **Baseball Fielding Disposition**
  - IRI: `https://baseballontology.org/BaseballFieldingDisposition`
  - Named parent: Disposition (`obo:BFO_0000016`).
  - Definition: A Disposition that inheres in a Person and is realized in
    Fielder Acts in which that Person acts to control a Baseball or produce an
    out from a baseball fielding position.
  - Necessary axioms: inheres in some Person; has realization some Fielder Act.
  - Identity: bearer plus the source-neutral fielding-position classification
    that differentiates the particular disposition.

No new object property is proposed. The later source-specific Mermaid must pin
the exact code-to-cluster table before RML.
