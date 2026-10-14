# Bounded comparisons and useful progress

Status: open
Readiness: ready-for-agent
Blocked by: 02-portable-presets

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Add a small initial comparison path shared by setup and the skill. Make the chosen candidate list, rate modes, footage, formats, quality levels, repeats and budget visible before execution. Use actual pilot measurements for estimates. Expand only for an explicitly identified unresolved comparison or user-requested wider coverage. Preserve the existing thorough mode as an explicit choice.

Likely areas: archivebench/core.py, cli.py, validation.py, docs/benchmark.md and docs/configuration.md. Avoid changing the active benchmark's source checkout while it is running.

## Acceptance criteria

- One measured encode remains the default; identical settings across targets reuse evidence.
- A small initial experiment has a concrete bound and does not silently expand into all encoders/qualities/sample combinations. Full coverage requests are never silently narrowed.
- Progress distinguishes hashing, reference preparation, screens, measured encodes, scoring and validation; report completed counts and distinguish known work from adaptive remaining work.
- Show estimate uncertainty and budget exhaustion explicitly. Overnight means encoding patience; a hard deadline is a separate user choice.
- Compare codecs at common accepted quality when possible and compare quality changes within a codec. Preserve named conversion variants; no additive causal savings claims.
- Existing resume identities, frozen validation and single/multi-target behavior keep their guarantees.

## Required checks

Tests for bounded work, cache reuse, progress stages, missing/failed evidence and resume; real small FFmpeg exercise; standard Python/report checks for touched areas.

## Comments

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

