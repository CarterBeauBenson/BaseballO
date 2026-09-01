# MLB people input contract

The transient provider document is an MLB people response with exactly one
record in `people` for the current proof and corpus-driven lane. NiFi supplies
the canonical resource kind (`player` or `person`) and expected provider ID
from the authoritative-corpus seed.

Selected source fields are `id`, `fullName`, `nickName`, `height`, `weight`,
`birthDate`, `batSide`, `pitchHand`, `primaryPosition`, and `currentTeam.id`.
Null or absent optional fields are allowed. Present selected values must pass
`mapping/prepare-context.py` before RML, including exact laterality codes and
the reviewed position tuple table. Unselected provider fields do not license
RDF assertions.

MLB primary-position code `Y` is the reviewed composite case. Its Position
Description describes the same Person and that Person's persistent Pitcher
Role and Fielder Role. It does not type the Person as a primitive two-way kind
and does not assert that either Role is realized by the response.

`one-record.synthetic.json` is hand-authored test data, not a retained API
response. It proves exact Unicode preservation and the admitted reference
grains without retaining an API payload.
