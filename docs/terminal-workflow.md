# Archive completed projects from the terminal

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

Inspect the saved configuration before running. Start with `comparison: "initial"`, one representative tuning section and a separate fresh section, one or two compatible encoders, and `encode_repeats: 1`. Preserve source format/resolution and all audio unless you explicitly choose a transformation. The [configuration reference](configuration.md) explains limits, targets and retention. Plan exposes bounds and unknown estimates; budget is not a promised finish time. Screens/pilots add work. Changed experiments need a new output folder.

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

Review the mapping and archive, then reopen a separate editing-project copy using replacements. Follow [editor acceptance](editor-acceptance.md) to record actual visual/editor decisions. Without current acceptance, cleanup preview lists zero eligible replacements; execution cannot bypass missing acceptance. Encoding success cannot supply job acceptance. Cleanup remains a separately requested operation, dry-run by default. Keep-original exceptions remain intact.

Current evidence covers Windows and the narrow synthetic Resolve path in that guide. Proprietary camera metadata, other NLEs, Log/HDR grading and physical 10-bit monitor fidelity are not certified.
