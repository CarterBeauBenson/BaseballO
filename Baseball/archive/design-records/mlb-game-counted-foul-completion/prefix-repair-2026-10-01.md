# Counted-foul prefix coverage repair

**Prepared and tested; publication blocked.** Automatic approval review rejected
the commit on October 1 because it did not recognize explicit authorization for
this semantic-freeze update. The specific approval request is pending. The
executable changes are held outside the active checkout until that is resolved.

The [September 30 narrow repair authorization and overlapping-region answer](../metric-repair-scope-2026-09-30/answers.md)
apply to these omissions in the already accepted counted-foul pattern. This
records implementation under that authorization, not a new ontologist decision.

The first NiFi repair game, 822678, was blocked by four existing foul strikes:
PA 24 after a pickoff out, PA 60 after an initial pitching change and pinch
hitter, and PAs 63 and 70 after defensive switches. Their old and current
hash-bound source censuses agree on the selected pitch identities, counts,
clocks and outcomes. The mapper's blanket prefix exclusions nevertheless
rejected them.

The corrected selector requires an exact pickoff-attempt/runner/out join,
unchanged ball/strike counts and a continuing inning; or rostered initial
substitution participants with actual subsequent pitch agency. A reconciled
initial substitution's interval may overlap another record. Each interval
must remain internally consistent and actual pitches retain their observed
order. Unknown reviews, changed counters, missing identities, contradictory
outs and two-strike held fouls remain excluded.

NiFi's existing targeted addition runs only the five counted-foul maps for
the selected missing pitches, then the existing count and retained admission
SHACL. The repair does not remap a whole game or rebuild the corpus. The test
fixture is a small derived context projection from the retained 822678 input,
with its original response hash; it is not an ingest input.

The context edit does not change the admission source censuses or SHACL
expectations. Exact compatibility entries preserve their original producer
hashes, source hashes and outcomes, including withheld outcomes. Existing
SQL and unrelated RDF therefore remain reusable. The global semantic freeze
remains unratified; only its context pin changes under the accepted mapping
package and narrow repair scope.

This repairs a recorded queue failure. It is not evidence that all 19 metrics
or all season populations are complete; publication and dashboard coverage
must be reported separately.
