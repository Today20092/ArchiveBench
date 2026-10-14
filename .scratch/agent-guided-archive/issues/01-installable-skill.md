# Installable agent skill

Status: open
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

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

