# Portable preset contract and evidence

Status: done
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

Integration validation on 2026-10-14: 58 pytest tests passed on Python 3.11 with the test process restricted to four logical CPUs, serialized against other development suites. Ruff format/check, ty, 15 report math tests and combined package build passed. Implementer recorded focused preset/installer tests, offline browser exports, still review and two playback checks. Earlier load-sensitive regression failures were resolved by the passing serialized run. Contract is available for dependent tickets in archivebench/presets.py and design.md.

Implemented the version 1 portable preset contract, legacy import and inspection, preset consumption by the existing archive runner, and offline report export. The schema and public seams are recorded in the design. Original camera runs remain unchanged.

Recovery verification: four focused preset tests passed on Python 3.11, including two folder roots using one unchanged preset; Ruff format/check and ty passed; 15 report math tests, offline browser export checks, native still checks and two playback tests passed. The report was regenerated from existing synthetic results before the browser export check. Package build and diff checks passed. Earlier full-suite failures occurred during concurrent camera/test workloads; integration must run a serialized full regression before closing this ticket. No camera quality or actual GPU/editor acceptance claim is made by these synthetic checks.

