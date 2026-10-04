# Shared Interfaces

Versioned schemas for commands, telemetry, capabilities, and faults belong here.
The narrative contract is currently in `docs/architecture/interfaces.md`.

Add a machine-readable schema and fixtures before two or more adapters depend on
the same message shape. Breaking changes require a new schema version and an
architecture decision record.
