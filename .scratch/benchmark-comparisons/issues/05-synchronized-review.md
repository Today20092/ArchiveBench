# 05: Review synchronized previews with exact-clip access

Status: open
Readiness: ready-for-agent
Blocked by: 03

## What to build

A user plays original/encoded sample previews together and can open exact measured clips while retaining a standalone shareable report.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [ ] Offer companion media for each validated finalist/sample after validation, within remaining budget.
- [ ] Synchronize sample-relative playback, seeking and pause state, and handle buffering/end-of-clip states without implying mismatched frames are synchronized.
- [ ] Label all converted previews and expose conversion details; provide exact encoded files for external playback.
- [ ] Show readable missing/unsupported-media states when the companion folder is absent or a codec cannot play.
- [ ] Use safe relative media references and keep standalone HTML usable without the media folder or network.
- [ ] Explain sharing privacy and browser limits on evaluating 10-bit/4:2:2 fidelity. Missing review media does not invalidate completed metric validation.

## Required checks

Check actual local playback, seek/pause synchronization, missing companion assets and no network requests. Verify preview labels, safe links and export/cleanup regression behavior. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

No implementation started.

