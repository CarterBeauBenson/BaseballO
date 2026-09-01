# MLB venue reference-point coordinates

Status: **accepted 2026-08-30 — source-independent design**

The default latitude/longitude coordinate designates a real Baseball Venue
Reference Point: a provider-selected Geospatial Position associated with the
Venue. The coordinate ICE uses the existing CCO World Geodetic System 1984
Reference System and carries the latitude and longitude values directly.

The point is not asserted to be Home Plate, an entrance, or a centroid. Those
would require more specific evidence. Coordinate corrections create new
response-versioned evidence without replacing the stable Venue or asserting an
unsupported movement Process.

This package proposes `BaseballVenueReferencePoint` and no object property. It
authorizes no executable source change.
