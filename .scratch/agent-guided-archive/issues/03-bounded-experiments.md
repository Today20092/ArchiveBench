# Bounded comparisons and useful progress

Status: in-progress
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

Specified from the user-approved interview on 2026-10-14. Implementing in the isolated archive-experiments worktree, based on the integration branch. CLI plan/status and synthetic benchmark/results are the approved public test boundaries. The current camera benchmark checkout remains untouched. Completion awaits combined integration checks.

Implemented initial/comprehensive selection, explicit adapter controls and bounds, saved initial attempt/search quotas, plan/status commands, stage counters and measured pilot estimates. Existing missing-comparison configs retain comprehensive behavior and runner/cache identity includes the planning code. Missing/failed target coverage remains unqualified; processing completion does not imply all targets passed.

TDD: new CLI plan test failed before adding commands; real synthetic limited-run test failed before adding the attempt limit. Both passed after implementation. Four focused experiment/wizard tests passed, including real FFmpeg shared-cache resume and budget exhaustion; 22 legacy validation tests passed. Python 3.11.14, four logical CPU affinity for test runs. Ruff format/check, ty, 15 report math tests and diff whitespace check passed. Report sources are unchanged, so bundled-JS/browser/still rebuild checks are reserved for combined integration. No real footage benchmarks or deadline guarantee tested. The native viewer, job acceptance and hardware-specific validation belong to their separate tickets.

