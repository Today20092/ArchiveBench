# Delivery evidence and remaining limits

Evaluation on Windows, 2026-10-14, used an installed local wheel outside the checkout and synthetic media only. The public interface is shared by the skill and terminal route. No camera originals were touched, no cleanup was executed, and no release was published.

## Observed checks

| Check | Actual result |
|---|---|
| Fresh wheel and skill installation outside checkout | Command/help/doctor available; all skill references resolved; overwrite refusal preserved the existing installation. |
| Codex CLI 0.154.0 discovery | Its app-server `skills/list` discovered the actual packaged project-local `archivebench` skill, enabled, with no discovery errors. |
| Two terminal folder jobs | The same unreviewed H.264 preset encoded synthetic 320×180 and 640×360 FFV1/PCM footage into independent verified jobs; each honored a keep-original exception. |
| Resume and preservation | Repeating jobs left completed output modification times unchanged; source hashes stayed unchanged. |
| Scope and cleanup | Different-footage inspection reported untested scope; unknown preset quality remained unknown. Without human visual/editor acceptance, cleanup preview listed zero eligible replacements. No approval was invented. |
| Native viewer/editor | Exact synthetic native comparison and narrow Resolve reopening were demonstrated; see [installation](installation.md#optional-native-visual-review) and [editor acceptance](editor-acceptance.md). |

## Actual with/without-skill model attempts

Two independent directories received byte-identical 128×72, four-second FFV1 fixtures, the same installed CLI, public documentation, experiment, provisional preset, mismatch context, keep-original exception and invalid-media case. Only the skill arm installed the shipped skill through its installer. Both received an identical neutral archival prompt, one encoder/repeat/tuning attempt and a 0.5-minute benchmark budget. An external supervisor capped each owned process tree at 180 seconds. No model or reasoning override, auth-file copying, global configuration modification or CODEX_HOME change was used.

| Arm | Wall time | Exit | Product commands/encodes |
|---|---:|---:|---:|
| Without ArchiveBench skill | 11.64 s | 1 | 0 / 0 |
| Installed ArchiveBench skill | 11.62 s | 1 | 0 / 0 |

Both failed before a model task could execute: the inherited configured `gpt-6.1-sol` was rejected as unsupported for this CLI's ChatGPT account. Inherited MCP configuration also produced startup authorization warnings. The test did not inspect credentials or retry a different model. There were no generated experiment results, reproducible agent-chosen settings, agent review decisions or observed clarifications to grade. Token usage was unavailable. Source hashes stayed identical.

These first failures establish a local account/model limitation, not skill usefulness. The retries below used the client's advertised default equally in both arms through invocation-local settings; no global configuration changed. Inherited skills/hooks/MCP settings remain comparison confounds.

## Client-default retries and writable scratch

The client's `model/list` reported `gpt-6-astra` as default. A second fresh pair selected it explicitly in both arms for the same neutral three-case task. Both executed the unchanged experiment: one successful screen, one tuning trial and one fresh-validation trial, libx264 CRF 23, one timing repeat. Both created a separate reuse job, recognized untested footage scope and retained its keep-original exception. Neither fabricated approval or changed format. Both stopped on workspace-write denial of system temporary storage during preflight: a scratch capability error, not encoder incompatibility. Neither completed preset export or unsupported-media inspection in this pair.

| Arm | Wall time | Exit | Observed outcome |
|---|---:|---:|---|
| Baseline, client default | 157.50 s | 0 | Partial task; stopped on scratch failure. |
| Installed skill, client default | 127.64 s | 0 | Partial task; stopped on the same failure. |

The skill implicitly read installed SKILL.md. A mistaken status-file-path example caused an additional missing-file result in this arm; shipped instructions were corrected to `archivebench status OUTPUT_FOLDER`. Saved artifacts and commands establish partial completion, regardless of successful process exit.

A third pair used fresh identical workspaces, the same advertised default and process-local TMP/TEMP pointing to owned writable scratch. It retained all three cases but requested concise inspection/output within 180 seconds. Both produced two scored trials, exact CRF 23 provisional presets, independent reuse jobs with keep-original exceptions, scope inspection and actual broken-media job inspection. Invalid media retained originals. Valid-media preflight still encountered Windows scratch permissions; job preparation is not successful compatibility validation. Both presets stayed visually unreviewed; the skill bound validated synthetic metric evidence, while baseline retained unknown imported measurement status. Neither expanded benchmark work, executed an archive, cleaned up or launched native apps in the paired task.

| Arm | Wall time | Exit | Actual completion |
|---|---:|---:|---|
| Baseline, owned scratch | 180.38 s | Timeout | Command/artifacts existed; findings document and final turn incomplete. |
| Installed skill, owned scratch | 167.38 s | 0 | Commands, artifacts and findings completed. |

Both completed ten command batches. Baseline timeout prevented final token telemetry; skill reported 359,641 input tokens, 322,688 cached input tokens and 3,377 output tokens. Earlier completed-pair events reported baseline 408,170 input/348,672 cached/3,313 output versus skill 247,369/200,960/2,815. These include inherited context and are not portable task-cost estimates. Fixture hashes stayed unchanged, no clarification was requested, and no cleanup execution or false human approval occurred.

Canonical records establish one screen and two full timed measurements per arm. Total FFmpeg encoding subprocesses, including pilots and review conversions, were not instrumented and remain unknown; two trial rows are not two total encodes.

Observed skill contributions were implicit routing, evidence in the provisional preset, and completing findings within this one cap. Baseline performed equivalent bounded measurements and preservation decisions. This does not prove universal superiority, statistically reliable speed/cost benefit or camera/editor quality. Other clients remain untested.

A separate explicit `$archivebench` execution smoke requested synthetic job execution, resume, manifest verification and cleanup preview. It exited in 79.72 seconds after stopping on the same WinError 5 while creating an owned scratch preflight directory. No full job execution, resume or acceptance/cleanup command occurred; source hashes remained intact. Successful terminal job execution outside the client sandbox is separate evidence and cannot fill this agent-execution gap. Do not interpret a process exit of zero as complete archival execution.

## Repeatable evaluation recipe

### Resolved restricted-client execution check

After replacing private temporary-directory permissions with a unique job-owned scratch folder that inherits its output ancestor's permissions, actual restricted Codex CLI execution passed. Filesystem and timeout failures now stop visibly instead of declaring valid footage unsupported. Scratch paths are bounded and checked before removal; no ACL grant or sandbox bypass was used.

The first fixed-wheel explicit skill run completed in 115.81 seconds. Actual command events and the manifest showed one full synthetic archive encode, a verified output with 78.4% savings, and a second run skipping that completed output. Source and output hashes and output modification time remained unchanged; the keep-original exception survived. Acceptance inspection had no human attestations and cleanup preview listed zero eligible replacements. Short compatibility probes still run during resume and are separate from full encodes.

A second installed-wheel restricted-client check completed in 104.55 seconds and verified the resume/acceptance/cleanup-preview path again. These pipeline checks resolve the earlier execution blocker; they do not establish visual acceptance, real-camera quality or broad skill superiority. The earlier failed attempts remain historical evidence. A later redundant confirmation attempt was stopped during coordination and is not counted as a completed check. Matching and mismatched footage scope, normalized frame rate, measured estimates and review references are additionally covered at the actual report-export/job boundary.

Use two fresh unrelated directories and install the same wheel/toolchain in both. Give both identical synthetic inputs and shipped CLI documentation, with the actual installed skill only in one arm. Inventory discovered skills; disable any global ArchiveBench copy only through invocation-local settings in the baseline. Use the same neutral request covering fresh setup, reuse on changed footage and unsupported preservation, or separate those cases when a working client/model is available. Keep an explicit `$archivebench` trial separately labeled from implicit activation.

Bound owned process trees, retain actual commands/exits/canonical artifacts and fixture hashes, and grade scope disclosure, measured repeats/encoder work, truthful evidence, exact settings, exceptions and preservation. Do not grade self-reported success as evidence. Record failed attempts, missing metrics and inherited configuration. A successful keep-original recommendation can be correct. Run more repetitions before making broad benefit claims; one pair is only a smoke comparison.

Public client behavior references: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode), and the [Agent Skills format](https://agentskills.io/specification). Local CLI help was also checked rather than assuming historical flags.
