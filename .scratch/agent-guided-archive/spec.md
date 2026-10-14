# Agent-guided archive workflow

Status: approved for implementation.
Confirmed by the user on 2026-10-14 after the design interview; implementation explicitly authorized by invoking implement-spec. The running benchmark remains isolated from implementation changes.

The approved public test boundaries are CLI commands, portable preset/job files, report exports/review records and observable verified archive outputs. Tests exercise those boundaries and the legacy regression paths named in the tickets.

## Purpose

Help editors, videographers and creators replace completed projects' camera media with smaller, visually accepted media that remains usable for their intended future editing. A successful decision may keep some or all originals when replacement is not worthwhile.

The user needs to answer: how much space does this save, how long will it take, and can I accept the change to my footage?

## Two entry points, one implementation

- An installable agent skill guides discovery, bounded experiments, interpretation, visual acceptance, preset creation and archive execution.
- Package the skill using the open [Agent Skills specification](https://agentskills.io/specification). Keep client installation/discovery instructions separate from the portable workflow. Format support alone does not guarantee access to local files, terminal execution, FFmpeg, GPU hardware or a native viewer.
- A standalone terminal interface supports the same decisions and operations without an agent or API key. Existing ArchiveBench commands are the reusable script foundation.
- Both use the same preset format, experiment engine, review evidence, archive runner and job records. Optional launcher scripts invoke that engine; they do not duplicate FFmpeg command construction or verification.
- Locate installed dependencies first. Explain and arrange missing tools as needed within the user's installation authorization. Document manual installation for terminal users and agents without installation access. Keep footage local.

## Agreed workflow

1. Inspect footage and actual CPU/GPU capabilities. Identify representative motion, texture and noise, supported formats, audio/metadata requirements, and the intended editing application.
2. Inspect existing presets. A preset from similar footage is a starting point; suggest a short confirmation check when a new project differs. Record an explicit user decision to skip that check and retain the distinction between old evidence and current-project evidence.
3. Propose a small experiment with sources, intervals, encoder/rate-control choices, format policy, measured repeat count, time allowance, scratch needs and expected output. Expand only to answer a remaining decision. Honor an explicit request for wider coverage or a different budget. Default to one measured encode per distinct setting.
4. Show actual samples and savings so the user can decide acceptable quality. VMAF supports search and screening; users need not choose a score before seeing footage. Additional accepted quality levels can produce additional presets.
5. At each accepted quality level, compare measured storage and encoding time, including Pareto choices. Explain codec, encoder, hardware and rate-control settings. Distinguish quality changes and format transformations; do not invent additive percentages attributing savings to codec or encoding speed.
6. Validate promising fixed settings on fresh footage. Keep incomplete, failed and provisional results visible. A user's visual acceptance and metric validation are separate evidence.
7. Save explained presets. Apply one project preset by default, with explicitly listed exceptions for stronger settings or keeping originals.
8. Run a reusable, resumable archive job on the selected folder. Record actual savings and verification results. A different project uses its own job record without modifying the preset's historical evidence.
9. Confirm visual acceptance and that the editing project reopens and reconnects to the replacement media. Only a separate explicit cleanup operation can delete the corresponding verified originals.

## Preset and job boundaries

**Archive preset:** portable, versioned exact encoder/rate-control settings, video/retention policy, a human explanation, tested hardware/toolchain and footage scope, and references to measured and visual-review evidence. Display names can lead with HEVC/H.265 or AV1 and the encoder/hardware. Codec names alone are insufficient settings.

**Archive job:** source and destination roots, a selected preset snapshot, explicit per-file exceptions, source/output mapping, checkpoint state, verification and acceptance records. Paths belong to the local job, not the reusable preset. Preserve compatibility with existing archive-settings exports and manifests.

**Preset scope:** tested footage characteristics and environment. Hardware compatibility, similar footage, measured quality and visual acceptance are distinct checks. A preset does not guarantee untested footage or another editor/hardware configuration.

**Replacement acceptance:** automated verification plus the user's visual review and recorded editor reopening/relinking confirmation, tied to the specific job outputs. New or changed files invalidate the corresponding acceptance. A playback check alone cannot certify an editing project.

## Policies

- Preserve dimensions, frame rate, bit depth and all audio by default. Offer chroma reduction or other transformations as separately named, explicit choices. Explain unsupported formats instead of silently adapting them.
- Quality tolerance and encoding patience are independent choices. 'Overnight' means willingness to spend more time for better compression, not a hard completion deadline. Estimates use measured rates and disclose uncertainty and excluded work.
- Show video-only benchmark projections separately from actual archive totals including retained streams. Report the source mix and coverage behind estimates.
- Keep file/path, hash, stream-retention, savings and decode checks. Review how timecode, proprietary metadata, sidecars and container compatibility affect replacement; unsupported cases retain originals.
- Cleanup remains dry-run by default and separately authorized. Never equate a metric pass or completed encode with permission to delete.
- Current Windows support is the first delivery scope. Do not advertise other platforms or editor workflows as tested without evidence.

## Delivery acceptance

- An agent can use an installed skill outside this repository; references and companion tools resolve without private paths.
- A terminal-only user can inspect dependencies, run a bounded comparison, visually review candidates, save/select a preset, and archive two different folders with independent resumable jobs.
- Both routes produce equivalent settings and verification for equivalent inputs, with no hidden agent-only state.
- Evaluate representative tasks with and without the skill using the same underlying tools and environment. Demonstrate improved decision completeness and reproducibility; measure unnecessary encodes and user effort rather than assuming the skill is beneficial.
- A mixed project can use one preset and an explicit keep-original exception without accidentally encoding or deleting that exception.
- Preset scope mismatches, failed probes, unmet quality targets, budget exhaustion and unknown estimates are visible.
- The report supports informed quality/size/time choices; visual acceptance is recorded separately from objective metrics.
- A supported editor reopening workflow is demonstrated. Other editors/formats remain explicitly unverified.
- Existing presets/settings, single-target experiments, archive manifests and original-preservation checks have regression coverage.

## Outside the first delivery

A new standalone GUI, cloud processing, automatic editor integrations for every NLE, universal camera presets, an exhaustive search by default, automatic deletion, automatic scheduling and a second independent encoder implementation.
