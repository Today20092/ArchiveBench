# Native visual comparison and saved decisions

Status: open
Readiness: ready-for-agent
Blocked by: 02-portable-presets

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Integrate an optional installed video-compare viewer for aligned original and candidate segments, using existing exact measured outputs and verified references where suitable. Preserve browser still/playback fallback. Save visual decisions separately from metrics, tied to source/candidate identities and reviewed intervals.

Likely areas: archivebench/media.py, cli.py, report review/export code, docs/installation.md and review instructions. Reuse existing software rather than implementing another player.

## Acceptance criteria

- Launch without shell-string interpolation and handle missing viewer, invalid paths and failed launch clearly.
- Verify temporal alignment, actual decoded dimensions and color-transform behavior on representative material; disclose display conversions and 10-bit/HDR limitations. Do not certify source fidelity from an 8-bit proxy.
- User can accept/reject a candidate and record objectionable moments; reopening the report/job preserves those decisions.
- Unavailable native viewer does not block access to existing review evidence. Terminal users can launch and record reviews without an agent.
- Evaluate external-program integration and licensing before bundling any third-party binary. Audio is verified/reviewed separately because the candidate viewer does not play it.

## Required checks

Argument/path tests, review-record invalidation tests, actual viewer smoke test, and offline browser/native-still/playback checks for affected report features. Mark untested display/editor combinations explicitly.

## Comments

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

