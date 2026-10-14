# Shared quality-level benchmark

Status: done
Blocked by: none

Scope: config validation, setup, tuning, target-specific shortlist/evidence, report comparison, documentation and tests.

Acceptance: old single-target configs work; invalid lists fail clearly; 80/90/95/97 share identical trials; one repeat remains the default; fresh checks are fixed and deduplicated; missing/unmet targets remain explicit; report displays size/quality/time by target without manufacturing validation; restart the authorized camera run in a fresh directory.

Checks: Python 3.11 pytest, Ruff format/check, ty, report math tests, bundled report build, offline browser/still/playback checks and package build.

## Comments

Previous single-target process stopped after verifying its command line. Its files are preserved; it had no completed measured trials or screens at interruption.

Implemented optional quality target lists, setup defaults 80/90/95/97, cached measurements and frozen search seeds for deterministic resume, deduplicated per-target validation, target-specific export evidence, and report quality-level comparisons. Single-target configs remain supported. Fixed a resume regression caught by the existing integration tests.

Verified on Python 3.11: 53 pytest tests passed; Ruff format/check and ty passed. Fourteen report math tests, two playback tests, offline browser checks and native still checks passed. Rebuilt bundled JS and built wheel/sdist. The synthetic CPU/GPU exercise completed with 18 tuning plus 6 validation trials, each one measured encode; one candidate served three targets with a single validation measurement. Browser checks cover target controls, exports, dense overlapping points, both themes, narrow layouts and zero network requests. No camera-quality conclusion is inferred from synthetic results.

Replacement camera run launched October 13 at 23:47:57 local time with the same eight tuning/fresh sections, targets 80/90/95/97, one repeat, and 600 minutes of timed work. The 4:2:0 variant runs first to reach GPU HEVC earlier. The actual camera benchmark remains in progress; completing it and visually choosing archive settings are separate from this implementation ticket. Old runs and all originals retained; no cleanup performed.

Later status before PR preparation: the camera process is interrupted with 14 saved trials and no completed fresh validation. Its last running checkpoint is historical, not evidence of an active process. Results and originals remain intact; it has not been restarted. The implementation ticket is complete, but no validated archival recommendation is claimed for that footage.
