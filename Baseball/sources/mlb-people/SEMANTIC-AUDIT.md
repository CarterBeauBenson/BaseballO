# MLB people semantic audit

Status: accepted source contract implemented; bounded NiFi proof required before
the lane is activated for corpus backfill.

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
