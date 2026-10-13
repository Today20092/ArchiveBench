# 01: Compare named format variants

Status: done
Readiness: ready-for-agent
Blocked by: None

## What to build

A user selects editable named variants, runs one experiment, and compares labeled measurements in one offline report.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [x] Offer Match source as the only default selection, plus original-resolution 10-bit 4:2:0 and capped-1080p 8/10-bit 4:2:0 presets.
- [x] Show chosen combinations and a labeled test-count estimate before running; avoid implicit Cartesian expansion.
- [x] Resolve Match source per clip, preserving mixed resolution, chroma, bit depth and frame rate while re-encoding.
- [x] Carry variant identity through probes, trials, cache/resume, report selection and archive exports; preserve audio/extra-stream retention choices.
- [x] Show failed or unsupported variant/source combinations without silent encoder or format fallback.
- [x] Read old single-format configurations/results as one variant; preserve existing archive and cleanup safeguards.

## Required checks

Use synthetic mixed-format sources, config/result/export tests and offline browser checks. Demonstrate distinct variants in one report and verify cache separation. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

Implemented on `codex/ticket-01-format-variants`, based on integration commit `ad2f9d9`; merged integration update `dad7214` before completion.

Red-green slices covered saved config validation, real mixed-source variant encoding/resume, report grouping/export and default setup. Canonical results include `variant` and `stage` on measurements and variant-specific failures. Named variants use distinct encode directories while sharing each sample's verified original lossless reference. Existing single-format configs/results remain readable.

Verification: 17 pytest tests passed, including real FFmpeg mixed 10-bit 4:2:2 and 8-bit 4:2:0 sources, resolution caps, unsupported source rejection, resume, report generation and existing archive/cleanup safeguards. Ruff format/check and ty passed. All 11 report math tests passed; bundled JS rebuilt. The offline Edge browser check passed, including variant labels, same-resolution candidate separation, selected policy exports, hostile labels, narrow layouts and no network requests.

Presets are editable in saved config; setup accepts preset numbers or a custom format and resolution. Variants run in selected order within the existing budget, so a short budget can leave later variants incomplete. Shared-candidate tuning and validation are subsequent tickets. Encoder command/scoring adapters were reused unchanged.

After sharing references, both real encoding/resume regression checks passed again. One browser rerun caught an existing immediate SVG count race; the check now waits for the chart to mount, and the final browser run passed.

