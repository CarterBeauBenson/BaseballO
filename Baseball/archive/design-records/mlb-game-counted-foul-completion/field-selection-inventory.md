# Field selection

All fields belong to the existing MLB game module. No duplicate provider
mapping or new endpoint population is proposed.

| Field | Selection | Use |
| --- | --- | --- |
| gamePk, revision, atBatIndex, playId, event index | Identity/join-only | Reuse current identities and provenance; no ordinal-to-BFO precedence. |
| isPitch, event type, call code, description, isBall/isStrike | Already supplied by authoritative source | Reconcile actual pitch/bunt/neutral-event kind; M3/M4 extend bounded coverage. |
| Event balls/strikes/outs | Already supplied by authoritative source | Source admission conditions; no count ICE or source-to-SQL value. Outs keep event scope. |
| Event start/end time | Already supplied by authoritative source | Bound and reconcile order; do not assign these times to runner or review acts. |
| Substitution player/replaced-player IDs and roster | Identity/join-only / already supplied | Verify initial pitching replacement and subsequent actual pitcher; no new role tenure. |
| Runner ID, playIndex, start/end/out flags | Already supplied by authoritative source | Reconcile count-neutral steal report with the existing running act and safe resolution. |
| reviewDetails, inProgress, isOverturned, final call flags | Already supplied by authoritative source | Operative count reconciliation only; original judgment reconstruction remains outside scope. |
| Counted strike/judgment/decision presence | Deterministically derivable after reviewed source conditions | Reuse full existing pattern and source SHACL. |
| General numeric count-state representation | Unresolved / not proposed | M3/M4 do not add this representation. |
