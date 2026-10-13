# Publish ArchiveBench as a public tool

Status: in-progress
Readiness: ready-for-agent
Blocked by: none; remote publication and CI verification in progress

## User intent

The user authorized public publication on their GitHub account after the full specification works and passes checks. ArchiveBench began as a way to archive their own footage. It gives videographers and editors a starting point to measure CPU/GPU quality, speed and storage tradeoffs on their devices, choose settings from the report, and use or adapt an archive script. Disclose that the project was built with AI coding agents.

## Acceptance criteria

- [x] Complete the approved feature spec and two-axis code review; resolve required findings.
- [x] Pass uv-based pytest, Ruff format/check and ty, report tests/build, offline browser checks, wheel build and a clean installed CLI smoke test.
- [x] Update README, installation/use guides and agent instructions to match implemented behavior, with a short project story and explicit AI-development disclosure.
- [x] Document the existing optional archive runner and exported-settings workflow for a neighboring Archived folder, keeping originals during encoding.
- [x] Check tracked source/history for private paths, media, local configs, logs and secrets before publishing.
- [ ] Create public Today20092/ArchiveBench, push verified source, and make installation and release downloads accessible.
- [ ] Verify remote contents, release assets and CI; report experimental hardware/platform limits honestly.

## Comments

GitHub connector and local Git credential manager identify Today20092. Repository name ArchiveBench was available at initial preflight. Publication is authorized; no further approval is needed.

Final local verification: 30 Python tests on Python 3.11 with pinned FFmpeg 8.1.2; Ruff format/check and ty; 13 report math tests and two real-file playback tests; offline chart/review and native-still checks. Built wheel and source distribution exclude local artifacts. Isolated wheel CLI completed both legacy and fresh-validation synthetic benchmarks. Standards review's temporary-path/docs findings and spec review's recommendation-card finding were fixed and independently verified. No remaining findings on either axis.
