# Bimanual Bunker Mini

Bunker Mini mobile base with a lift and two robot arms, prepared as a new
ARGUS robot adaptor area for industrial inspection.

- Student maintainer: To be assigned
- Status: CAD and concept animation available; hardware connection code pending
- Intended simulation targets: MuJoCo or Isaac Sim
- Tested upstream version/commit: Not recorded

## Model and video

| Asset | Description |
| --- | --- |
| [STEP assembly](cad/bunker_mini_stepper_lift.STEP) | Original user-supplied finished assembly, including the base, lift and bimanual arms; 143,755,720 bytes, stored in Git LFS |
| [Industrial inspection video](media/Industrial_Inspection_Demo.mp4) | Blender concept animation; 36 seconds, 1280 x 720, 24 fps, H.264; 2,520,281 bytes |

The video shows the robot pressing an elevator call button, waiting for access,
entering and exiting the elevator, opening a stairwell door, and opening an
electrical cabinet to inspect its meter and breaker compartment.

## Retrieve and use

Install Git LFS, then run these commands from the repository root:

```bash
git lfs install
git lfs pull --include="connected-robots/bimanual-bunker-mini/cad/*"
```

Open the STEP file in a STEP-capable CAD application. Play the MP4 in a browser
or video player. GitHub source ZIP downloads may contain an LFS pointer instead
of the full CAD file; use the commands above to obtain the complete model.

The STEP file preserves the CAD assembly, but does not supply simulator joints,
actuators, collision settings or a Blender animation. The editable Blender scene
and simulation package are separate deliverables and are not included here.

## Controls and integration status

No ARGUS hardware commands are implemented in this adaptor yet. Base movement,
lift control, both arms, grippers, camera feedback and telemetry remain integration
work. MuJoCo and Isaac Sim setup dependencies will be recorded with the tested
runtime when simulator integration is added.

The video is an authored kinematic sequence. Door contact, collision avoidance,
autonomous navigation, physical joint limits, stop behavior, command timeouts and
network-loss behavior have not been validated by this video. Hardware motion
limits remain to be measured and documented before enabling real actuators.

## Provenance and verification

The project owner supplied the completed STEP assembly and requested its addition
to this repository. The video was rendered in Blender from that model for the
requested industrial inspection scenario; it is not customer or site footage.
No new license is granted to any underlying vendor components; the repository's
existing licensing terms and applicable upstream rights remain in effect.

Last asset verification: 2026-10-04. Both repository copies match their source
files byte-for-byte. The video was decoded successfully across all 864 frames.
See [asset-manifest.json](asset-manifest.json) for file sizes and SHA-256 hashes.

Next steps are to assign a maintainer, record the hardware inventory and upstream
versions, implement the ARGUS adaptor, and validate simulator and supervised
hardware behavior.
