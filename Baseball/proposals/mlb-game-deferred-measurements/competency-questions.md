# Competency questions

1. Which exact motion portion or boundary is evaluated by start speed, end
   speed, exit speed, initial vectors, acceleration, and spin?
2. Are these local Process Profiles within one Motion Process, as required by
   the accepted time-shot guidance?
3. Which coordinate system fixes origin, axes, signs, units, handedness, and
   plate plane for every vector and position component?
4. Does `plateTime` denote elapsed duration from the initial tracking
   evaluation to plate crossing?
5. Which two Fiat Points and reference direction ground release extension?
6. Which anatomical Fiat Points on the batter determine the upper and lower
   Fiat Surfaces of the three-dimensional Strike Zone Site at the pitch
   evaluation, and which Home Plate boundaries determine its four vertical
   Fiat Surfaces?
7. What MLB Games documentation establishes the evaluation plane and method
   history of `pX`, `pZ`, `strikeZoneTop`, and `strikeZoneBottom`, independently
   of similarly named Savant fields?
8. Which break fields measure actual geometry, and which are fitted or derived
   provider outputs?
9. What rotational Process Profile, axis, frame, and unit ground spin rate and
   direction?
10. Which Fiat Lines and shared Fiat Point constitute launch angle immediately
   after contact?
11. Which source-specific Projection/Estimate ICE represents projected distance
    without inventing an actual or possible Distance Quality?
12. Which row-level evidence distinguishes tracked launch values from inserted
    estimates? Without it, retain only provider-reported value provenance.
13. Which provider classifications require versioned Reference Systems but no
    new world-side universal?
14. Accepted: every genuine MLB pitch-type Nominal Measurement ICE classifies
    the particular Pitch Act and may trigger a separately reviewed
    source-independent Pitch Act subtype. `Slider` is only an example.
15. Accepted: the Pitch Ball Motion Process remains distinct and carries its
    own measured Process Profiles rather than inheriting the Pitch Act type.
16. What provider convention fixes the origin Fiat Point, perpendicular axis
    Fiat Lines, sign, orientation, scale, component projection, and polygon for
    `coordX` and `coordY` without using Spatial Region classes? Until that is
    documented, can the tuple be retained only as provider-frame information
    and used for containment against a polygon expressed under that same
    convention?
17. For 2026 and later, does the Games feed's strike-zone evidence describe the
    three-dimensional rulebook Strike Zone Site, the two-dimensional ABS
    Evaluation Fiat Surface at the midpoint of Home Plate, or both? What
    source evidence selects the applicable method for each pitch?

Negative tests: no number attaches directly to a Pitch Act, ball, bat, Motion
Process, or source record; no vector exists without its frame; no estimate is
asserted as observed reality; a two-dimensional rendering is not asserted to
be the three-dimensional Strike Zone Site, and an ABS Evaluation Fiat Surface
does not replace that Site; no Spatial Region or Coordinate System Axis
individual is created; provider display coordinates are
not asserted as feet or latitude/longitude; no world-side Location Site is
minted from an ungrounded provider tuple; and field names do not supply missing
geometry.
