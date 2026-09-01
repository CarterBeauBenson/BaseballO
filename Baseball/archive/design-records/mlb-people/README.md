# MLB people API coverage and gap review

Status: **accepted gap and de-duplication record on 2026-08-29; no mapping authorized**

This package evaluates whether the standalone MLB people endpoint contributes
a nonduplicative semantic surface. The current answer is **no** for the fields
observed here: every potentially useful person attribute is already present in
the authoritative MLB game payload under `gameData.players.*`. A field that is
not yet emitted by the game RML is MLB-game mapping coverage debt, not evidence
that a second source should own the assertion.

The people endpoint could later widen population coverage or provide a
different refresh cadence. That operational benefit does not establish new
semantic content. A future lane therefore requires an explicit ownership and
coverage decision before RML: which population it alone covers, which source
owns each assertion, and how duplicate triples are prevented.

No class or property is proposed. Existing CCO vocabulary covers Person,
Birth, Height, Mass, names, measurements, nominal classifications, and
reference systems. The review instead records four genuine modeling gaps that
must not be hidden in new ICE labels:

- the world-side spatial structure behind persistent batting-side capability;
- the anatomical and spatial structure behind pitching-hand laterality;
- the referent of MLB's `primaryPosition` classification; and
- the temporal scope and institutional meaning of `currentTeam`.

Unicode round-trip remains a mandatory proof gate for the MLB-game completion
work. Names such as `Francisco Mejía` and `Eugenio Suárez` must remain exact
from transient HTTP response through RDF, SPARQL, SQL, and UI output.

This package does not authorize a people source module, RML, SHACL, NiFi lane,
RDF promotion, SQL materialization, or UI exposure.
