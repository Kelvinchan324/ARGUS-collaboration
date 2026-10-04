# Existing Work Migration Checklist

Migrate by component, not by copying an entire working drive.

## 1. Inventory

For each candidate folder, identify its owner, purpose, maintainer, source
repository, license, size, generated files, secrets, personal/customer data, and
whether it is the authoritative copy.

## 2. Choose a destination

| Material | Destination |
| --- | --- |
| ARGUS integration source | `adapters/`, `interfaces/`, or a future application folder |
| ARGUS-owned CAD needed to build | `hardware/` with Git LFS and an export/BOM |
| Third-party source unchanged | Upstream link in `third_party/dependencies.json` |
| Required third-party patch | Separate fork plus a documented pinned revision |
| Videos, ROS bags, datasets, checkpoints | External artifact storage with version/checksum |
| Proposals, interviews, quotations, company records | Private document system, not this code repo |
| Build outputs, dependencies, archives | Regenerate; do not commit |

## 3. Review before adding

- [ ] Repository visibility is appropriate
- [ ] Copyright and license allow the intended use
- [ ] Secrets and personal/customer data are removed
- [ ] File is not a duplicate archive
- [ ] Files above normal Git size use approved LFS or artifact storage
- [ ] README explains how the material is used and maintained
- [ ] A reviewer other than the uploader has checked the change

## Suggested first migration batches

1. Cockpit communication/control source and its current protocol notes
2. ARGUS robot control source and interface mapping
3. Small ARGUS-owned cockpit/armrest/foot-pedal CAD, BOM, and assembly exports
4. One robot adapter at a time, beginning with the currently best-tested link
5. Test fixtures and sanitized example configuration

Do not migrate presentation archives, interview material, dependency folders,
downloaded ZIP files, or full upstream robot trees in the first pass.
