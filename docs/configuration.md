# Experiment configuration

Create a config with `archivebench setup`, then review it. Each run compares one common output format.

```json
{
  "version": 1,
  "profile": "compact",
  "mode": "quick",
  "pixel_format": "yuv420p10le",
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
- `pixel_format`: yuv420p, yuv420p10le or yuv422p10le. Incompatible encoders are reported as failed probes. Bit-depth expansion cannot restore detail absent from the source.
- `target_vmaf`: model-score target in (0,100]. `tolerance`: allowed convergence distance, 0–5. Being within tolerance below the target does not count as meeting it in the report.
- `budget_minutes`: positive per-invocation budget. Expensive preflight/hash work and process teardown can exceed wall-clock expectations. Individual encoder screens have a 30-second timeout.
- `samples`: existing local paths with start/seconds. Samples are at most 60 seconds. Start with 6-second quick or 20-second thorough sections. Use explicit labels safe to share.
- `encoders`: empty means all available configured adapters; otherwise a list of names from `doctor`.
- `quality_overrides`: optional starting quality by encoder, for example `{"libsvtav1": 35}`. This tunes initial quality; it is not a universal CRF equivalence.
- `ffmpeg`, `ffprobe`: optional executable paths. `doctor` and setup use PATH; benchmark honors these config paths.

Encoder controls and ranges live in `archivebench/encoders.py`. Changing them changes restart fingerprints. Advanced users/agents can add another adapter there with an explicit codec family, quality direction/range and tested FFmpeg arguments. Ordinary config is data, not shell commands.

The report's duration/target controls reinterpret saved measurements only. They do not run additional encodes. Exported archive settings contain one exact tested encoder/quality/format plus the benchmark identity; inspect the sample before applying those settings to a different project.
