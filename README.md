# ARGUS Collaboration

ARGUS is a multi-robot telepresence and control project. This repository is the
shared integration hub for the cockpit, Robot-AR, Aloha Mini, Open Duck Mini,
Stanford Pupper V2, and Unitree Go2 through dimOS.

## Where work goes

```text
ARGUS-collaboration/
├── cockpit/             Shared cockpit application and control code
├── connected-robots/    One folder for each robot
├── docs/                Short project-wide guides
├── CONTRIBUTING.md      How students submit work
└── README.md             Project entry point
```

- Shared cockpit code belongs in [`cockpit/`](cockpit/).
- Robot-dependent code belongs in that robot's folder under
  [`connected-robots/`](connected-robots/).
- A student working on one robot should normally change only that robot folder.
- Project-wide explanations and safety procedures belong in [`docs/`](docs/).

Each robot folder should eventually contain its code, setup instructions,
dependency list, configuration example, and tests. Keeping these items together
makes it easy for a student to understand and maintain one complete integration.

## Connected robots

- [Robot-AR](connected-robots/robot-ar/)
- [Aloha Mini](connected-robots/aloha-mini/)
- [Open Duck Mini](connected-robots/open-duck-mini/)
- [Pupper V2](connected-robots/pupper-v2/)
- [Unitree Go2 with dimOS](connected-robots/unitree-go2/)

The robot folders are currently placeholders. Their maintainers should add only
the ARGUS-specific code they use. Keep full external open-source projects in
their original repositories and link to them from the robot README.

## Short guides

- [How the cockpit connects to each robot](docs/architecture.md)
- [How to move existing work into the repository](docs/migration.md)
- [Physical robot safety checklist](docs/safety.md)
- [Licensing guidance](docs/licensing.md)

## Safety

Robots can injure people or damage equipment. Test new integrations in
simulation or with actuators disabled, keep an accessible emergency stop, and
use the [bring-up checklist](docs/safety.md).

## Licensing

No project-wide license has been selected yet. Until the maintainers add one,
the original authors retain all rights to ARGUS-owned material. Every upstream
dependency keeps its own license. See [licensing guidance](docs/licensing.md).
