# 02: Recommend shared settings across tuning samples

Status: done
Readiness: ready-for-agent
Blocked by: 01

## What to build

A user sees project-wide tuning-qualified candidates, weakest scenes and duration-weighted estimates rather than a combination of per-sample winners.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [x] Measure each candidate's one encoder/quality/variant policy on all required tuning samples.
- [x] Require every tuning sample to meet the target; missing, failed or unsupported samples prevent qualification.
- [x] Identify weakest sample and completed/required coverage in the report.
- [x] Average measured rates within each selected source, multiply by its full duration and sum across distinct sources without double counting.
- [x] Label estimates as selected-source video-only projections and candidates as provisional pending fresh validation.
- [x] Changing the display threshold never creates measurements or a validation claim.

## Required checks

Test an average-passing candidate with one failing scene, incomplete coverage, mixed durations, repeated sections from one source and report/export evidence labels. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

Implemented shared-candidate measurement, full-source identities/durations, weakest-scene evidence and provisional exports. Adaptive per-sample searches discover candidates; a shared measurement pass fills each candidate's missing tuning samples within the budget. Failed or budget-limited measurements remain visible and cannot qualify.

Red-green evidence: a real synthetic motion/flat-scene experiment initially lacked coverage for differing quality settings. The completed implementation measures each discovered setting on all three sections across two source files and reuses those outputs on resume without changing originals. Controlled report fixtures verify the weakest-scene gate, missing coverage, averaging repeated sections per source, distinct full durations and legacy extrapolation.

Checks passed: 18 pytest tests, 12 report math tests, Ruff format/check, ty, bundled-JS build and offline browser checks. The browser workflow verifies source-duration defaults, weakest-scene labels, three-of-three coverage, provisional archive exports, chart selection and threshold controls with no network requests. A fresh demo used CPU encoders and the available NVIDIA encoder. General hardware/editor coverage remains outside this ticket.

