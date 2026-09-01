# Source evidence

CCO defines Day (`cco:ont00000800`) as a Temporal Interval based on one
rotation of an Astronomical Body relative to a Temporal Reference System, and
Calendar Date Identifier (`cco:ont00001340`) as an identifier that designates
a Day. BFO supplies `precedes`, `occupies temporal region`, and `temporal part
of`.

Observed MLB game evidence supplies a UTC `dateTime`, an `officialDate`, and a
venue IANA time-zone identifier. MLB transaction dates supply a date without a
time-zone field. The design therefore preserves the game source's UTC and
venue-local evidence while refusing to invent transaction-zone precision.

