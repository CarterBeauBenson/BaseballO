# Source evidence

The accepted venue inventories observe 'timeZone.id', 'tz', 'offset', and
'offsetAtGameTime' in venue and game payloads. They withheld the fields because
identifier-system and offset temporal scope were not established.

CCO supplies Time Zone Identifier, Reference System, and designation, but its
imported Time Zone Identifier account designates a Spatial Region. BaseballO
does not use that spatial-region pattern. This proposal therefore leaves the
identifier's source-independent designation target unresolved rather than
silently inheriting it. A numeric offset is not timeless because legal rules
and daylight-saving transitions can change it. No raw response was acquired or
retained.
