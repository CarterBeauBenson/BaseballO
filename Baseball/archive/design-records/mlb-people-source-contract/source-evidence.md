# Source evidence

## Provider surface

Provider: MLB Stats API. The accepted investigation observed the official
people endpoint through a request such as:

- <https://statsapi.mlb.com/api/v1/people/660271?hydrate=currentTeam>

Observed person records expose `id`, `fullName`, `nickName`, name parts and
renderings, birth date/place fields, `height`, bare integer `weight`, batting
side, pitching hand, primary position/number, status metadata, debut/draft
fields, strike-zone values, and optional current-team hydration. No raw response
is retained by this proposal.

## Existing MLB-game overlap and accepted ownership

The authoritative MLB live-game contract already exposes these person fields
under `gameData.players.*`. Their presence is semantic duplication even when
the current game RML omits a field. The accepted source-ownership decision now
assigns person identity, names, and accepted descriptive reference facts to
`mlb-people`, while game participation and game-scoped roles remain in
`mlb-game`.

The people graph must therefore be populated and compared before any future
game-reference cutover. Existing promoted game RDF is not deleted or rewritten
by this contract.

## Positive and nearby negative evidence

| Evidence | Claim supported | Nearby claim not supported |
| --- | --- | --- |
| `id` in the people resource | An MLB person identifier designates a Person under the MLB person-ID Reference System. | The integer is an intrinsic Person quality. |
| `fullName` and `nickName` | Proper Name and Nickname ICEs designate that Person and preserve exact source text. | Name-part ontology, legal-name status, preferred-name status, or timeless validity. |
| A strict value such as `6' 4\"` | The syntax explicitly supplies feet and inches and can be losslessly normalized to strictly positive total inches for a Height measurement. | A measuring event, instrument, method, agent, or measurement time. |
| Bare integer `weight` | The provider reports a body-size number conventionally interpreted as pounds. | The payload itself or reviewed official documentation establishes the unit; a mapping to pounds is therefore withheld. |
| `birthDate` | The response is about a Birth involving the Person and contains a Date Identifier designating a Day. | The Birth occupied the whole Day or an accepted Birth-to-Day temporal relation exists. |
| `batSide`, `pitchHand`, `primaryPosition` | Provider classifications are available for later study. | A complete realist target for persistent batting disposition, bodily laterality, or customary/roster/game role. |
| `currentTeam`, `primaryNumber` | Provider context is present at acquisition time. | A historically scoped occupation-role context or uniform-number assignment interval. |

## Encoding evidence

Earlier checked artifacts contained mojibake such as `MejÃ­a`, proving that an
apparently valid source name can be corrupted by a repeated or mismatched
decode. The repository's UI regression corpus already uses the correct
`Eugenio Suárez` spelling. The people proof must establish an exact UTF-8
round trip before promotion.

The literal preserves the exact decoded scalar sequence. A normalized form may
be used only inside a deterministic name-IRI hash; it must never rewrite the
RDF lexical form.

## Existing vocabulary

The accepted vocabulary supplies Person, Height, Mass, Birth, Proper Name,
Nickname, generic Measurement Information Content Entity, Descriptive
Information Content Entity, Non-Name Identifier, Calendar Date Identifier,
Reference System, Day, Inch, and the required existing relations and direct
ICE value properties. No new class or property is proposed.

Mass and Pound being available does not make the provider integer's unit
known. Availability is not evidence.

## Operational evidence contract

Successful API bytes are transient. Before RML, a source-contract input
validator checks every present selected ID, ISO date, and height string; height
must also compute to total inches greater than zero. Malformed present values
quarantine the response. Null or absent optional values remain valid and emit
nothing. Post-RML SHACL validates only RDF that was emitted and cannot detect a
source field the mapping omitted.

The future source lane persists request URI/time, HTTP status, response
SHA-256, mapping version, input-validation result, SHACL report, graph hash,
promotion target, and outcome. World entities are stable; the response and its
reported measurement/date evidence are content-versioned; array positions
never enter identity.
