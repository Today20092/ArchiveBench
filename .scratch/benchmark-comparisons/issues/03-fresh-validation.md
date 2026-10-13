# 03: Validate finalists on reserved fresh footage

Status: done
Readiness: ready-for-agent
Blocked by: 02

## What to build

A user approves fresh sections and a budget, then receives validated recommendations or explicit failed/incomplete outcomes.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [x] Propose one non-overlapping validation section per source; allow review/replacement before running. Default to twice tuning length capped at 60 seconds.
- [x] Reject overlap with tuning sections and disclose insufficient footage instead of reusing it.
- [x] Reserve 30% of one total budget by default; stop tuning before consuming the reserve and checkpoint incomplete validation.
- [x] Shortlist the smallest and fastest tuning-qualified candidates per variant, deduplicated.
- [x] Keep candidate settings fixed in validation. Failures never trigger tuning, automatic encoder switching or target reduction.
- [x] Recommend only candidates meeting the target on every required tuning and validation sample; distinguish provisional, failed and incomplete evidence.
- [x] Resume preserves stage identity and completed work. Exports include the selected policy and accurate evidence status.

## Required checks

Exercise interval checks, shortlist selection, deterministic budget interruption/resume and real fixed-setting validation. Verify failures block validated recommendations and exports. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

Implemented reviewed holdout sections, fixed-stage candidate measurement, frozen shortlist and explicit evidence status. One budget is shared per invocation, with explicit resume providing another allowance as recorded in the approved spec.

Verification: 24 Python tests passed on Python 3.11, six fresh-validation tests include real FFmpeg measurement/resume, controlled timeout, budget boundary and heldout failure. Ruff format/check and ty passed. All 13 report math tests passed, bundled JS rebuilt, and offline browser checks passed with a raised display target above a passing holdout score. Synthetic CPU/GPU demo ran fresh sections and retained originals. Report/export paths and diagnostics are redacted. Hardware compatibility beyond this machine remains dependent on the configured adapters.

Next visual-review tickets can use validation sample IDs `validation-N`, reference clips at `<run>/validation-N/reference.mkv`, unchanged trial output/hash fields, `validation_shortlist` candidate status and `remaining_seconds`. Review assets remain separate from metric validation.

