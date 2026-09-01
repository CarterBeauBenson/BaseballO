# MLB personnel transactions API

Status: **accepted by the ontologist on 2026-08-29; implementation pending**

This package covers a detachable future MLB transactions source lane. It does
not create one generic `Transaction Act`, because the provider collection is
heterogeneous: it includes trades, signings, roster assignments, status
changes, suspensions, number changes, retirement, and even death records.
Those do not share one honest act genus.

The uniform entity is an instance of the existing CCO Descriptive Information
Content Entity, not a new BaseballO record class. Each record remains about a
Person and, only when supported, one or more precise world-side processes. Its
type code is represented with the existing generic Nominal Measurement ICE and
a Reference System instance. A trade may span multiple person rows under one
repeated transaction ID; a death record is about a CCO Death, not a fictional
personnel act.

The proposal reuses CCO Act of Contract Formation, Act of Employment, Gain of
Role, Loss of Role, Stasis of Role, and Death. Existing team-scoped Occupation
Roles plus `has organizational context` already express the relevant
membership fact, so no roster-membership role is proposed. Only two world-side
BaseballO gaps remain: personnel trade and uniform-number assignment. The
package creates no field-specific ICE or reference-system class.

No RML, SHACL, NiFi group, source directory, or graph namespace is created in
this review phase.
