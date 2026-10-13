# Publish ArchiveBench as a public tool

Status: in-progress
Readiness: ready-for-agent
Blocked by: completion and review of benchmark-comparisons tickets 01–05

## User intent

The user authorized public publication on their GitHub account after the full specification works and passes checks. ArchiveBench began as a way to archive their own footage. It gives videographers and editors a starting point to measure CPU/GPU quality, speed and storage tradeoffs on their devices, choose settings from the report, and use or adapt an archive script. Disclose that the project was built with AI coding agents.

## Acceptance criteria

- [ ] Complete the approved feature spec and two-axis code review; resolve required findings.
- [ ] Pass uv-based pytest, Ruff format/check and ty, report tests/build, offline browser checks, wheel build and a clean installed CLI smoke test.
- [ ] Update README, installation/use guides and agent instructions to match implemented behavior, with a short project story and explicit AI-development disclosure.
- [ ] Document the existing optional archive runner and exported-settings workflow for a neighboring Archived folder, keeping originals during encoding.
- [ ] Check tracked source/history for private paths, media, local configs, logs and secrets before publishing.
- [ ] Create public Today20092/ArchiveBench, push verified source, and make installation and release downloads accessible.
- [ ] Verify remote contents, release assets and CI; report experimental hardware/platform limits honestly.

## Comments

GitHub connector and local Git credential manager identify Today20092. Repository name ArchiveBench was available at initial preflight. Publication is authorized; no further approval is needed.
