# 01: Implement the confirmed chart-first report

Status: done
Readiness: ready-for-agent
Blocked by: none

## Scope

Implement the [confirmed specification](../spec.md) in the report template, application, math helpers and bundled JavaScript. Extend scoring results with frame timestamps and update report documentation and tests. Preserve pre-existing working-tree changes.

## Acceptance criteria

- [x] Tradeoff charts lead; selection and a pinned baseline connect all decision views.
- [x] Collection qualification rejects missing measurements and weak samples; thresholds are independent.
- [x] Ranking, sorting, scope/duration controls and the saved conclusion behave consistently.
- [x] Evidence shows real per-sample/frame measurements or explicit missing-data states.
- [x] Exact settings and decision-summary exports distinguish measurements, estimates and review.
- [x] Synchronized playback, seeking and media reset pass actual browser checks.
- [x] Required checks pass and the requested report is rebuilt.

## Required checks

Run pytest, Ruff format/check, ty, report math tests, bundled-JS build and offline browser checks. Use synthetic media for playback and benchmark integration tests; keep generated media and reports out of Git.

## Comments

- The user confirmed the interview decisions and explicitly authorized implementation.
- Existing unrelated changes were present before this work and are retained.
- Verification: 13 pytest tests, 10 report math tests, Ruff formatting/checks and ty all pass. The bundled JavaScript is rebuilt and the requested demo regenerated from unchanged canonical results.
- Offline browser verification passes linked selection/pinning, sample coverage, independent thresholds, saved conclusion, exports, review state, real synthetic playback/seek/pause synchronization, frame seeking, hostile labels, empty states and narrow layouts. Screenshots were inspected in light and dark themes; no network requests occurred.
- Browser tests use an isolated in-memory document without local-file navigation. Old runs explicitly lack frame timelines; browser playback remains codec-dependent and requires locally selected matching sample clips.
