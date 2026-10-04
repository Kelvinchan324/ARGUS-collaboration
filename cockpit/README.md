# Cockpit

> [Open the ARGUS website](https://kelvinchan324.github.io/ARGUS-collaboration/) · [English](https://kelvinchan324.github.io/ARGUS-collaboration/en/)

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

## Current public files

- [`cad/`](cad/) contains the current SolidWorks frame and seat-dimension part
  references. They are research files, not certified manufacturing drawings.
- Shared cockpit application code should be added under `src/` when it is ready
  to migrate from the development machine.
