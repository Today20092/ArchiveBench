# 03: Validate finalists on reserved fresh footage

Status: open
Readiness: ready-for-agent
Blocked by: 02

## What to build

A user approves fresh sections and a budget, then receives validated recommendations or explicit failed/incomplete outcomes.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [ ] Propose one non-overlapping validation section per source; allow review/replacement before running. Default to twice tuning length capped at 60 seconds.
- [ ] Reject overlap with tuning sections and disclose insufficient footage instead of reusing it.
- [ ] Reserve 30% of one total budget by default; stop tuning before consuming the reserve and checkpoint incomplete validation.
- [ ] Shortlist the smallest and fastest tuning-qualified candidates per variant, deduplicated.
- [ ] Keep candidate settings fixed in validation. Failures never trigger tuning, automatic encoder switching or target reduction.
- [ ] Recommend only candidates meeting the target on every required tuning and validation sample; distinguish provisional, failed and incomplete evidence.
- [ ] Resume preserves stage identity and completed work. Exports include the selected policy and accurate evidence status.

## Required checks

Exercise interval checks, shortlist selection, deterministic budget interruption/resume and real fixed-setting validation. Verify failures block validated recommendations and exports. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

No implementation started.

