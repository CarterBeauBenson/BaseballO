# MLB venue time-zone evidence

Status: **under review — design only**

This package separates a stable Time Zone Identifier from abbreviations and
time-dependent UTC offsets. It asks whether 'timeZone.id' is an identifier in
the IANA system and what observation time scopes 'tz', 'offset', and
'offsetAtGameTime'.

The fields already occur in the MLB game payload. No mapping or ownership
cutover is authorized.
