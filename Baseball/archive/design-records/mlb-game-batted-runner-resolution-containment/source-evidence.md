# Source evidence for the bounded A1 implementation

The current mapping already creates a Batted-Ball Play Process for an evidenced
contact pitch and retains its terminal PA result as a part. It separately
creates per-row Runner Resolution Processes. A1 supplies a missing connection
between those existing individuals, without changing their identities.

Read the checked-in [original fixture](../../../data/raw/game-566279.json),
SHA-256 `e36caf73ff54d6eeac29dba350d5d37001e769eaaf4c1a9e5eac4763ad2630c2`.
In `liveData.plays.allPlays[23]`, runner 606466 has a steal at event index 5
and a scoring resolution on a single at index 7. Only the latter belongs in
the initial terminal-contact association. Preserve row indexes 0 and 2 as
different records/resolutions.

[Game 822693](../../../data/raw/samples/2026-08-25/822693.json), PA 36,
has a strikeout and wild-pitch advances at the same event index.
[Game 823826](../../../data/raw/samples/2026-08-25/823826.json), PA 78,
has mixed strikeout/wild-pitch labels and a null batter placeholder. Neither
is an evidenced terminal batted-ball play for this addition.

An initial mechanical selection can require a completed PA, the existing
terminal in-play pitch condition, an unambiguous explicit event-index join,
a recognized contact-result category on both result and runner row, and an
existing boolean-supported runner resolution. More complex or differently
classified secondary consequences may be omitted from this bounded addition.
They are not declared independent or assigned a default metric value.
