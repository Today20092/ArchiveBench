# Portable preset contract and evidence

Status: open
Readiness: ready-for-agent
Blocked by: none

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Define a versioned reusable preset around existing archive-settings exports. Store exact encoder/rate-control settings and format/retention policy, explanation, tested footage/hardware/toolchain scope and evidence references. Keep source/destination paths and checkpoints in jobs. Expose import, inspection and export in the CLI as well as the report. Propose concrete schema and compatibility handling before code changes.

Likely areas: archivebench/archive.py validation, formats.py, cli.py, report.py, report/math.js and report/app.js. Add a focused preset module only if it gives the shared contract a clear home.

## Acceptance criteria

- A preset can be used with two different folder roots without editing its encoding settings or historical evidence.
- Codec display names include the actual implementation/hardware and why to choose it; avoid universal quality claims.
- Scope matching separates unsupported hardware/format from untested footage. Explicitly skipping a suggested sample check does not create current-project validation.
- Legacy archive-settings and manifests remain readable with their documented semantics; malformed or incompatible settings fail clearly.
- Measured estimates include source mix, sample coverage and exclusions. Changing quality/format choices cannot retain unrelated validation.

## Required checks

Contract round-trip, invalid-input, scope mismatch and legacy regression tests; report export math tests and browser checks when touched; all required development checks.

## Comments

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

