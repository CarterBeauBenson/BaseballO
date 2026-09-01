# Competency questions

1. Which Process represents one batter's turn against pitching?
2. Which Process realizes the Batter Role during that turn?
3. In which Person does the Batter Role inhere?
4. Does the same Batter Role persist across that Person's career, games, and
   Plate Appearances?
5. Which more specific source-supported Acts may additionally realize the
   Batter Role?
6. What does a Stasis assert about a Role, and what does it not assert?
7. Can a Plate Appearance exist without a Swing Act or Bunt Act?

Negative tests:

- a Stasis does not realize a Role or Disposition;
- a Role is not an occurrent part of a Plate Appearance;
- a Plate Appearance is not a Planned Act merely because it contains Acts;
- a Plate Appearance does not itself realize the Batter Role when its
  Batter Act supplies the realization;
- a new Batter Role is not minted for each game or Plate Appearance; and
- MLB's `atBatIndex` does not by itself classify the turn as an official
  statistical at-bat.

## Executable acceptance mapping

The accepted answers that constrain generated RDF are pipeline contracts, not
manual review prompts:

| Competency-question answer | Executable check |
| --- | --- |
| One Plate Appearance contains one generic Batter Act | Authoritative SHACL cardinality constraint |
| The Batter Act has the batter Person as participant | Authoritative SHACL qualified-value constraint |
| The Batter Act realizes one Batter Role | Authoritative SHACL qualified-value constraint |
| The realized Role inheres in that participant | Authoritative SHACL SPARQL constraint |
| The persistent Role uses the player-scoped identity pattern | Authoritative SHACL node-kind and IRI-pattern constraints |
| A Stasis does not realize a Role | Authoritative SHACL prohibition |
| The Plate Appearance does not duplicate the realization | Authoritative SHACL prohibition |

NiFi runs the authoritative SHACL profile after RML and before graph loading.
Failure blocks promotion. Python may launch the SHACL engine, serialize its
report, and check source/RDF mechanics, but it must not duplicate these semantic
acceptance decisions in imperative graph-review code.
