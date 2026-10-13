# Overnight archive helper for completed projects

Status: open
Readiness: needs-info
Blocked by: None

## What to consider later

The current archive runner already accepts exported benchmark settings, reviews eligible files and encodes a batch while preserving originals. Document that workflow in the initial release.

A future convenience helper could accept an Originals folder and exported settings, create an adjacent Archived folder, and launch/resume an overnight job. Confirm any additional scheduling, folder-selection and progress requirements before building another script. Reuse the existing runner and retain hashes, path boundaries, minimum savings, decode/stream checks and separate explicit cleanup.

## Comments

Recorded from the user's public-release request as an optional follow-up. It does not block publication and is not part of the current implementation scope.
