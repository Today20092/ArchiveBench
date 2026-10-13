# 01: Compare named format variants

Status: open
Readiness: ready-for-agent
Blocked by: None

## What to build

A user selects editable named variants, runs one experiment, and compares labeled measurements in one offline report.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [ ] Offer Match source as the only default selection, plus original-resolution 10-bit 4:2:0 and capped-1080p 8/10-bit 4:2:0 presets.
- [ ] Show chosen combinations and a labeled test-count estimate before running; avoid implicit Cartesian expansion.
- [ ] Resolve Match source per clip, preserving mixed resolution, chroma, bit depth and frame rate while re-encoding.
- [ ] Carry variant identity through probes, trials, cache/resume, report selection and archive exports; preserve audio/extra-stream retention choices.
- [ ] Show failed or unsupported variant/source combinations without silent encoder or format fallback.
- [ ] Read old single-format configurations/results as one variant; preserve existing archive and cleanup safeguards.

## Required checks

Use synthetic mixed-format sources, config/result/export tests and offline browser checks. Demonstrate distinct variants in one report and verify cache separation. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

No implementation started.

