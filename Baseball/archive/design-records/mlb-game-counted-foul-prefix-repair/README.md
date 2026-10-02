# F4: finish the counted-foul substitution repair

**Accepted by the user on October 1, 2026; implementation follows this decision.**
The user answered **"Approve"** to the explicit request for F4's tested
three-strike repair and scoped context-hash update. This records that named
acceptance before implementation. The reviewed package was published on `dev`
at `6eb1f45`; the exact patch and candidate hashes below remain unchanged.

The [patch](selection.patch) repairs one existing source-selection function:

- Reuse C3's retained replacement witness when Q7 withholds the incoming
  pinch-runner's zero-episode history. W1 already uses the same helper. Require
  consistent reconciliation, exact outgoing/incoming identities, base and time
  witnesses, unchanged count and outs, and no movement, review or scoring effect.
- Include a rostered DH in the existing count-neutral pre-pitch switch selection.
  This is source administration for selecting the subsequent foul; it does not
  assert a defensive act or assign a Fielder Role to the DH.

The competency question is whether these independently reconciled, count-neutral
records should suppress a later recorded pitch that increments strikes from one
to two. They should not. The actual pitch, counter increment, participants and
times still supply the foul-strike evidence. Existing M3/M4 maps supply its graph
pattern. No ontology term, object property, identity policy or metric changes.

## Exact evidence and selection

| Game | PA index | Prefix | Missing strike selected |
| --- | --- | --- | --- |
| 822682 | 50 | PR with no later movement; pickoff attempt | `839f74ce-afdd-33dd-af88-490a45bcd322` |
| 822682 | 58 | DH switch | `c2e8b154-4bd4-3c13-b6c4-e20702e8e3de` |
| 822688 | 53 | PR with no later movement; mound visit | `32fa7d8b-6fc0-3079-93cd-187d2fb6f991` |

[Evidence](evidence.json) records the exact retained input and candidate hashes.
The candidate generates 42 triples through the five unchanged foul-strike maps,
all belonging to these three strike identities. The later two-strike foul in
822688 remains excluded. Neither zero-episode personal history is admitted.
Thirty-nine mutations of count, participants, replacement witnesses, roster,
position, movement and result flags are rejected. Existing C3 and W1 checks pass.
The C3 test's older blanket overlap expectation is corrected to H3's accepted
rule: a reconciled count-neutral substitution may overlap the first pitch;
actual pitch-to-pitch overlap remains excluded.

The field selection inventory is unchanged: event type, position, substitution,
participants, base, counters, timestamps, review/scoring flags and runner rows
are already supplied by the MLB game lane. This repairs coverage of those fields;
it acquires no new field or source. The existing accepted
[M3/M4 graph design](../mlb-game-counted-foul-completion/README.md)
and [Q7 isolation](../mlb-game-zero-episode-history-isolation/README.md)
remain authoritative. No new Mermaid shape is required.

## Exact activation scope

The acceptance covers F4's patch and this scoped context-pin update:

- Old context SHA-256:
  `7d90c64f64e03c920578bf40100677c1534a791792cf49a08b2426fe7c9141d6`.
- New context SHA-256:
  `86f6f6ad62eec5795b6bc464a0040c210e8be4bb83e94e65b765b943eb3cc00e`.
- Patch SHA-256:
  `7ff564597eeb8546f3ecd810ee2273060d1cbb8f53da03d7b823de27c82b76c1`.

Only this context pin, its containing protected-set digest, its runtime/inventory
references and exact retained-proof compatibility may advance. The global freeze
remains unratified. Unrelated protected artifacts remain unchanged. Preserve old
proof identities and outcomes; the fingerprint update must not trigger RDF
regeneration or pretend a failed graph check passed. The modified function only
changes foul selection; W1 already accepts the zero-episode witness separately.

After acceptance is recorded and pushed separately, apply the patch and its
engineering consequences. The existing NiFi foul-addition lane owns bounded
retries, existing source SHACL over base plus addition, additive promotion and
downstream SQL refresh. Changed implementation fingerprints make the recorded
failed cases retryable. Its usual bounded discovery may find the same supported
pattern elsewhere. Do not replace whole games, rebuild RDF, or replay already
promoted PA49 merely to repair PA50/58.

This is a source-selection fix, not a claim that the dashboard or every source
conflict is resolved. No live RDF was changed by the offline candidate check.

The original focused check requires the pre-implementation context and the
pinned retained inputs. From this decision commit, before applying the patch:

```powershell
python -B Baseball/archive/design-records/mlb-game-counted-foul-prefix-repair/check.py
```

The check applies only the candidate patch to a disposable copy, runs the
existing mappings locally, and never mutates the active context or live graph.
