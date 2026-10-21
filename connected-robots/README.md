# Connected Robots

> [Open the ARGUS website](https://kelvinchan324.github.io/ARGUS-collaboration/) · [English](https://kelvinchan324.github.io/ARGUS-collaboration/en/)

Each robot has one self-contained folder. The student responsible for that robot
adds and maintains its connection code inside that folder.

| Robot | Folder | Current status |
| --- | --- | --- |
| SO-101 Bimanual | [`so101/`](so101/) | Physical leader teleoperation bridge for the cockpit; hardware validation pending |
| Robot-AR | [`robot-ar/`](robot-ar/) | Bridge and planner prototype imported; hardware validation pending |
| Aloha Mini | [`aloha-mini/`](aloha-mini/) | Inventory needed |
| Bimanual Bunker Mini | [`bimanual-bunker-mini/`](bimanual-bunker-mini/) | STEP assembly and inspection concept video; hardware adaptor pending |
| Open Duck Mini | [`open-duck-mini/`](open-duck-mini/) | Inventory needed |
| Pupper V3 | [`pupper-v3/`](pupper-v3/) | Inventory needed |
| Unitree Go2 with dimOS | [`unitree-go2/`](unitree-go2/) | Planned |

## What belongs inside each robot folder

- the ARGUS connection/control code for that robot
- a README naming the student maintainer
- setup and run instructions
- links to external projects and the tested version or commit
- safe example settings with no passwords, keys, or private addresses
- robot-specific tests and troubleshooting notes

Do not copy an entire external open-source project here. Link to it and keep only
the code your team wrote to connect it to the ARGUS cockpit.
