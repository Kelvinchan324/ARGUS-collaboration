# ARGUS Collaboration

ARGUS is a multi-robot telepresence and control project. This repository is the
shared integration hub for the cockpit, ARGUS robot, Aloha Mini, Open Duck Mini,
Stanford Pupper V2, and Unitree Go2 through dimOS.

The repository owns the code and documentation that connects these systems. It
does **not** silently copy entire third-party projects. Upstream projects remain
separate and are recorded in [`third_party/dependencies.json`](third_party/dependencies.json).

## Start here

- [System architecture](docs/architecture/overview.md)
- [Robot integration status](docs/robots/README.md)
- [Developer setup](docs/setup/developer-environment.md)
- [How to contribute](CONTRIBUTING.md)
- [Migration checklist](docs/project/migration-checklist.md)

## Repository map

```text
adapters/       ARGUS-owned integrations for each robot
config/         Safe, versioned examples (never real secrets or robot IPs)
docs/           Architecture, setup, operating procedures, and decisions
hardware/       ARGUS-owned hardware notes and approved CAD
interfaces/     Stable command, telemetry, and capability contracts
scripts/        Setup and repository validation helpers
third_party/    Upstream dependency register; no vendored source
```

## Current phase

The collaboration framework is ready. Robot adapters are placeholders until the
existing working code is reviewed and migrated. Do not treat an adapter as safe
for hardware merely because its folder exists; check its status in the
[robot matrix](docs/robots/README.md).

## Safety

Robots can injure people or damage equipment. Test new integrations in
simulation or with actuators disabled, keep an accessible emergency stop, and
use the [bring-up checklist](docs/operations/bringup-checklist.md).

## Licensing

No project-wide license has been selected yet. Until the maintainers add one,
the original authors retain all rights to ARGUS-owned material. Every upstream
dependency keeps its own license. See [licensing guidance](docs/project/licensing.md).
