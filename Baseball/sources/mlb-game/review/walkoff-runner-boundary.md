# Supported walk-off runner histories

The [accepted question 8](../../../archive/design-records/walkoff-runner-boundary/review.json)
is implemented in the existing C1 source selection, RML, source SHACL,
serialization check and canonical query/SQL evidence. See the
[real proof](../../../benchmarks/metrics/walkoff-runner-boundary-2026-09-15/README.md).

A corroborated Final home win in the final bottom regulation/extra inning
must reconcile against scheduled innings, the previous score, final team
scores, counted scoring rows and one stable terminal event with compatible
game-end evidence. All existing half-history checks still apply. Still-active
histories use that event as the existing termination anchor and share the
already represented game-ending instant as their intervals' endpoint.
Histories ending in counted scores retain those scores, including all counted
home-run scoring. No third out is manufactured and game ending adds no erosion.

Source SHACL requires a same-game, typed, timestamp-supported endpoint and
rejects conflicting endpoints or a simultaneously asserted counted terminal
Out/Run on an active game-ended history. The mechanical verifier checks the
exact endpoint and episode inventories selected from source. These checks run
inside the existing NiFi lifecycle before promotion. The source manifest keeps
the final boundary and terminal kinds after raw input cleanup.

This bounded extension does not resolve placed-runner entry, offensive runner
substitutions, unresolved review effects, shortened-game termination, or all
within-PA ordering. Unknown histories stay withheld. Query/SQL retention of
individual histories and results does not certify full selected populations.
