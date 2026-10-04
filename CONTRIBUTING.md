# Contributing to ARGUS

## Normal workflow

1. Create an issue that states the robot, intended behavior, and acceptance test.
2. Create a short branch from `main`, such as `feat/go2-video-bridge`.
3. Make a focused change and update the relevant documentation.
4. Run `python scripts/validate_repo.py`.
5. Open a pull request using the repository template.
6. Obtain review from the owner of each affected area before merging.

Do not push directly to `main`. The GitHub repository should require pull
requests and at least one approval.

## Rules for hardware changes

- Default to simulation, replay, or actuators-disabled testing.
- State the tested robot, firmware, computer, operating system, and dependency
  versions in the pull request.
- Document command limits, timeouts, stop behavior, and loss-of-network behavior.
- Never commit credentials, API keys, Wi-Fi details, private IP addresses, logs
  containing personal data, or customer recordings.
- Keep hardware-specific logic inside its adapter. Shared interfaces must remain
  independent of any one robot.

## Third-party projects

Do not copy an upstream project into this repository. Add or update an entry in
`third_party/dependencies.json`, pin a reviewed commit before deployment, and
put only ARGUS-specific patches or adapters here. If a fork is truly needed,
create a separately named fork and document why.

## Documentation expectations

Every robot page should cover ownership, setup, network path, supported
capabilities, safety limits, known issues, and a last-known-good test record.
Use diagrams and commands that can be updated as the system changes.
