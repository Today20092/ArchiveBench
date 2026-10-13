# Publish ArchiveBench as a public tool

Status: done
Readiness: ready-for-agent
Blocked by: none

## User intent

The user authorized public publication on their GitHub account after the full specification works and passes checks. ArchiveBench began as a way to archive their own footage. It gives videographers and editors a starting point to measure CPU/GPU quality, speed and storage tradeoffs on their devices, choose settings from the report, and use or adapt an archive script. Disclose that the project was built with AI coding agents.

## Acceptance criteria

- [x] Complete the approved feature spec and two-axis code review; resolve required findings.
- [x] Pass uv-based pytest, Ruff format/check and ty, report tests/build, offline browser checks, wheel build and a clean installed CLI smoke test.
- [x] Update README, installation/use guides and agent instructions to match implemented behavior, with a short project story and explicit AI-development disclosure.
- [x] Document the existing optional archive runner and exported-settings workflow for a neighboring Archived folder, keeping originals during encoding.
- [x] Check tracked source/history for private paths, media, local configs, logs and secrets before publishing.
- [x] Create public Today20092/ArchiveBench, push verified source, and make installation and release downloads accessible.
- [x] Verify remote contents, release assets and CI; report experimental hardware/platform limits honestly.

## Comments

GitHub connector and local Git credential manager identify Today20092. Repository name ArchiveBench was available at initial preflight. Publication is authorized; no further approval is needed.

Final local verification: 30 Python tests on Python 3.11 with pinned FFmpeg 8.1.2; Ruff format/check and ty; 13 report math tests and two real-file playback tests; offline chart/review and native-still checks. Built wheel and source distribution exclude local artifacts. Isolated wheel CLI completed both legacy and fresh-validation synthetic benchmarks. Standards review's temporary-path/docs findings and spec review's recommendation-card finding were fixed and independently verified. No remaining findings on either axis.

Published public [Today20092/ArchiveBench](https://github.com/Today20092/ArchiveBench) and [v0.1.0](https://github.com/Today20092/ArchiveBench/releases/tag/v0.1.0) at cc94bfc0059012366b4a30d8c15e4895f64c3c12. [Final source CI](https://github.com/Today20092/ArchiveBench/actions/runs/38382625895) passed every step. Release assets include wheel, source distribution, reviewed synthetic demo ZIP and SHA256SUMS; upload digests verified against local bytes. Public wheel URL installs and runs help/doctor through isolated uv on Python 3.11. Public README reviewed at desktop/mobile widths; badges and documentation links work. Optional overnight scheduling wrapper remains a separate follow-up; existing batch archive runner is documented.
