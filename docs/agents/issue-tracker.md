# Local issue tracker

Track work in Markdown under `.scratch/<feature>/`. Local files are the issue tracker; creating tickets does not publish anything externally.

- Keep the agreed specification in `spec.md`.
- Keep interview decisions and unresolved questions in `design.md`. Mark proposals as unresolved until the user settles them.
- Create one implementation ticket per file at `issues/NN-description.md`, numbered from `01`.
- Each ticket includes `Status:`, `Blocked by:`, scope, acceptance criteria and required checks. Make it understandable without chat history.
- Use implementation statuses `open`, `in-progress`, `blocked` and `done`. Start a ticket only after its listed blockers are done.
- Append work notes and verification results under `## Comments`. Mark done only when acceptance criteria and required checks pass.

Finish the design interview and record the user's confirmation before treating the spec or implementation tickets as ready. Keep private footage paths and raw results out of tracked planning documents.
