# ArchiveBench 0.2.0

Released 2026-10-16. This release packages the terminal UI, revised Windows Send to workflow, fixed comparisons and archive output controls. Install the [release wheel](https://github.com/Today20092/ArchiveBench/releases/tag/v0.2.0) or use a source checkout at `v0.2.0`. See [installation](installation.md).

## Terminal UI

`archivebench-tui` provides four steps, Clips, Settings, Review and Progress. It accepts folders, individual clips or a mixture, deduplicates overlaps, and keeps relative paths under a common source folder. Sources must share one drive; the destination can be elsewhere.

The preset table compares codec, CPU/GPU device, quality controls, color format and resolution. Settings includes the destination and audio policy, with container, timecode and other-data choices under Advanced. AAC bitrate is selectable per channel, with the stereo equivalent displayed. Preflight saves or loads the job and must succeed before Start becomes available.

The UI runs the shared archive engine in a worker and retains output beside the job in a log. Stop and exit request confirmation and wait for owned encoding work to stop safely. Resume checks completed files and restarts an interrupted file from its beginning. Changing a preset file does not rewrite a saved job's snapshot. Cleanup is outside the TUI.

The UI includes a scrollable preset table, selected-preset and review summaries, and fewer layout rebuilds on tab navigation. Background duration probes and historical per-preset encode estimates help plan jobs. Missing timing data stays visible, and estimates exclude audio processing and verification.

See [the TUI guide](terminal-ui.md).

## Windows Send to

Both **Archive footage** and **Archive footage (terminal)** now launch the TUI directly. Explorer supplies the selected source paths; the user chooses the output folder inside the application. The default host is the Windows console host. WezTerm is an explicit installer option and uses the user's existing configuration.

**Review originals for deletion** remains a separate legacy cleanup launcher with acceptance gates. The PowerShell installer's `-Legacy` mode restores the older desktop and numbered-prompt archive launchers. Installing the current tool and refreshing the shortcuts are separate steps. Existing shortcuts do not automatically become current just because checkout files changed.

See [installation and removal](windows-send-to.md).

## Archive engine and project selection

The shared selection code supports mixed folders/files, selected-file job snapshots and preserved relative paths. It excludes generated archives and proxies. The older `archivebench-desktop` selector remains available, but it is no longer the default Send to destination.

Jobs now support explicit MKV, MOV and MP4 output policies, audio copy/AAC/removal, selected dropped audio tracks, and timecode/data handling. Supported timecode preservation requires MOV or MP4. Compatibility checks reject unsupported combinations; a successful mux probe does not establish editor compatibility or preservation of proprietary metadata.

Selected jobs enable progress and continuation after individual file failures. Low disk space and identity conflicts still stop the batch. Source/output hashes, decode checks, retained-stream checks and actual savings remain part of verification. Encoding preserves originals; cleanup requires separate visual/editor acceptance and confirmation. Existing Proxy Watcher manifests are not imported. See [archive jobs](archiving.md), [the legacy desktop guide](archive-desktop.md) and [the Proxy Watcher comparison](proxy-watcher-comparison.md).

## Quick comparisons and reports

New setup defaults to a fixed comparison rather than a target-quality search. It saves short sections, two explicit settings per encoder, one timing repeat and a default 30-minute allowance. The queue compares encoders on the first scene before checking its measured frontier on additional scenes. The allowance includes preparation, scoring and report work; incomplete measurements remain visible. Explicit resume grants another allowance while reusing verified measurements.

Advanced `--strategy tune` remains available for target searches and fresh validation. Old configurations without a strategy retain tuning behavior. Fixed comparisons export measured starting presets without claiming fresh-validation coverage or visual approval.

Quick runs write the measurements report before detailed browser review. Deferred review is the default; `archivebench review prepare` generates assets for a selected trial under a separate allowance. Exact native review remains available. Report and preset handling distinguish fixed evidence from qualified target recommendations. Encoder threading and bounded scoring calibration also changed to use available hardware without an arbitrary SVT processor cap.

See [quick comparison and refinement](quick-comparison.md), [configuration](configuration.md) and [benchmark evidence](benchmark.md).

## Packaging and verification

The package now declares Textual as a runtime dependency and adds `archivebench-tui` and `archivebench-desktop` entry points alongside the CLI, skill installer and Send to installer. uv installs those dependencies; FFmpeg remains separate and Node is only needed for report development.

Release checks cover Python 3.11 tests, Ruff formatting/lint, ty type checking, report math/playback tests, synthetic tuning and fixed-comparison reports, offline browser/native-still checks, and installation of the built wheel. The public CI workflow repeats the source, report and package checks. Synthetic measurements test the workflow and do not recommend settings for camera footage.

The wheel and source distribution use version 0.2.0. Release assets include SHA-256 checksums and a synthetic report demo. Windows is the exercised platform; other platforms need their own runtime checks. FFmpeg is not bundled.

The optional skill supports one-time use through `npx skills use` and project or global installation through `npx skills add`. New installations use explicit invocation in Codex and Claude Code. Existing installed copies retain their old settings until updated. Live invocation in every client and interactive Explorer launch are not certified by the automated tests.

## Agent-guided workflow

The release also includes the shared CLI and portable skill workflow:

- Optional portable Agent Skills package and installer, using the shared terminal engine.
- Bounded initial experiment planning, explicit timing repeats and adaptive multi-quality comparisons with progress/evidence reporting.
- Explained portable presets with exact controls, historical footage/environment scope and separate visual evidence.
- Exact native comparison integration and durable user review decisions.
- Reusable job snapshots across folders with independent resume state and explicit exceptions.
- Replacement mappings and visual/editor attestations before separate new-job cleanup.

Follow [installation](installation.md) and the [terminal walkthrough](terminal-workflow.md). Installation does not configure global agent clients or perform cleanup automatically. Existing exported settings and legacy archive manifests retain their documented contracts; they are not retroactively editor-approved.

Windows is the tested platform. The editor evidence covers only the narrow synthetic DaVinci Resolve Studio 21.1.1.10 HEVC Main10 MOV-to-MKV path described in [editor acceptance](editor-acceptance.md). Other editors, camera metadata, Log/HDR grading, physical display fidelity and subjective audio acceptance remain unverified. Scores and a native viewer opening cannot establish human approval.

The delivery evaluation records named-client discovery and bounded model behavior; one synthetic comparison cannot establish universal benefit over an agent without the skill. The terminal interface requires no model/API key.
