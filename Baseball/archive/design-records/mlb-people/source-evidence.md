# Source and de-duplication evidence

## Provider observation

Provider: MLB Stats API. Inspected transiently on 2026-08-28 through the
official endpoint:

- <https://statsapi.mlb.com/api/v1/people/660271?hydrate=currentTeam>

No response JSON was retained. Future acquisition must keep raw API payloads
transient and preserve request, response, and promoted-graph hashes.

## Authoritative MLB-game overlap

The checked authoritative game contract exposes a complete people object at
`$.gameData.players.*` in
`Baseball/sources/mlb-game/schema/mlb-feed-rml-source-schema.yaml:432-906`.
It includes all seven fields that an earlier draft incorrectly called new:

- `nickName` at approximately line 797;
- `birthDate` at approximately line 478;
- `height` at approximately line 606;
- `weight` at approximately line 893;
- person-level `batSide` at approximately line 448;
- person-level `pitchHand` at approximately line 809; and
- `primaryPosition` at approximately line 827.

The same game object also contains the other name, birthplace, debut, roster
number, status, pronunciation, and presentation fields evaluated in this
package. The standalone endpoint can widen coverage, but it does not supply a
new kind of assertion for those fields.

## Physical-measurement evidence

`height` is emitted as a feet/inches string and `weight` as an integer
conventionally interpreted by MLB as pounds. The world-side targets are CCO
Height and Mass qualities inhering in the Person. MLB's label `weight` does not
license CCO Weight, which is relative to a gravitational field. These existing
game fields belong in the later MLB-game completion design, using direct ICE
values and units only if the shared ICE foundation is accepted.

## Laterality and primary-position gaps

Person-level `batSide` uses `L`, `R`, and `S`; person-level `pitchHand` uses
`L` and `R`. The values are provider classifications, not the spatial or
anatomical entities that ground them. `S` describes a capability to bat from
more than one side, not a third physical side. A particular plate appearance's
matchup side is also not identical to a persistent capability.

The pinned vocabulary contains CCO Spatial Orientation and Bodily Component,
but the checked evidence does not yet support a complete relata/identity model
for batting stance or pitching-hand anatomy. `primaryPosition` is similarly
ambiguous between customary role, roster designation, and classification of a
Person. All three fields stop at the ontology gap; generic Nominal Measurement
ICE does not cure an unknown target.

## Encoding evidence

The checked schema inventory contains corrupt lexical evidence such as the
UTF-8 name `Mejía` decoded as `MejÃ­a`. That is evidence of a prior decoding
error, not a source spelling. A later proof must compare Unicode scalar
sequences across HTTP, generated Turtle, parsed RDF literal, SQL row, and UI
JSON.

## Existing vocabulary coverage

Existing terms cover Person, Birth, Height, Mass, Proper Name, Nickname,
Measurement Information Content Entity, Nominal Measurement Information
Content Entity, Reference System, Date Identifier, Spatial Orientation, Bodily
Component, and all required accepted relations. No new object property is
required, and this review does not justify a new named class.
