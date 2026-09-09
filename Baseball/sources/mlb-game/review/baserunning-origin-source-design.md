# Runner origin through stasis boundaries

The four local runner object properties were withdrawn on 2026-09-09.
The [runner structural correction](../../../archive/design-records/runner-structural-correction/README.md) supersedes the earlier shortcut design.

The general `BaserunnerAtBaseStasis` is no longer restricted to a PA start.
Existing mapped instances keep their identities and gain the narrower
`PlateAppearanceStartBaserunnerAtBaseStasis` type. PA-start temporal and location
checks remain on that subclass. Stasis has participants, not agents or role
realizations.

Origin queries require the same runner, a Base participant, explicit precedence,
and a stasis ending at the act's first instant. Neither `movement.start`,
`movement.originBase`, the next recorded event nor a bare precedes edge proves
that boundary or persistence. No new stases or ending instants are emitted by
this correction. Existing PA-start evidence remains available in its own query;
origin stays unbound until authoritative boundary evidence exists.
