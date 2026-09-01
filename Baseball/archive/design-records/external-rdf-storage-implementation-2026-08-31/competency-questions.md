# Competency questions

- Can the persistent authoritative and indexed RDF move to an external volume without moving transient API payloads or the SQL serving layer?
- Can startup fail closed when the configured external volume is absent or replaced by a different volume at the same drive letter?
- Can the existing TDB2 store be copied only while writers are stopped and activated only after source/target integrity verification?
- Can the local store remain available as a rollback copy until its deletion is separately authorized?
