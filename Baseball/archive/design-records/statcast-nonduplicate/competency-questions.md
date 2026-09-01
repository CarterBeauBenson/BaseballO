# Competency questions

These questions are source-independent. Passing them requires the graph to
represent reality and the information about reality separately.

## Source selection and detachability

1. Which retained Statcast facts are genuinely unavailable from the MLB games
   source, rather than renamed, unit-converted, or reconstructed MLB facts?
2. Can every Statcast assertion be removed without removing MLB game facts or
   changing MLB source identities?
3. Can a Statcast record be joined to the corresponding game, plate
   appearance, pitch, batter, and pitcher without treating a provider row ID as
   the identity of any of those entities?
4. Can a query distinguish direct MLB measurements, Statcast measurements,
   provider model estimates, and BaseballO-derived analytical classifications?

## Physical geometry

5. What actual Angle Quality does an arm-angle measurement measure, and which
   two Fiat Lines and shared Fiat Point constitute that angle?
6. Which bodily component and anatomical reference point support the
   shoulder-side Fiat Line without creating a field-specific ICE substitute?
7. What Fiat Point of the Baseball Bat is selected as its tracked sweet spot,
   and which versioned reference system establishes that selection?
8. What Process Profile of a Swing Act captures the changing motion of that
   Fiat Point?
9. Can attack angle and attack direction be represented for both contact and
   swing-and-miss cases without asserting a nonexistent Bat-Ball Contact
   Process?
10. What geometric construction turns the final 40 milliseconds of tracked bat
    motion into the plane or line used by a swing-path-tilt angle?
11. Are the intercept X and Y fields signed coordinate differences or
    nonnegative distances, and what are their origin, axis directions, and
    reference instant?

## Defensive configuration

12. What actual spatial configuration of fielder persons and field sites is
    classified by an infield or outfield alignment token?
13. During what temporal interval does that configuration hold relative to a
    Pitch Act?
14. Which provider/version reference system defines each alignment category,
    and can the token be represented as a nominal measurement without turning
    the category into a world class?

Negative test: an aggregate of Fielder Persons at a Baseball Field Site during
a Pitch Temporal Interval does not by itself entail a Defensive Fielding
Configuration; the relative player Sites and spatial relations must be
represented.

## Model outputs and expected outcomes

15. What actual or possible process is the target of a per-batted-ball xBA
    probability?
16. Which input measurements, comparable-event population, season, and model
    version condition that probability?
17. How does a per-event xwOBA estimate represent its distribution over
    possible single, double, triple, and home-run outcomes and its season
    weights?
18. What future Run Process aggregate is estimated by run expectancy, and does
    `delta_run_exp` include runs scored during the pitch?
19. What possible game-ending outcome is measured by home-team win expectancy?
20. Can before-state and after-state estimates be distinguished from the delta
    calculated between them?

## Barrel and Good At Bat use

21. Can a Barrel classification be derived from authoritative launch-speed and
    launch-angle measurement ICEs without ingesting the duplicate
    `launch_speed_angle` column?
22. Can the graph identify the versioned Barrel algorithm and retain the
    classification ICE separately from the actual BattedBallMotionProcess?
23. Can Good At Bat analytics consume the Barrel classification, xBA/xwOBA,
    attack geometry, and actual result without treating any one provider score
    as the truth of the plate appearance?
24. Can the analytical layer explain which contributing measurements and model
    versions supported a plate-appearance score?

## Provenance and missingness

25. Can a query distinguish absent, not tracked, not applicable, deprecated,
    estimated, and directly measured values?
26. Can historical method changes, including PitchFX/Statcast velocity eras,
    the 2019 xBA/xwOBA input change, the 2026 plate reference change, and the
    2026 ABS strike-zone change, be represented without silently merging
    incompatible reference systems?
