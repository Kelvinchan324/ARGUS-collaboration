# ADR-0001: Use an integration hub, not a vendor monorepo

- Status: Accepted
- Date: 2026-10-04

## Context

ARGUS connects several independently maintained open-source robots. Copying all
of their source and assets into one repository would obscure licenses, make
updates difficult, and create large duplicated history.

## Decision

Keep ARGUS-owned interfaces, adapters, configuration, hardware changes, tests,
and documentation here. Track external projects in a dependency register. Pin
reviewed commits for reproducible deployments. Use a separate fork only when an
upstream contribution cannot carry a required patch.

ARGUS-owned binary CAD may use Git LFS after it passes the migration checklist.
Large recordings, datasets, model checkpoints, and generated outputs belong in
versioned artifact storage, not normal Git history.

## Consequences

The repository stays reviewable and ownership is clearer. Initial setup requires
an explicit dependency/bootstrap step, and contributors must record compatible
upstream revisions.
