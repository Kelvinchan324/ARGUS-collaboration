# Task list (not executable yet)

These are **product skills**, not mock dances. Do not POST a fake open-door sequence.
A skill is ready only when `/capabilities` shows the needed slots `wired`.

## Now (no camera, no arm serial)

| Skill | Needs | Status |
|-------|--------|--------|
| Drive / stop | chassis USB | mock only |
| Phrase parser (`前進 1 秒`) | bridge | ready |
| E-stop | `/stop` | ready |

## After arms + calibrate

| Skill | Primitives |
|-------|------------|
| Home | `arm_preset home` |
| Open/close jaw | `gripper` 0..1 |
| Reach preset | `pick` / `place` (fixed joints — only if the scene matches) |

## After camera + VLA (`vla_act` wired)

| Skill | Notes |
|-------|--------|
| Open door | approach → `vla_act("grasp handle")` → rotate/pull → back up |
| Tidy / pick-place | `vla_act("pick up X")` then place |
| Search & rescue later | same contact primitives + mobility; planner stays LLM |

Opening a door is contact-rich. Scripted joint playback is not that skill.
