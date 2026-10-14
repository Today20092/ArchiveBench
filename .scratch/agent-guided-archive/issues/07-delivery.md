# Agent and terminal delivery verification

Status: done
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

Specified from the user-approved interview on 2026-10-14. Dependencies completed on the integration branch before delivery began. Updated installed references and terminal/installation/release documentation around actual shipped commands. Isolated wheel, named-client discovery, paired bounded model evaluation and two-folder terminal smoke are in progress. Aggregate integration regression/review remains required before closure. The camera benchmark and original checkout are untouched.

Delivery evidence is in docs/delivery-evaluation.md; raw synthetic/client artifacts remain outside checkout. Installed-wheel terminal two-folder jobs and packaged-skill discovery passed. Actual paired model attempts include inherited-model rejection, advertised-default bounded comparisons, partial scratch failures and a baseline timeout. Skill comparison/preset/job planning executed, but explicit model-driven archive execution stopped on WinError5 even with owned TMP/TEMP; this acceptance gap remains open. Focused test_skill, resource links, quick skill validator, Ruff format/check, ty and local wheel/sdist passed. Final serialized regression and review belong to the integration owner.

Final closure after review fixes: the restricted-client scratch failure is resolved with bounded inherited-permission job scratch. Actual installed-skill execution and resume passed; source/output hashes matched, keep-original exceptions remained intact and cleanup preview had zero eligible replacements without attestations. The five independent review findings and frame-rate follow-up are resolved. Report exports now carry scoped review/toolchain evidence and measured rates; preflight reports matching or untested footage without altering historical evidence.

Combined integration checks on Python 3.11: locked sync; 77 pytest tests passed in 144.69 seconds; Ruff format/check and ty passed; bundled JavaScript rebuilt; 16 report math tests and 2 playback tests passed; a fresh synthetic benchmark completed with 8 trials and fresh validation; offline browser and native-still checks passed. The wheel and sdist built; final wheel matched the isolated installed-wheel hash used for final inspection. The report screenshot was inspected. Earlier observed native-viewer and Resolve project-copy reopening evidence remains preserved outside the worktrees. All checks used synthetic footage; no camera quality acceptance, human attestation, cleanup execution or publication was fabricated. Paired evaluation supports narrow observed contributions, not a universal benefit claim.

