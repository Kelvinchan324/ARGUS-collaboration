# Robot Integration Matrix

Status describes this repository, not the upstream project's maturity.

| System | Adapter status | Primary role | Upstream |
| --- | --- | --- | --- |
| Robot-AR | Inventory needed | Large ARGUS mobile/telepresence robot | Project-owned |
| Aloha Mini | Inventory needed | Dual-arm mobile manipulation | [liyiteng/AlohaMini](https://github.com/liyiteng/AlohaMini) |
| Open Duck Mini | Inventory needed | Biped research/character platform | [apirrone/Open_Duck_Mini](https://github.com/apirrone/Open_Duck_Mini) |
| Pupper V2 | Inventory needed | Quadruped research platform | [Pupper V2 Interface](https://github.com/stanfordroboticsclub/Pupper-V2-Interface) |
| Unitree Go2 | Planned | Mobile sensing/navigation through dimOS | [dimensionalOS/dimos](https://github.com/dimensionalOS/dimos) |

Before changing a row to `experimental`, add an adapter README with setup,
capabilities, limits, a simulator/replay test, and a named maintainer. Before
changing it to `supported`, record a physical smoke test and rollback procedure.

Use the [robot page template](robot-template.md) when adding detail.
