# MLB people semantic audit

Status: accepted source contract implemented; the bounded NiFi proof completed
and the source lane is active. The [module guide](README.md) describes its
independent population discovery. Current run status and proof applicability
belong to source-local NiFi evidence.

The implementation follows the accepted people source contract and the
accepted Mass, laterality, and position-cluster extension packages. Every
measurement ICE measures a world-side Quality or Disposition. Every name and
identifier designates the stable Person, and every Birth is a Process with the
Person as participant. No measurement process, realization event, or
Birth-to-Day localization is invented.

The pre-RML gate rejects malformed present identifiers, dates, heights,
weights, laterality codes, position tuples, and invalid UTF-8. Null or absent
optional fields emit nothing. The post-RML SHACL profile validates the
resulting RDF only.

Excluded questions remain player-team stint history from `currentTeam`,
uniform-number assignment, strike-zone geometry, and debut/draft acts.
