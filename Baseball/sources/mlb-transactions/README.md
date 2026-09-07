# MLB transactions source module

This detachable module maps the MLB Stats API `transactions` endpoint into the
information and grounded world-side graph accepted in
[`../../archive/design-records/mlb-transactions-source-contract/`](../../archive/design-records/mlb-transactions-source-contract/).
It references persistent Persons and Baseball Teams without redescribing them.
For exact Trade and signing rows with complete structured parties, it owns the
event evidence and transition-bounded Player Role identities described below.

## Owned boundary

- [`schema/`](schema/) documents the transaction, type-code, prepared-context,
  and optional Death-code-pin inputs.
- [`mapping/prepare-context.py`](mapping/prepare-context.py) validates transient
  API inputs before RML and creates an isolated execution context.
- [`mapping/mlb-transactions.rml.ttl`](mapping/mlb-transactions.rml.ttl) is the
  only RML owned by this source.
- [`mapping/iri-policy.yaml`](mapping/iri-policy.yaml) fixes the accepted
  deterministic identities.
- [`shacl/authoritative.ttl`](shacl/authoritative.ttl) validates only RDF
  emitted by this module.
- Runtime source validation uses Apache Jena with one bounded worker and the
  unchanged source-owned SHACL profile. The selected engine, validator hash,
  shape hash, and conformance report remain in the lane's evidence.
- [`fixtures/`](fixtures/) contains synthetic, one-record evidence. It is not a
  retained API response.
- [`tests/test_prepare_context.py`](tests/test_prepare_context.py) checks the
  pre-mapping gate and identity contract without touching runtime state.
- [`review/semantic-status.json`](review/semantic-status.json) records the
  accepted semantic status; the source catalog records the active operational
  status.

No file in this module imports another source's RML or SHACL. Integration occurs
only after independent promotion to the authoritative triple store.

The module owns separate connectors for the Transactions response and its
Transaction Types code list. It does not reuse the Games, People, or Teams
connectors; canonical IDs connect the promoted RDF afterward.

## Pipeline contract

```text
transactions API bytes + transactionTypes API bytes
  -> pre-mapping input/code-list validation
  -> isolated transactions-context.json
  -> source-owned RML
  -> source-owned authoritative SHACL
  -> source-owned authoritative event-graph promotion
```

The pre-mapping gate rejects malformed required identifiers, malformed source
dates, unknown `typeCode` values, and `typeCode`/`typeDesc` mismatches before
RML can omit or reinterpret them. SHACL then validates the emitted RDF; it does
not inspect the raw JSON. The raw inputs remain byte-identical and transient.
Their hashes, the context hash, mapping hash, SHACL report, and promotion
provenance belong in the NiFi run manifest.

The temporary context serializes non-ASCII code points with lossless JSON
Unicode escapes. This avoids the selected RMLMapper's Windows charset defect
without normalizing, ASCII-folding, or rewriting the source text. Row identity
is still computed from the original decoded Unicode content.

## Information graph

Each provider `id` identifies one grouping Descriptive Information Content
Entity. A generic Non-Name Identifier designates that group. Each semantically
distinct row/leg is a content-versioned Descriptive Information Content Entity
whose IRI ends in a SHA-256 of the accepted canonical selected-content object.
The grouping has that row as continuant part.

The row is about canonical `data/player/{id}` and `data/team/{id}` IRIs when
their source identifiers are present. This module does not type or describe
those persistent entities. A Nominal Measurement ICE classifies each row with
the exact MLB type code. A separate Descriptive ICE carries optional source
description text. Calendar Date Identifiers carry `xsd:date` values, designate
Days, and are distinguished by row-scoped field-key identifiers.

Rows outside the explicitly grounded branches remain information-only. Exact
`TR` groups map one Baseball Personnel Trade Act with both Teams as agents and
one Loss/Gain pair per complete Person/from-Team/to-Team leg. Exact `SGN` and
`SFA` rows with a Person and destination Team map an Act of Contract Formation
followed by Gain of the destination-team Player Role. Each transition has its
own Temporal Region within the effective-date Day. Signing alone does not
infer a Major League Free Agent Role.

## Death gate

There is no guessed or default Death code in this repository. Without
`--death-code-pin`, context preparation emits no Death rows.

An optional pin must:

1. bind the exact raw SHA-256 of the acquired `transactionTypes` bytes;
2. name a code whose exact paired description is `Death` in that snapshot;
3. reference an accepted ontologist decision whose canonical SHA-256 matches;
4. be explicitly listed in that decision's `authorizedArtifacts`; and
5. reside inside this module.

Only then may a matching transaction row with non-null `person.id` produce one
row-scoped CCO Death with that canonical Person as participant. Source dates
remain unbound to the Death boundary.

Release, retirement, free-agency declaration, roster movement, waiver/status,
and Uniform Number Assignment remain information-only because the current
endpoint surface does not establish every required agent, directive output,
exact affected Role, and boundary fact.

## Focused execution

Prepare the synthetic one-record context:

```powershell
python Baseball/sources/mlb-transactions/mapping/prepare-context.py `
  Baseball/sources/mlb-transactions/fixtures/one-record-transactions.json `
  Baseball/sources/mlb-transactions/fixtures/transaction-types.json `
  <temporary-directory>/transactions-context.json `
  --manifest <temporary-directory>/prepare-manifest.json
```

Run the focused standard-library tests:

```powershell
python -m unittest discover -s Baseball/sources/mlb-transactions/tests -p "test_*.py"
```

NiFi owns the independent process group, graph namespace, validation,
promotion, retry, and cleanup lifecycle. Once submitted, healthy runs are
asynchronous and are not continuously watched.

The `MLB Transactions` group passed its bounded proof, has an enabled 05:00
Eastern trigger for the prior Eastern-calendar day, and promotes one
event-evidence graph per requested date scope. It does not create a Game
query-index pair. Current run status belongs to source-local terminal NiFi
evidence, not this module contract.
