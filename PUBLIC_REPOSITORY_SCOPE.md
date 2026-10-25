# Public repository scope

## Private-repository research exception

The owner confirmed the repository is now private. The four STP report-back
PDFs and interview synthesis are authorized for collaborator-only storage in
`docs/private-reference/`. This narrow exception does not authorize public
publication, unrelated participant records, or credentials. The Pages builder
excludes that directory. Keep it out of any alternative website deployment.
Before making the repository public, review both current files and Git history;
deleting a file from the latest commit alone does not remove previous copies.
The public-material rules below continue to apply to the website and other exports.

This repository is the public technical integration hub for ARGUS. It should
contain material that collaborators can review, test or use to reproduce the
system without exposing people, customers, networks or internal business work.

## Included

- ARGUS-owned cockpit and shared-control source code
- Robot-specific adapters, tests and setup documentation
- Safe example configuration without credentials or private addresses
- Necessary, ownership-confirmed CAD references
- Public architecture, roadmap and safety guidance
- Small, purposeful website assets with known provenance

## Kept outside this public repository

- Interviews, participant records and customer material
- Names, contact details, signatures and identifiable event photographs
- Internal business-model, pricing, budget and mentor-feedback decks
- Credentials, Wi-Fi details, private IP addresses and calibration secrets
- Duplicate QA renders, temporary files and generated build output
- Complete copies of external open-source projects or vendor firmware
- Large presentation and poster working files that do not help build or test the system

## Review before adding

Before committing a binary document, image, CAD model or external source tree,
confirm ownership, licensing, privacy, technical purpose and whether a link to
the original source would be better. Public documentation should distinguish
verified functionality from work in progress and planned research.
