# 04: Inspect low-scoring moments at full resolution

Status: open
Readiness: ready-for-agent
Blocked by: 03

## What to build

A user inspects paired stills from weak moments with matching timestamps and controllable crop/zoom.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [ ] Retain frame-score evidence sufficient to select three separated low-scoring moments for each validated finalist/sample.
- [ ] Generate paired original/encoded full-resolution stills from the same source instants, handling differing output dimensions and metric subsampling.
- [ ] Show fewer than three moments when necessary and explain unavailable evidence.
- [ ] Allow user-controlled crop/zoom with clear source/output dimensions; avoid presenting interpolated pixels as recovered detail.
- [ ] Generate after validation within remaining budget; report missing assets separately from metric validation.
- [ ] Keep report labels escaped, source paths redacted and generated assets private by default.

## Required checks

Use controlled per-frame scores plus real sample extraction to test temporal pairing and limited coverage. Check crop alignment, disclosures and missing assets in the offline browser. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

No implementation started.

