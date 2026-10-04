# Physical Robot Bring-up Checklist

## Before power

- [ ] Correct robot, hardware revision, firmware, and adapter version identified
- [ ] Test area clear; robot restrained or lifted when appropriate
- [ ] Emergency stop or physical power disconnect reachable
- [ ] Battery condition and voltage confirmed
- [ ] Command limits and heartbeat timeout configured
- [ ] Only one active command source

## Before motion

- [ ] Network path and robot identity confirmed
- [ ] Telemetry is current and timestamps are sane
- [ ] Stop command tested with actuators disabled or at minimal power
- [ ] Joint/velocity directions checked one axis at a time
- [ ] Operator and observer agree on abort conditions

## After test

- [ ] Return to safe state and remove power when required
- [ ] Record versions, result, faults, and owner in the pull request or issue
- [ ] Store large logs/recordings outside Git and link only approved artifacts

Never perform unattended first-motion testing.
