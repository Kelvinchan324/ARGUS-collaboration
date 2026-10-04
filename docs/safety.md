# Physical Robot Bring-up Checklist

## Before power

- [ ] Correct robot, hardware revision, and code version identified
- [ ] Test area clear; robot restrained or lifted when appropriate
- [ ] Emergency stop or physical power disconnect reachable
- [ ] Battery condition confirmed
- [ ] Speed/command limits and timeout configured
- [ ] Only one active command source

## Before motion

- [ ] Robot identity and connection confirmed
- [ ] Telemetry is current
- [ ] Stop tested with actuators disabled or at minimal power
- [ ] Directions checked one axis at a time
- [ ] Operator and observer agree on abort conditions

## After the test

- [ ] Return the robot to a safe state
- [ ] Record code version, result, faults, date, and tester in its README or issue
- [ ] Store large logs and recordings outside Git

Never perform unattended first-motion testing.
