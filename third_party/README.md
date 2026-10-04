# Third-party Dependencies

`dependencies.json` is the source register for external projects used by ARGUS.
It is not an automatic instruction to download every project.

When an integration becomes reproducible, replace `pinned_commit: null` with the
tested full commit SHA and record the same SHA on the robot page. Review the
upstream license and security posture whenever the pin changes.

Do not place downloaded upstream source, release archives, package caches, or
generated dependencies in this directory.
