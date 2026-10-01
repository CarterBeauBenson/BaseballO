# MLB game acquisition gate removal, October 1, 2026

After the API workflow audit identified the local `Check Proof Release` stage
blocking schedule acquisition, Carter Beau Benson instructed:

> remove the contact MLB gate. They never responded and have not sent me anything saying stop. SO I think we are all good

The active flow has no gate depending on an MLB correspondence response. The
identified acquisition blocker is the local requirement for a completed sample
game whose mapping, context and SHACL hashes match the current checkout. This
record applies the user's gate-removal instruction to that acquisition blocker;
it does not represent a response, permission or approval from MLB.

Remove that prerequisite from the MLB-game daily and bounded schedule request
path. Connect `Prepare Schedule Batch` directly to `Acquire MLB Schedule`,
preserve queued requests, and recover the missed daily schedule work. Keep the
05:00 America/New_York trigger, HTTP retry handling, source-byte retention and
the existing per-game RML, SHACL, promotion and quarantine stages.

This changes an acquisition dependency within the existing lifecycle. It does
not approve ontology changes, new object properties, mapping changes, semantic
freeze updates, replacement of existing game graphs or a corpus rebuild. Other
source modules and explicitly authorized full-recovery proof checks retain
their own scope. This instruction is recorded before implementation.
