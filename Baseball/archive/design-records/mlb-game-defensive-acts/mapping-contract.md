# D1 source and identity contract

## Existing semantic pattern

Use only accepted `FieldingAttemptAct`, `CatchAttemptAct`, `ThrowAct`,
`TagAttemptAct`, `FielderRole`, `BattedBallPlayProcess`, Person and
`BaseballEventRecord`. Each admitted act has its actual Person agent via
`cco:ont00001833`, realizes (`obo:BFO_0000055`) that person's persistent
Fielder Role, and is an occurrent part (`obo:BFO_0000132`) of the existing
batted-ball play. The role inheres in that Person (`obo:BFO_0000197`).
The source record is about the supported acts (`cco:ont00001808`).
Use `obo:BFO_0000063` only for separately supported temporal precedence.
No invented recipient, throw-target, runner-position or sequence property.

## Proposed identity serialization (requires D1 acceptance)

An act is one supported uninterrupted performance by a specific defender,
within one contact play. Repeated performances by the same person remain
distinct; superclass typing does not create another performance.

Proposed IRI: `data/game/{gamePk}/act/defense/{playId}/{performanceIndex}`.
The namespace prefix is `https://baseballontology.org/`. `playId` must be the
existing stable ID of the unique associated contact event. `performanceIndex`
is the one-based canonical performance position in the reconciled description,
not an assist-array position, timestamp, observation hash or ontology class.
It serializes identity and does not assert temporal precedence.

Missing/nonunique play IDs, ambiguous performance segmentation and source
corrections that make performance alignment ambiguous are withheld. On an
unambiguously aligned correction, retain each performance's identity; do not
renumber existing performances to manufacture continuity. Corrections requiring
an identity policy beyond this bound return to review. Do not create an
event-specific Role; reuse `data/player/{playerId}/role/fielder`.

## Evidence selection

Require a unique contact event, complete final result description, matching
runner event association, uniquely resolved named defenders and consistent
structured credits/outcomes. Names join only to the owning payload's known
Persons. Position labels and array order do not substitute for identity.

- A simple named fly/line/pop out with its same-person putout and no contrary
  narrative supports that person's Catch Attempt. A successful catch is also
  a Fielding Attempt of the same identity. Do not manufacture a throw or tag.
- A description explicitly identifying a ground-ball fielding/throw/receipt
  supports those particular performances when the identified agents and
  structured result agree. A generic `A to B` credit chain without a resolved
  throw reading remains insufficient: it can represent a deflection.
- A described relay preserves repeated participants and separately supported
  throw/receipt performances. A duplicate outfield-assist credit is not another
  throw. Do not insert a catch before every assist credit automatically.
- Admit a Tag Attempt only from a description supporting the intentional
  touch, with reconciled agent and runner/base context. A putout category alone
  is insufficient. Do not infer strict catch-before-tag when receipt and base
  contact overlap.
- Hits, home runs, errors, sacrifices, deflections, rundowns and incomplete
  descriptions stay in the population inventory. Select any positively
  supported acts without declaring the whole play complete. No source field
  receives a zero just because credits or a recognized phrase are absent.

These are bounded evidence criteria, not a claim that the current payload
supports every play or that all mentioned actions meet the accepted differentia.
Selector output must retain which source spans and structured rows establish
each act, agent and order edge for inspection before RML execution.

## Validation and release

After acceptance: source selection, source-owned RML, one-record fixture,
whole-game SHACL and semantic inspection, then bounded NiFi corpus work.
SHACL checks exact selected act/agent/role/part membership, no extra identities,
and exact supported precedence edges. The separate complete-population proof
checks all eligible plays, not only those with selected acts. Depth and breadth
have separate order gates. A selected-play proof does not certify a game.

NiFi retains source, RDF, selector, SHACL and implementation hashes with the
promotion marker. SQL accepts only the promotion-bound proof supplied by the
NiFi materializer; requests cannot submit evidence. Values are calculated from
SPARQL graph bindings, never copied from source-side metric counters. The
existing full roster proof supplies team-game exposure independently.

Protected implementation scope after explicit acceptance: MLB context builder,
`sources/mlb-game/mapping/mlb-game.rml.ttl`, `mapping/iri-policy.yaml`, owning
mapping coverage records, source conformance and scoped mapping provenance
records. Acceptance does not authorize ontology edits or unrelated mappings.
