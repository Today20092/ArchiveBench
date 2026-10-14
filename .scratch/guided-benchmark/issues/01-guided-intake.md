# Guide benchmark setup and explain coverage

Status: done
Blocked by: none

Scope: AGENTS.md pointer and docs/agent-workflow.md. Implement the accepted guided intake and coverage/report criteria.

Acceptance: all topics in ../spec.md are represented with observable completion criteria; prior decisions are reused; runtime and sample duration remain separate; existing data preservation and fresh-validation requirements survive.

Required checks: diff review, local link resolution, intake-topic and safety-rule checks. No executable source changes.

## Comments

Initial implementation expands the existing workflow rather than adding a second instruction source. The rerun is separate operational work.

Verified: git diff --check passed; every intake topic, coverage safeguard and AGENTS.md entry point passed the content check; every relative workflow link resolves. Reviewed the diff against the accepted scope and retained source-preservation, fresh-validation and separate-cleanup requirements. No executable source changes, so code tests were not needed for this documentation edit.

User follow-up: ask about a live progress view, explain screening/tuning/validation before launch, distinguish automatic timeout limits from manual cancellation, and request authorization before manually stopping an individual render unless immediate safety requires it. Added to the same workflow; no progress UI was implemented or promised. Diff whitespace check passed after the addition.
