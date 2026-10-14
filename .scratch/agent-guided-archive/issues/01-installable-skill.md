# Installable agent skill

Status: done
Readiness: ready-for-agent
Blocked by: none

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Package an ArchiveBench skill with an explicit trigger and a short decision workflow. Read skill-creator and writing-for-agents instructions when implementing. Reuse docs/agent-workflow.md and current CLI commands, with branch-specific references for discovery, comparisons, preset reuse, archive jobs and cleanup. Locate tools before installing dependencies; provide actionable manual installation when needed. Keep the skill usable outside the repository.

Likely areas: a new skills/archivebench/ package, docs/agent-workflow.md, docs/installation.md and packaging/release configuration. Do not create a parallel FFmpeg implementation.

## Acceptance criteria

- Follow the open [Agent Skills specification](https://agentskills.io/specification): valid required frontmatter, name matching the directory, concise activation description, and skill-relative resources. Run the reference format validator. Keep client-specific installation/discovery details outside the shared workflow.
- Test representative activation prompts and unrelated negative cases; format compatibility must not be presented as verified execution support across all clients. Explain local terminal/filesystem/FFmpeg requirements.

- Include every referenced file in the distributable package or use a tested stable lookup; no private absolute paths or agent-specific hidden state.
- Use existing commands in the first skill version; label capabilities pending other tickets rather than claiming them implemented.
- Reuse supplied user choices; disclose repeat count, format changes, scope and cost before running. Explain metric versus visual acceptance and retain separate cleanup authorization.
- A fresh installation in a temporary agent skill directory resolves all references and can invoke the installed CLI from an unrelated working directory.

## Required checks

Validate skill metadata/references and run a documented smoke walkthrough outside the checkout. Follow docs/development.md for code/package changes.

## Comments

Integration validation on 2026-10-14: 58 pytest tests passed on Python 3.11 with the test process restricted to four logical CPUs, serialized against other development suites. Ruff format/check, ty, 15 report math tests and combined package build passed. Ticket-specific validator, isolated installed-wheel smoke and playback checks were recorded by the implementer. Earlier concurrent-load regression failures were resolved by the serialized passing run; no failing checks were hidden. Paired agent evaluation and final skill updates remain assigned to ticket07.

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

Implemented a canonical `skills/archivebench` package with branch-specific local references, included in the wheel, plus the `archivebench-skill --destination` installer. Existing installs are preserved. The portable workflow calls the shared CLI and labels release-dependent preset/job/review operations rather than claiming unavailable commands. Client-specific installation and smoke cases are in docs/installation.md and docs/skill-smoke.md.

TDD: the public outside-checkout installation test failed before the module existed and passes after implementation, including linked-resource resolution, CLI invocation and overwrite refusal. Official skills-ref and the local skill-creator validator pass. A newly built wheel installed into a fresh Python 3.11 environment successfully installed its skill and invoked doctor/help from an unrelated directory. Four activation and three unrelated cases were walked through for routing coverage; paired model execution remains ticket 07, and cross-client execution support is not claimed.

Checks: focused test passes; Ruff formatting/check and ty pass; build passes; 14 report math tests and 2 playback tests pass. Full regression returned 50 passed and 4 failed legacy tiny-budget validation tests under simultaneous test/render load, including one synthetic-source FFmpeg failure. Global regression must be serialized and completed on the integration branch before this ticket is marked done. Report sources were unchanged; a rebuilt bundle had only line-ending churn and was restored. No camera files or active benchmark processes were changed.

