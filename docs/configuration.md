# Experiment configuration

Create a config with `archivebench setup`, then review it. Each run uses one output policy. Use separate configs and run folders to compare policies. With `source`, each sample retains its own supported bit depth and chroma; compare recommendations within that sample.

```json
{
  "version": 1,
  "profile": "compact",
  "mode": "quick",
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

- `profile`: compact/editing. The wizard chooses suggested targets; explicit `target_vmaf` controls the experiment.
- `mode`: quick/thorough; determines finalist cap, tuning attempts, repeats and metric subsampling.
- `pixel_format`: `source` keeps each source's bit depth and chroma, or choose `yuv420p` (8-bit 4:2:0), `yuv420p10le` (10-bit 4:2:0), `yuv422p` (8-bit 4:2:2), or `yuv422p10le` (10-bit 4:2:2). Source formats outside those four require an explicit conversion choice. Incompatible encoders are reported as failed probes. Expanding bit depth or chroma cannot restore absent detail.
- `resolution`: `original` (default), `2160p`, `1440p`, `1080p` or `720p`. Caps fit within 3840×2160, 2560×1440, 1920×1080 or 1280×720, with the box rotated for portrait footage. Smaller sources are never enlarged. Lanczos scaling preserves display aspect ratio; reduced dimensions round down to even numbers. Frame rate stays unchanged. Scores compare candidates upscaled to the original dimensions against the original reference, so downscaling loss remains visible in scores.
- `audio_mode`: `copy` (default) keeps original audio without re-encoding, `aac` converts retained tracks, or `none` removes all audio in the archive. The benchmark itself remains video-only.
- `drop_audio_tracks`: one-based audio track numbers to omit, e.g. `[3, 4]`. Default `[]` keeps all tracks. This counts audio tracks, not FFmpeg's absolute stream indexes.
- `audio_kbps_per_channel`: AAC bitrate from 32 to 512, default 192. Used only with `audio_mode: "aac"`.
- `subtitles`, `attachments`: `copy` (default) or `drop`. Copy must be supported by MKV; incompatible streams fail the job rather than being silently discarded.
- `metadata`: `copy` (default) retains and checks user tags and chapters, or `drop` omits them. Container-generated technical tags can change; required attachment filename/MIME tags remain. Proprietary camera metadata and editor relinking are not guaranteed.
- `target_vmaf`: model-score target in (0,100]. `tolerance`: allowed convergence distance, 0–5. Being within tolerance below the target does not count as meeting it in the report.
- `budget_minutes`: positive per-invocation budget. Expensive preflight/hash work and process teardown can exceed wall-clock expectations. Individual encoder screens have a 30-second timeout.
- `samples`: existing local paths with start/seconds. Samples are at most 60 seconds. Start with 6-second quick or 20-second thorough sections. Use explicit labels safe to share.
- `encoders`: empty means all available configured adapters; otherwise a list of names from `doctor`.
- `quality_overrides`: optional starting quality by encoder, for example `{"libsvtav1": 35}`. This tunes initial quality; it is not a universal CRF equivalence.
- `ffmpeg`, `ffprobe`: optional executable paths. `doctor` and setup use PATH; benchmark honors these config paths.

Encoder controls and ranges live in `archivebench/encoders.py`. Changing them changes restart fingerprints. Advanced users/agents can add another adapter there with an explicit codec family, quality direction/range and tested FFmpeg arguments. Ordinary config is data, not shell commands.

The report's duration/target controls reinterpret saved measurements only. They do not run additional encodes. Exported version 2 archive settings contain the tested encoder/quality, video policy, measured dimensions/format, retention choices and benchmark identity. Audio and other streams are not included in benchmark measurements. Inspect samples before applying settings to another project; `source` can resolve to a different format there, which may be unsupported by the chosen encoder.

The chart-first report defaults to the whole collection. A configuration qualifies only when the exact encoder, quality control and resolution policy have measurements on every planned sample. Its displayed collection mean and low-5% scores are each the minimum across samples. Size and time projections weight the measured sample mix by duration; they are not guaranteed totals for a larger collection. Independently tuned per-sample settings may leave no fully measured collection choice. Single-sample exploration does not fill that coverage gap.

Optional low-5% quality and projected encoding-time limits start blank. Changing them, the mean floor or the duration does not alter the saved experiment conclusion. Pin a measured configuration to compare another against that named baseline. Size/time comparisons require the same sample coverage. Decision-summary exports include active constraints, measured sample values, projections and self-reported visual-review status; archive-settings exports retain their existing schema.

New benchmarks save `vmaf_frames` with scored-frame timestamps relative to sample start. Reports use them for quality timelines and low-score seek shortcuts. Old runs without this data show an explicit unavailable state; rebuilding does not reconstruct measurements from logs or rerun encoding. The offline report embeds first-frame images only. Optional synchronized playback uses matching trimmed sample clips chosen locally in the browser; clips are not uploaded or embedded in exports, and unsupported codecs need a native player. Review marks last for the browser session and do not authorize cleanup.

Existing version 1 archive settings/manifests retain their previous AAC/drop-tracks-3/4 behavior for restart and cleanup. New report exports default to copying all audio and retained streams, even when rebuilding a report from an older benchmark. The report displays this policy before export.

The runner writes MKV. Unsupported data streams and cover art stop a new archive job. Copied audio/subtitle payloads and attachment contents are verified, alongside stream selection, dispositions, metadata, chapters, video, hashes, savings and full audio/video decode. Application-specific metadata and editor compatibility still need a separate test. Originals remain intact until a separate, explicit cleanup.
