# Archive completed projects from the terminal

For an interactive interface with clip selection, preset comparison and progress, use [the terminal UI](terminal-ui.md). This guide covers the command-line and scripted workflow.

The command and agent skill share one engine, preset format and job records. No agent or API key is needed here. Install the current revision using [installation](installation.md); the initial published 0.1.0 wheel may lack these commands. Check `archivebench --help`.

## Compare a small sample

```powershell
archivebench doctor
archivebench scan FOOTAGE_FOLDER
archivebench setup --config comparison.json
archivebench plan comparison.json
archivebench benchmark comparison.json --output comparison-run
archivebench status comparison-run
```

Inspect the saved configuration before running. Setup defaults to `strategy: "fixed"`, five-second sections, two settings per encoder, one timing repeat and a 30-minute wall-clock allowance. Select encoders or enter `all`. Scores are observed without target tuning; the first scene gives an early CPU/GPU comparison. The report lists coverage, unfinished work and estimates. Preserve source format/resolution and all audio unless you explicitly choose a transformation. Use `setup --strategy tune` for advanced target searches and fresh validation. See [quick comparison](quick-comparison.md). Changed experiments need a new output folder.

Open `comparison-run/report.html` beside its companion media. At your acceptable quality, compare fastest/smallest measured choices. VMAF is not a quality percentage or grading guarantee. Projections cover video only; actual archive savings include retained streams. Incomplete measurements cannot establish a recommendation.

## Review and save reusable settings

```powershell
archivebench review inspect --results comparison-run/results.json
archivebench review launch --results comparison-run/results.json --trial TRIAL_ID
```

The optional native viewer receives aligned exact files. Inspect movement, texture, noise and intended editing needs. It is silent; check audio separately. Browser previews are converted aids. Record only your actual decision using `review record` (see `--help`). Rejections can include objection timestamps. Regenerate the report with `archivebench report comparison-run/results.json` to include decisions.

Use **Export portable preset** in the report for exact settings, tested scope and evidence. Legacy **Export archive settings** remains available; import it with:

```powershell
archivebench preset import archive-settings.json --output preset.json --name "HEVC archive" --description "Reason for choosing these settings"
archivebench preset inspect preset.json
```

Legacy imports start with unknown/unreviewed evidence. A codec name alone cannot reproduce settings. On different footage, inspect scope with `--context observations.json` and consider a short confirmation comparison. Historical evidence is not current-project validation. Keeping originals is valid.

## Apply one preset to different folders

This is the everyday archival stage. Reuse the chosen preset without another benchmark; each folder receives its own job. Windows users can alternatively install the [Send to launcher](windows-send-to.md).

```powershell
archivebench job create project-a.json --source PROJECT_A --output ARCHIVE_A --preset preset.json --exceptions exceptions-a.json
archivebench job inspect project-a.json
archivebench job run project-a.json --execute
archivebench job create project-b.json --source PROJECT_B --output ARCHIVE_B --preset preset.json
archivebench job inspect project-b.json
archivebench job run project-b.json --execute
```

Omit exceptions when none are needed. A list such as `[{"path":"night/important.mov","action":"keep-original"}]` retains that file. See [archiving](archiving.md) for stronger-setting exceptions. Each job snapshots settings and has independent checkpoint state. Rerun the same job to resume; changed sources, outputs or settings are refused. Preflight identifies unsupported preservation cases and unknown estimates. Outputs must pass hash, format, stream, savings and decode checks.

## Review replacement before reclaiming space

```powershell
archivebench acceptance inspect --output ARCHIVE_A
archivebench cleanup --output ARCHIVE_A
```

After processing ends, inspect the mapping. Follow [replacement acceptance](editor-acceptance.md) to record either actual visual/editor decisions or explicit quality-tradeoff acceptance without inspection. Without current acceptance, cleanup preview lists zero eligible replacements; execution cannot bypass missing acceptance. Encoding success cannot supply job acceptance. Cleanup remains a separately requested operation, dry-run by default. Keep-original exceptions remain intact.

Current evidence covers Windows and the narrow synthetic Resolve path in that guide. Proprietary camera metadata, other NLEs, Log/HDR grading and physical 10-bit monitor fidelity are not certified.
## Immediate use and job outcomes

For a first project, a representative-footage comparison is recommended, or use a built-in starter immediately:

```powershell
archivebench preset list
archivebench preset export STARTER_PATH_FROM_LIST --output starter.json
archivebench job create project.json --source FOOTAGE_FOLDER --output EXTERNAL_OR_PROJECT_ARCHIVE --preset starter.json
archivebench job inspect project.json
archivebench job run project.json --execute
```

The list includes Quality priority, Balanced, Space priority and an explicit AVC alternative. These are unmeasured settings, not quality guarantees or measured size/time estimates. Preserve resolution, frame rate, bit depth and chroma by default; copy all audio tracks. Select format reductions or audio conversion explicitly. Technical incompatibility blocks that file; choose another compatible preset explicitly. If historical footage scope differs, a short comparison is optional; the TUI requires explicit acceptance of uncertain suitability.

Select video footage only: this workflow does not back up editing projects, graphics, music or sidecars. Destinations may be within the project, on an external drive or at an arbitrary path. Relative footage paths are retained; generated archives are excluded from discovery. Keep enough free space for originals and replacements. CRF/CQ output sizes are uncertain; historical estimates exclude retained streams and verification and cannot promise fit.

After a run, open `ARCHIVE_FOLDER/archive-summary.html` offline beside `archive-manifest.json`, the saved job and logs. It distinguishes verified, failed, kept-original, insufficient-saving and unfinished work. Replacement size reduction and potentially reclaimable original bytes are separate from net storage reclaimed after cleanup. Originals remain throughout encoding. The adjustable minimum-saving default is 10%.

Rerun the same job command to resume; verified matching files are reused and interrupted files restart from their beginning. The guided UI loads an existing destination job by default. Conflicting settings or selections require resolving the conflict or choosing another destination. Recoverable per-file failures retain affected originals and continue; job-wide storage failures stop safely. After an interrupted run, resolve unfinished work before cleanup.
