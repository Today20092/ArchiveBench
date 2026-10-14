# Editor reopening and replacement acceptance

Status: open
Readiness: ready-for-agent
Blocked by: 04-native-review, 05-reusable-jobs

Specification: [agreed scope](../spec.md). Design: [implementation map](../design.md).

## Scope

Define a concrete editor reopening/relinking acceptance path tied to each job. Keep automated verification, visual acceptance and user editor confirmation separate. Review current MKV naming, camera timecode/data, metadata and sidecar limitations. Support a documented tested path or retain originals for unsupported requirements. Strengthen the new workflow's cleanup eligibility without reinterpreting legacy evidence.

Likely areas: archivebench/archive.py verification/cleanup, job records, cli.py and docs/archiving.md. Container changes require actual codec/stream/editor verification rather than renaming extensions.

## Acceptance criteria

- Document and demonstrate one explicitly named editor/version/container workflow using a project copy and representative footage; do not advertise universal NLE support.
- Provide deterministic source-to-output mapping and retained requirements so the user can reconnect media; never modify the only project file automatically.
- Visual and editor attestations refer to verified output identities; changed outputs invalidate acceptance.
- Cleanup previews only eligible replacements and still requires a separate explicit execute action. Encoding, metric validation and preset approval cannot authorize deletion.
- Unsupported proprietary metadata/data/timecode or sidecar needs produce a visible keep-original outcome unless a tested preservation path exists.
- Legacy manifests retain documented handling; any newly required acceptance migration is explicit and tested.

## Required checks

Cleanup eligibility/invalidation and no-delete-on-failure tests; retained metadata/audio tests; manual editor reopen/relink evidence; full required development checks for code changes.

## Comments

Specified from the user-approved interview on 2026-10-14. Implementation has not started. Readiness means specified; dependency completion is still required. Keep the current camera benchmark and earlier uncommitted work intact.

