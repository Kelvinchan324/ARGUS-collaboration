# Moving Existing Work into This Repository

Migrate one working component at a time.

1. Start with the shared cockpit communication and control code. Put it in
   `cockpit/` and add run instructions.
2. Choose the best-tested robot connection. Put only your ARGUS-specific code in
   that robot's folder under `connected-robots/`.
3. Add safe example settings, dependency links, and the exact tested versions to
   that robot's README.
4. Open a pull request and have another person review it before merging.

Do not migrate dependency folders, downloaded open-source projects, ZIP files,
presentations, interviews, customer material, videos, build output, passwords,
API keys, Wi-Fi credentials, or private network addresses.

Large original CAD should be added only when the team confirms ownership and
that it is necessary for building the system. Use Git LFS for approved binary
CAD files.
