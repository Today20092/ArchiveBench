# Benchmark comparisons and validation

Status: approved for implementation

## Requested scope

- Compare multiple chroma/bit-depth/resolution choices in one experiment and report.
- Improve visual review with synchronized playback, full-resolution crops and weak-moment previews.
- Recommend settings across selected samples.
- Validate shortlisted settings on fresh footage not used for tuning.
- Use AGENTS.md and local Markdown tickets for the workflow.

## Accepted decisions

- Users select named, editable format combinations. Show the test count before running instead of silently expanding a Cartesian product.
- A project recommendation uses identical settings across all selected samples and meets the target on every sample. Failed or missing samples make the evidence incomplete; averages cannot hide failures.
- Keep the shareable HTML lightweight. Optional companion media provides synchronized browser-compatible previews and exact benchmark clips. Label converted previews explicitly.
- Propose non-overlapping validation sections for user review before starting. Keep them out of tuning; insufficient footage makes validation incomplete.
- Use one total budget with a visible validation reserve. Results remain provisional if validation is incomplete.
- Use the default triage labels alongside separate implementation progress statuses.
- Offer editable presets: Match source (default selected), original-resolution 10-bit 4:2:0, capped-1080p 10-bit 4:2:0, and capped-1080p 8-bit 4:2:0. Permit additional supported combinations. Explain that increasing bit depth cannot recover detail.
- Match source preserves each clip's resolution, chroma, bit depth and frame rate, including mixed-source projects. It re-encodes video and does not require the source codec or bitrate. Encoder/quality settings remain shared across samples for a candidate; unsupported sources prevent it from qualifying. Never silently switch encoders or reduce source chroma.
- Validate the smallest and fastest tuning-qualified candidates per variant, deduplicated. Do not automatically lower the quality target when none qualifies.
- Validation never tunes a candidate. Failed candidates stay failed; only another successfully validated candidate can be recommended. Further tuning requires a new experiment.
- Propose one fresh section per selected source, preferably from another scene, at twice the tuning duration capped at 60 seconds. Reserve 30% of the total budget. Missing coverage or time means incomplete validation.
- After validation, generate synchronized full-sample review previews and full-resolution still pairs from three separated low-scoring moments for each validated finalist/sample. Allow user-controlled crops/zoom. Use the remaining budget; missing review assets do not erase completed validation evidence.
- Weight project storage/time estimates by each selected source's full duration, averaging multiple tuning sections within that source. Estimates cover only selected source files. Every required sample must pass quality regardless of duration weight.
- Label browser-converted playback as review previews, show conversion details, and provide exact encoded files for external playback. Full-resolution stills aid detail review but cannot certify original 10-bit or 4:2:2 fidelity in the browser.

## Review artifacts

[Specification](spec.md) and five draft tickets in [issues](issues/) record the design. Confirm the testing approach and ticket breakdown before marking tickets ready for implementation.

The user authorized the complete spec and ticket breakdown by invoking implement-spec. Work the dependency graph and record verification on each ticket.
