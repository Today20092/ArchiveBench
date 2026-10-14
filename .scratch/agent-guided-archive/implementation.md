# Implementation run

Integration branch: `codex/agent-guided-archive`.
Review baseline: `7491a64327d6f6a86730d0f3c4e8eca5ed34add7`.

The baseline preserves the earlier repeat-count/quality-level changes and approved specification. The original checkout remains on `codex/archivebench-quality-levels` so the running camera benchmark uses unchanged files. Implementation and merges happen in the isolated integration checkout. No public PR is requested; the local Markdown tracker closes tickets by marking done after acceptance and verification.

## Task graph

Ready initially: 01 installable skill, 02 portable presets. Tickets 03/04/05 depend on 02. Ticket 06 depends on 04/05. Ticket 07 depends on all earlier work.

Implementers use separate branches/worktrees, the TDD skill and the public seams approved in spec.md. Each merges the integration tip before completion. A merger subagent integrates completed branches sequentially. Final code review compares the pinned baseline to the integration branch, with separate standards and specification reviews; one implementer fixes findings. Generated media/private configurations stay out of Git.

Acceptance exploration notes are stored outside the repository. Manual native-viewer and editor evidence must report actual observed results; untested combinations remain explicit.

Tickets01/02 integrated and complete. Combined Python3.11 regression passed 58 tests, Ruffformat/check and ty passed, reportmath15passed, packagebuildpassed. The test process used four logical CPUs and no concurrent development suite. Ticket-specific native still/playback/browser/package checks are recorded in ticket comments. The next ready frontier is03bounded experiments,04native review and05reusable jobs.

Tickets03/04/05 integrated and complete after70 passing Python tests and all required report/browser/still/playback/package checks. Nativeviewer actual synthetic-frame rendering was observed; realcamera quality remains unreviewed. Ticket06 replacement acceptance is now ready. Current integration commit is recorded byGit; no source change was applied to the running camera experiment.

Ticket06 integrated and complete after74 passing Python tests, Ruffformat/check, ty, math15 andpackagebuild. Actual Resolve project-copy reopening and playback evidence was inspected and preserved outside the worktree. Ticket07delivery is now ready. A fresh process check found the historical camera benchmark interrupted with14savedtrials; cause unconfirmed. Its last checkpoint was not rewritten, and a new resume/time allowance was requested separately from implementation. Do not silently restart it.
