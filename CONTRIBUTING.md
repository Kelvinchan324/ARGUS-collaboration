# Contributing to ARGUS

## Normal workflow

1. Create an issue that states the robot, intended behavior, and acceptance test.
2. Create a short branch from `main`, such as `feat/go2-video-bridge`.
3. Put shared cockpit work in `cockpit/`, or robot-specific work in the matching
   `connected-robots/<robot-name>/` folder.
4. Update that folder's README with setup or behavior changes.
5. Open a pull request using the repository template.
6. Ask the student responsible for that robot, plus the project owner when
   cockpit behavior changes, to review it.

Do not push directly to `main`. The GitHub repository should require pull
requests and at least one approval.

## Rules for hardware changes

- Default to simulation, replay, or actuators-disabled testing.
- State the tested robot, firmware, computer, operating system, and dependency
  versions in the pull request.
- Document command limits, timeouts, stop behavior, and loss-of-network behavior.
- Never commit credentials, API keys, Wi-Fi details, private IP addresses, logs
  containing personal data, or customer recordings.
- Keep hardware-specific logic inside its robot folder. Cockpit code should not
  directly depend on one robot's SDK.

## Third-party projects

Do not copy an entire upstream project into this repository. Link it in the
robot's README, record the tested version or commit there, and keep only the
ARGUS-specific connection code in this repository. If a fork is truly needed,
create a separately named fork and document why.

## Documentation expectations

Every robot README should name the student maintainer and cover setup,
dependencies, supported controls, safety limits, known issues, and the last
successful test.
