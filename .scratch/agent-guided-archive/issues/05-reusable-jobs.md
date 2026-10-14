# Reusable folder jobs and explicit exceptions

Status: done
Readiness: ready-for-agent
Blocked by: 02-portable-presets

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Extend the existing archive command with a saved job configuration and immutable resolved preset snapshot. Accept arbitrary source/output folders, default project preset and explicit stronger-setting/keep-original exceptions. Reuse manifest checkpoints and verification. Offer a thin reusable launcher only if it improves terminal usability; all encoding remains in the shared runner.

Likely areas: archivebench/archive.py, cli.py, docs/archiving.md and archive integration tests. Existing source/output/settings parameters are the foundation, not a replacement runner.

## Acceptance criteria

- Dry-run resolves eligible files, settings, exceptions, destination mapping, compatibility gaps, scratch needs and estimated size/time where evidence exists.
- The same installed runner/preset processes two independent project folders with separate manifests; no repository-specific or private paths are embedded.
- Resume verifies source/output identities and cannot silently change settings after preset edits. Keep-original exceptions are excluded from both encode and cleanup selections.
- Preflight unsupported streams/container combinations before long batch work; failures preserve originals and leave inspectable checkpoints.
- Retain hash/path/stream/decode and actual-savings checks. Report not-worth-encoding files explicitly.
- Terminal execution and agent invocation of equivalent jobs use identical resolved settings.

## Required checks

Two-folder integration test; interruption/resume; changed preset/source/output; exception and traversal/collision checks; retained audio/metadata and insufficient-savings cases; standard development checks.

## Comments

Combined integration checks passed on 2026-10-14: Python3.11 pytest70passed with serialized four-logical-CPU tests, Ruffformat/check andty, reportmath15/build, freshdemo/offlinebrowser/native-still/playback2 andpackagebuild. Twofolder, exceptions, snapshot, interruption/resume, changedmedia, unsupportedpreservation andactualsavings tests passed. Jobcleanup remains intentionally guarded until ticket06 supplies scoped visual/editor acceptance. No camera archives or deletion performed.

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

Implemented shared `job create|inspect|run`, embedded immutable preset snapshots, exact-file
keep-original/stronger-setting exceptions, bounded short encode/mux preflight, mapping/scratch
and historical video-only estimates. Runner reuses encoding/verification/checkpoints and binds
the job snapshot in the manifest; each encoded record carries resolved settings. Job cleanup is
blocked pending ticket06 acceptance. Unsupported data/timecode/cover art or extra video streams
retain originals. Inspection never grants metric or visual acceptance.

Focused Python 3.11 tests: two-folder execution; interruption/pending checkpoint/resume;
preset file edits; changed settings/output/source; malformed media; exact keep/stronger
exceptions and traversal; insufficient actual savings. Ruff and ty passed for touched code.
Global checks remain for integration. No camera batch or original cleanup performed.

