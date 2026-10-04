# Cockpit

This is the shared ARGUS application. Cockpit code should handle the operator
controls, user interface, robot selection, video/telemetry display, and the
common connection layer used to reach the connected robots.

Put code here when it is useful to more than one robot. Do not place a robot's
vendor SDK or hardware-specific commands here; keep those in that robot's folder
under `connected-robots/`.

## Suggested contents as the code is migrated

```text
cockpit/
├── src/          Cockpit application source
├── tests/        Shared cockpit tests
├── assets/       Cockpit-owned UI assets
└── README.md     Setup and run instructions
```

Only create these subfolders when there are real files to put in them.
