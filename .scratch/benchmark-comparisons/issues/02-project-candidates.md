# 02: Recommend shared settings across tuning samples

Status: open
Readiness: ready-for-agent
Blocked by: 01

## What to build

A user sees project-wide tuning-qualified candidates, weakest scenes and duration-weighted estimates rather than a combination of per-sample winners.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [ ] Measure each candidate's one encoder/quality/variant policy on all required tuning samples.
- [ ] Require every tuning sample to meet the target; missing, failed or unsupported samples prevent qualification.
- [ ] Identify weakest sample and completed/required coverage in the report.
- [ ] Average measured rates within each selected source, multiply by its full duration and sum across distinct sources without double counting.
- [ ] Label estimates as selected-source video-only projections and candidates as provisional pending fresh validation.
- [ ] Changing the display threshold never creates measurements or a validation claim.

## Required checks

Test an average-passing candidate with one failing scene, incomplete coverage, mixed durations, repeated sections from one source and report/export evidence labels. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

No implementation started.

