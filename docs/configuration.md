# Experiment configuration

## Default: fixed settings within a wall-clock allowance

New `setup` defaults to `strategy: "fixed"`. See [quick comparison](quick-comparison.md) for five-second sections, explicit `fixed_settings`, selected/all encoders, work estimates, measured starting presets and hardware threading. `budget_minutes` includes initialization/scoring/review for this strategy. It does not tune quality or claim fresh validation. `setup --strategy tune` opts into the target-search behavior described below. Configurations without `strategy` retain legacy tuning semantics and cache identity.

`archivebench setup` now proposes a bounded **initial** comparison: at most two selected clips, one explicit format variant, up to three named encoders and four quality targets. Its default candidate list is CPU HEVC (`libx265`), CPU AV1 (`libsvtav1`) and GPU HEVC (`hevc_nvenc`); actual compatibility checks may fail. It never substitutes a supported format silently. Use `archivebench setup --comparison comprehensive` for wider coverage, and enter `all` at the encoder prompt to test every installed configured adapter.

The saved `comparison` field is `initial` or `comprehensive`. Older configs without it retain comprehensive behavior. Initial configs require explicit encoders and retain all selected clips and quality targets; over-wide requests are rejected with instructions to choose comprehensive. `initial_trial_limit` defaults to 12 and accepts 1..24 tuning attempts, including failed or interrupted attempts. Search quotas reserve work for other encoders/scenes; the total cap also covers shared-setting measurements across clips. Successful identical settings reuse cached evidence. A low cap can leave targets unmet or coverage incomplete; expanding requires an edited config and a new output folder. Fresh validation is separate, at most two shortlisted settings per target/variant on each saved validation section; shared choices are deduplicated.

Run `archivebench plan CONFIG.json` before encoding to inspect the exact footage intervals, format variants, encoder controls, quality targets, repeats, time allowance and work bounds. The listed adapter controls describe the supported rate/speed policy; this does not claim a search over other encoder speed presets or rate modes. Full measured encodes have an explicit bound; screens and short pilots are separate, and reference preparation/scoring/review generation add work. Scratch needs depend on the footage; the runner checks space before preparing lossless references.

One measured encode remains the default. `overnight` expresses willingness to spend encoding time for compression, not a hard finish deadline. Pilot estimates disclose startup and excluded work; unknown totals stay unknown. The budget begins after initialization and is not a guaranteed completion time.

Create a config with `archivebench setup`, then review it. Select named format variants to compare output policies in one run and report. Setup selects only Match source by default, and offers original-resolution 10-bit 4:2:0 and capped-1080p 8/10-bit 4:2:0 presets. Each combination is explicit. The displayed test count is an upper bound because compatibility checks and adaptive tuning can reduce the workload.

Edit the preset labels and choices in the saved `variants` list, or add supported combinations. For example:

```json
"variants": [
  {"id": "match-source", "label": "Match source", "pixel_format": "source", "resolution": "original"},
  {"id": "420-10-1080p", "label": "10-bit 4:2:0 capped 1080p", "pixel_format": "yuv420p10le", "resolution": "1080p"}
]
```

IDs must be unique lowercase names containing digits or hyphens. Variants contain only `id`, `label`, `pixel_format` and `resolution`. Audio and other stream retention choices apply to the whole experiment. Existing configs without `variants` remain one single-format experiment. When `variants` is present, its policies control encoding instead of the legacy top-level pixel format and resolution fields.

Match source resolves each clip separately. Mixed 4K 10-bit 4:2:2 and 1080p 8-bit 4:2:0 sources keep their respective dimensions, chroma, bit depth and frame rate while being re-encoded. Codec and bitrate may change. Unsupported source/encoder combinations are recorded under that variant; the tool never silently switches encoder or format. Measurements, cache identities and archive exports retain variant identity.

```json
{
  "version": 1,
  "profile": "compact",
  "mode": "quick",
  "encode_repeats": 1,
  "pixel_format": "source",
  "resolution": "original",
  "audio_mode": "copy",
  "drop_audio_tracks": [],
  "audio_kbps_per_channel": 192,
  "subtitles": "copy",
  "attachments": "copy",
  "metadata": "copy",
  "target_vmaf": 93,
  "tolerance": 0.5,
  "budget_minutes": 15,
  "samples": [
    {"path": "D:/Footage/example.mov", "label": "Motion example", "start": 10, "seconds": 6}
  ],
  "encoders": [],
  "quality_overrides": {}
}
```

- `profile`: compact/editing. Sample and format choices remain explicit. Setup offers quality levels 80,90,95,97; enter one score for a single-target experiment.
- `mode`: quick/thorough; determines finalist cap, tuning attempts and metric subsampling. It does not select timing repeats.
- `encode_repeats`: positive integer, default `1` in either mode. Each tuning and validation setting is encoded this many times to measure timing variability; the report uses the median. Set `2`, `3` or another positive integer only when repeated timing measurements are wanted. Extra repeats do not improve picture quality. Screening, short pilots, scoring and attempts at different quality settings are separate work. Older configs without this field now use one repeat; existing results keep their recorded timings. Changes to repeat count or runner code require a new run folder.
- `pixel_format`: `source` keeps each source's bit depth and chroma, or choose `yuv420p` (8-bit 4:2:0), `yuv420p10le` (10-bit 4:2:0), `yuv422p` (8-bit 4:2:2), or `yuv422p10le` (10-bit 4:2:2). Source formats outside those four require an explicit conversion choice. Incompatible encoders are reported as failed probes. Expanding bit depth or chroma cannot restore absent detail.
- `resolution`: `original` (default), `2160p`, `1440p`, `1080p` or `720p`. Caps fit within 3840×2160, 2560×1440, 1920×1080 or 1280×720, with the box rotated for portrait footage. Smaller sources are never enlarged. Lanczos scaling preserves display aspect ratio; reduced dimensions round down to even numbers. Frame rate stays unchanged. Scores compare candidates upscaled to the original dimensions against the original reference, so downscaling loss remains visible in scores.
- `audio_mode`: `copy` (default) keeps original audio without re-encoding, `aac` converts retained tracks, or `none` removes all audio in the archive. The benchmark itself remains video-only.
- `drop_audio_tracks`: one-based audio track numbers to omit, e.g. `[3, 4]`. Default `[]` keeps all tracks. This counts audio tracks, not FFmpeg's absolute stream indexes.
- `audio_kbps_per_channel`: AAC bitrate from 32 to 512, default 192. Used only with `audio_mode: "aac"`.
- `subtitles`, `attachments`: `copy` (default) or `drop`. Copy must be supported by MKV; incompatible streams fail the job rather than being silently discarded.
- `metadata`: `copy` (default) retains and checks user tags and chapters, or `drop` omits them. Container-generated technical tags can change; required attachment filename/MIME tags remain. Proprietary camera metadata and editor relinking are not guaranteed.
- `target_vmaf`: model-score target in (0,100], or the default report threshold when using multiple targets. If omitted with `target_vmafs`, the report starts at the highest target.
- `target_vmafs`: optional nonempty list of unique numeric scores in (0,100], e.g. `[80, 90, 95, 97]`. The runner searches these levels using shared measurements and references. When both fields are present, `target_vmaf` must belong to the list. Older configs with only `target_vmaf` remain single-target experiments. Setup defaults to four levels and one measured encode per setting. Adding targets adds distinct quality attempts, not timing repeats, and can require more time. It does not guarantee a near-target result: integer quality controls, bounded attempts, failures and time limits can leave a target unmet. The report never interpolates missing measurements.
- `tolerance`: allowed convergence distance above the target, 0–5. A score below the target never counts as meeting it. The search uses up to two attempts per target in quick mode or four in thorough mode, reusing the nearest measured setting and bracketing when available. Identical encoder/quality/sample/variant/stage measurements are cached across targets and resume.
- `budget_minutes`: positive per-invocation budget. Expensive preflight/hash work and process teardown can exceed wall-clock expectations. Individual encoder screens have a 30-second timeout.
- `samples`: existing local paths with start/seconds. Samples are at most 60 seconds. Start with 6-second quick or 20-second thorough sections. Use explicit labels safe to share.
- `encoders`: empty means all available configured adapters; otherwise a list of names from `doctor`.
- `quality_overrides`: optional starting quality by encoder, for example `{"libsvtav1": 35}`. This tunes initial quality; it is not a universal CRF equivalence.
- `ffmpeg`, `ffprobe`: optional executable paths. `doctor` and setup use PATH; benchmark honors these config paths.

Encoder controls and ranges live in `archivebench/encoders.py`. Changing them changes restart fingerprints. Advanced users/agents can add another adapter there with an explicit codec family, quality direction/range and tested FFmpeg arguments. Ordinary config is data, not shell commands.

The report's duration/target controls reinterpret saved measurements only. They do not run additional encodes. Exported version 2 archive settings contain the tested encoder/quality, video policy, measured dimensions/format, retention choices and benchmark identity. Audio and other streams are not included in benchmark measurements. Inspect samples before applying settings to another project; `source` can resolve to a different format there, which may be unsupported by the chosen encoder.

The chart-first report defaults to the whole collection. The runner tests each discovered encoder, quality control and variant policy on every prepared tuning sample within the budget. A configuration qualifies only when every planned tuning sample has a successful measurement meeting the target. Its displayed collection mean and low-5% scores are each the minimum across samples, and the report identifies the weakest scene. Missing, failed or unsupported samples prevent qualification. Single-sample exploration does not fill that coverage gap.

Selected-source video-only projections average the measured size and encoding-time rates within each source, multiply by that source's full duration, then sum distinct source files. Selecting multiple sections from one source does not count its full duration twice. The report starts with the selected sources' combined duration; changing the duration scales the same measured source mix. These are estimates, not guaranteed full-file totals. Older results without source duration and identity retain a labeled sample-duration extrapolation.

Tuning-qualified choices remain provisional pending fresh-footage validation. Archive exports record the canonical evidence status. Changing display thresholds cannot create measurements or validation evidence.

### Fresh-footage validation

Setup proposes one `validation_samples` section per source, twice its longest tuning section and capped at 60 seconds. Review or replace these saved intervals before running, ideally choosing a different scene. Every interval must fit the source and avoid every tuning interval for that source. If a source lacks enough footage, setup explains the gap and leaves the experiment provisional. Shorter explicit fresh sections are allowed after review.

`validation_reserve` defaults to `0.3`. All variants and stages share one time budget per invocation. Tuning stops at 70% of that allowance, and validation uses the remaining time. Preflight/tool checks and source hashing precede the timed work. An explicit resume starts a new invocation allowance; completed verified trials are reused.

The smallest and fastest tuning-qualified settings per target and variant form a deduplicated, frozen shortlist. Every candidate uses its exact encoder and quality on every fresh section, once regardless of how many targets selected it. Validation never tunes from those sections or changes encoder. Resume continues the frozen shortlist. Each candidate records the targets that selected it and a status for each. Passing a lower target does not imply passing a higher one. A scoring failure is failed evidence, a timeout or missing section is incomplete evidence, and only passing every required section produces validated evidence. Legacy results without holdouts remain provisional.

The quality-level comparison table shows the smallest validated collection choice at each saved target, its worst tuning/fresh sample means, projected video size and encoding time, and savings against the highest target's smallest validated choice. A target without validated coverage is labeled explicitly. Click a level to apply its threshold to existing charts and visual review. One setting may qualify at several levels. Exported archive evidence records that setting's lowest frozen validation target; display controls cannot invent evidence. The table does not certify future footage or visual acceptability.

Optional low-5% quality and projected encoding-time limits start blank. Changing them, the mean floor or the duration does not alter the saved experiment conclusion. Pin a measured configuration to compare another against that named baseline. Size/time comparisons require the same sample coverage. Decision-summary exports include active constraints, measured sample values, projections and self-reported visual-review status; archive-settings exports retain their existing schema.

New benchmarks save `vmaf_frames` with scored-frame timestamps relative to sample start. Reports use them for quality timelines and low-score seek shortcuts. Old runs without this data show an explicit unavailable state; rebuilding does not reconstruct measurements from logs or rerun encoding. The offline report embeds first-frame images. Validated finalists also receive generated companion stills and paired H.264 8-bit 4:2:0 MP4 previews, plus an exact measured MKV copy for native-player review. Keep the `review` folder beside the report for synchronized playback. Browser synchronization is approximate, and converted previews cannot certify preservation of source chroma or bit depth. Clips are not uploaded or embedded in exports. Review marks last for the browser session and do not authorize cleanup.

Existing version 1 archive settings/manifests retain their previous AAC/drop-tracks-3/4 behavior for restart and cleanup. New report exports default to copying all audio and retained streams, even when rebuilding a report from an older benchmark. The report displays this policy before export.

The legacy runner writes MKV; reusable jobs support explicit MKV/MOV/MP4 choices. Timecode preserve requires supported MOV/MP4 and verification, reject blocks timecoded inputs, and drop explicitly removes timecode. Unsupported data streams and cover art remain keep-original boundaries unless an explicit supported drop policy is selected. Copied audio/subtitle payloads and attachment contents are verified, alongside stream selection, dispositions, metadata, chapters, video, hashes, savings and full audio/video decode. Application-specific metadata and editor compatibility still need a separate test. Originals remain intact until a separate, explicit cleanup.
# Weak-moment visual review

## Portable archive presets

The report can export `archive-preset.json` alongside the legacy archive-settings export. A version 1 preset wraps exact settings, a measured tradeoff explanation, historical footage/hardware/toolchain scope, sample coverage and exclusions. It contains no project source/output roots. Saved hash-bound visual reviews are exported as section references with current or invalid status; browser visual marks do not become acceptance. Reviewed sections do not imply acceptance of unreviewed footage. Measured video-byte and encode-time rates support historical estimates; retained streams and verification remain excluded.

Terminal users can run `archivebench preset import archive-settings.json --output preset.json --name "HEVC CPU"`, `archivebench preset inspect preset.json`, and `archivebench preset export preset.json --output another-preset.json`. Existing outputs are not overwritten. `archive --settings preset.json --source INPUT --output OUTPUT` uses the same runner on any selected folder. Preset inspection accepts `--context observations.json` with actual `supported_encoders`, `supported_pixel_formats`, footage characteristics and optional `skip_sample_check`. Unsupported hardware/format and untested footage are reported separately. Observations and skipping a check never grant current-project validation.

Preset settings are bound to their saved evidence by a canonical settings fingerprint. Edited settings or encoder controls are rejected; create new evidence for new choices. This detects accidental changes, not forged evidence. Source-mode format controls are symbolic: the runner resolves each source's actual format. Existing version 1/2 settings and manifests retain their documented behavior. Legacy imports have unknown scope until new measurements exist.

Validated finalists receive paired PNG stills after scoring, within the remaining invocation budget. The report offers every measured tuning and validation sample for the selected settings. Stills select up to three scored frames at least one second apart. Sparse scores can supply fewer moments. Each pair uses the same decoded frame index and sample-relative time, including when scoring skips frames.

The originals and encodes retain their native image dimensions. Crop zoom and horizontal/vertical position use the same normalized region in each image. Enlarging a smaller output does not recover detail. RGB PNG display conversion and browser rendering cannot certify preservation of 4:2:2 chroma or 10-bit detail.

Keep the generated `review` folder beside `report.html` to use native-size stills. Missing assets leave the embedded first-frame previews available. Asset failures do not change metric validation. Resume with more time to finish assets. Sharing the companion folder reveals footage, so review its contents before sharing.

