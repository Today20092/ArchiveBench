# 04: Inspect low-scoring moments at full resolution

Status: done
Readiness: ready-for-agent
Blocked by: 03

## What to build

A user inspects paired stills from weak moments with matching timestamps and controllable crop/zoom.

Follow the approved [specification](../spec.md) and [design decisions](../design.md). The user authorized implementation with implement-spec. Start when the listed blockers are done.

## Acceptance criteria

- [x] Retain frame-score evidence sufficient to select three separated low-scoring moments for each validated finalist/sample.
- [x] Generate paired original/encoded full-resolution stills from the same source instants, handling differing output dimensions and metric subsampling.
- [x] Show fewer than three moments when necessary and explain unavailable evidence.
- [x] Allow user-controlled crop/zoom with clear source/output dimensions; avoid presenting interpolated pixels as recovered detail.
- [x] Generate after validation within remaining budget; report missing assets separately from metric validation.
- [x] Keep report labels escaped, source paths redacted and generated assets private by default.

## Required checks

Use controlled per-frame scores plus real sample extraction to test temporal pairing and limited coverage. Check crop alignment, disclosures and missing assets in the offline browser. Run pytest, Ruff format/check, ty and report math tests for code changes. Rebuild bundled JS and run offline browser checks for report changes. Preserve source/output hashes, path boundaries, savings checks, decode checks and separate explicit cleanup.

## Comments

Implemented native-size weak-moment review in `archivebench/stills.py` and `report/stills.js`. Libvmaf evidence now stores original decoded frame indices. Select up to three measured moments separated by one second, extract paired native PNGs, verify input/cache hashes and path containment, and report incomplete assets independently of validation. The report exposes tuning and validation samples, shared normalized crop/zoom, conversion disclosures and readable missing-folder states. Existing embedded first-frame previews remain available.

Verification: full pytest passed, 26 tests after merging the integration source-boundary addition. Ruff format/check and ty passed. All 13 report math tests, bundled-JS build, existing offline browser workflow and dedicated still browser checks passed. The dedicated check covers real local PNG dimensions, matched crop coordinates, missing assets, validation selection and narrow/wide layout. Source hashes and the source-boundary integration guard remain intact.

Ticket05 composes its media hook after still generation with the same remaining-budget callback and sanitizes both companion asset fields in public results. Visual review is a display aid and cannot certify chroma/bit-depth preservation.

