# Agent and terminal delivery verification

Status: open
Readiness: ready-for-agent
Blocked by: 01-installable-skill, 02-portable-presets, 03-bounded-experiments, 04-native-review, 05-reusable-jobs, 06-replacement-acceptance

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Finish the installed skill and standalone CLI documentation around the completed capabilities. Validate the full accepted workflow through both entry points. Publish installation/release artifacts only under the applicable user authorization; building local packages and release notes does not itself publish.

Likely areas: README.md, docs/, skills/archivebench/, package/release configuration and end-to-end fixtures. Check local AGENTS.md and relevant skill instructions before implementation.

## Acceptance criteria

- Compare representative agent tasks with and without the skill against the same CLI and fixtures. Record scope disclosure, unnecessary encoding work, user clarifications, reproducible settings, truthful quality claims and preservation/cleanup behavior. Include fresh setup, preset reuse on different footage, and unsupported-format cases. Report observed benefit and failures without a blanket reliability claim.
- Validate the skill against the open Agent Skills format and test discovery/execution on at least one named supported client outside the repository. Document untested clients rather than inferring working integration from the client showcase.

- A fresh agent skill installation can discover tools, run a bounded test, launch review, create a preset and prepare/run a job using only shipped references.
- A user without an agent can complete equivalent comparison, preset, archive and separate cleanup-preview steps from terminal instructions.
- Two folders use the same preset with independent resume state; include a scope mismatch and a keep-original exception.
- Report quality/savings/time explanations, evidence state and observed costs agree across both routes. Do not ship private footage/configs/results.
- Windows claims are supported by the checks; other platforms/editor combinations remain scoped. Update links, help and glossary consistently.

## Required checks

Python 3.11 locked sync, pytest, Ruff format/check, ty, bundled JS build, report math, offline browser, native still/playback checks and wheel/sdist build. Installed wheel/skill smoke tests outside checkout plus manual editor/native-viewer acceptance record.

## Comments

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

