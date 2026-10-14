# Integration review

Reviewed `7491a64327d6f6a86730d0f3c4e8eca5ed34add7...ff4536d` with independent Standards and Spec reviewers. Findings remain separate by axis. One final implementer handles all corrections, including the observed restricted-client preflight failure.

## Standards

1. **P2: Distinguish a saved running checkpoint from an active process.** `archivebench/cli.py:286–303` prints saved progress or results status without qualification; `archivebench/core.py:445–501` writes running without an observation timestamp or liveness evidence. Abrupt termination therefore leaves status reporting running indefinitely. `AGENTS.md` requires labeling incomplete evidence and using canonical results as experiment truth. Report checkpoint state and current activity separately, preserving counters; explicit unknown activity is sufficient.
2. **P3: Add settled domain terms to the glossary.** Preset, job, historical scope, visual attestation and replacement acceptance were introduced without updating `GLOSSARY.md`. `docs/agents/domain.md` requires definitions as terms are settled; ticket 07 also requires glossary consistency. Distinguish portable settings/evidence, local execution records and human acceptance from automated verification.

No additional actionable code-smell finding. Existing dictionary shapes and CLI dispatch follow repository conventions; separate preflight and full verification duties do not require another abstraction. Tool-enforced formatting and type checks were excluded from review findings.

## Spec

1. **P1: Portable presets lose visual-review evidence and tested toolchain.** The specification requires “tested hardware/toolchain and footage scope, and references to measured and visual-review evidence.” `report/math.js:130–137` exports only platform/CPU/GPU and hardcodes unreviewed without review references. `archivebench/report.py:74–89` displays saved reviews separately without placing them in the export payload. Measured exports need scoped bound references and toolchain identity; visual acceptance must remain separate from metric validation.
2. **P2: Measured exports cannot yield archive estimates.** The specification says “Estimates use measured rates” and requires source mix/coverage. `report/math.js:136–137` lacks numeric rates and uses a basis incompatible with `archivebench/jobs.py:234–249`, which expects measured video bytes and encoding seconds per source second. Align the producer/consumer contract and test actual report exports at the job boundary.
3. **P2: Jobs omit footage-scope mismatch inspection.** The specification requires “Preset scope mismatches … are visible.” `archivebench/jobs.py:155–164` resolves settings without comparing actual probed footage to the preset scope. A manually supplied context can expose differences through preset inspection, but job preflight must identify actual per-file mismatches and confirmation-check decisions without changing historical evidence.

No unsolicited feature scope found. Restricted-client scratch permissions remain a separately observed delivery blocker.

Summary: Standards 2 findings, worst stale activity reporting; Spec 3 findings, worst missing bound preset review/toolchain evidence.

## Resolution

All five findings were fixed by the single final implementer in `eca3ec4` and `34df0c3`, merged as `a0e303f`. Follow-up review caught and then confirmed correction of equivalent frame-rate scope values (`30` versus `30/1`). Scoped visual references and toolchain identity remain separate from metric qualification; producer/consumer rates and per-file scope have actual report-export/job boundary tests. Saved status explicitly reports unknown live activity. The glossary is updated.

The observed restricted-client scratch failure was also resolved without ACL grants or bypassing its sandbox; operational errors stop visibly instead of being labeled format incompatibility. Actual agent encoding/resume and independent hash checks passed. Scratch cleanup revalidates the bounded nonce path and resolved identity before removal; follow-up source review found no concrete boundary regression.

Combined checks passed: 77 Python tests, Ruff format/check, ty, 16 report math tests, 2 playback tests, rebuilt bundled JavaScript, fresh synthetic benchmark, offline browser, native stills and package builds. Final wheel matched the isolated installed package used for inspection. Reviews and synthetic checks do not certify subjective camera quality, broader editor compatibility or authorize deletion.
