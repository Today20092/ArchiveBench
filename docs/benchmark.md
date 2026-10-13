# Running and interpreting a benchmark

[Back to the README](../README.md) · [Configuration](configuration.md) · [Archiving](archiving.md)

## Choose samples

Select short sections with motion, fine detail and dark or noisy footage. Similar clips add less information than varied scenes. Setup lists eligible clips and asks which to include; it does not infer scene diversity. Proxy and generated archive folders are excluded.

Use the saved configuration and canonical `results.json` as the experiment record. JSON, CSV and Markdown results accompany the HTML report. Report controls reinterpret saved measurements; they do not encode new candidates.

## Screening and tuning

Configured H.264, H.265, AV1 and VP9 encoders available in FFmpeg get a one-second compatibility/quality screen. Hardware encoders must actually encode the selected format. Unconfigured or failing implementations are reported.

| Mode | Finalists | Quality attempts per finalist | Timed encodes per attempt |
| --- | ---: | ---: | --- |
| Quick | Up to 4 | Up to 2 | One |
| Thorough | Up to 8 | Up to 4 | Three; report the median |

Screens favor near-target quality, then size and time. This heuristic can miss useful encoders; raw screen results are retained. A budget-limited run is a partial search, not proof that the best possible settings were found.

Each quality discovered during tuning becomes a shared candidate. Within the budget, the runner measures that exact encoder, quality and format variant across every prepared tuning sample. The report requires successful measurements meeting the target on every planned sample; averages cannot hide a weak scene. It shows the weakest scene and completed/required coverage. These choices remain provisional pending fresh-footage validation.

Compact starts at VMAF 93 and Editing at 96. These are adjustable model-score targets, not guarantees of viewing quality or grading latitude. Quality-control values are not interchangeable between encoders. Recommend only measured settings that meet the target. Exact encoder commands are defined by the adapters described in the [configuration reference](configuration.md).

## Scoring and projections

VMAF is a model score, not a percentage of original quality. SSIM provides another comparison against the reference. Review motion and detail in the saved clips at native size before accepting a setting.

Scores use original-resolution VMAF, with `vmaf_4k_v0.6.1` at source widths of 3840 or more and `vmaf_v0.6.1` otherwise. Reduced-resolution candidates are upscaled against the original reference for scoring, so downscaling loss remains part of the comparison. Quick mode scores every second frame for VMAF; Thorough scores every frame. Frame counts are checked and timestamps aligned by frame index.

Reference chroma is converted to the requested output format. Scores therefore do not measure all color-detail loss when converting original 4:2:2 footage to 4:2:0. Use named format variants within one experiment to compare format or resolution choices.

Benchmark encodes are video-only. Timing includes decoding, scaling, encoding and disk I/O. It excludes scoring, hashing, previews and archive verification. Duration projections are linear estimates; they exclude audio and other retained streams. Source complexity, machine load, drivers and encoder builds can change actual size and time. Stable trial order, warm-up probes and repeated timings do not eliminate thermal or system-load bias.

Full-source projections average measured rates within each distinct source, then multiply by its full duration and sum the sources. Multiple sections from one file contribute to its average without counting that file twice. The report starts with the selected sources' total duration; the duration control scales that source mix. Older results without full durations retain labeled sample-duration extrapolation. See the [configuration reference](configuration.md) for evidence and export labels.

HDR, interlaced and variable-frame-rate sources are rejected. Supported format choices are listed in the [configuration reference](configuration.md).

## Restart and budgets

Rerun the same benchmark command to resume. Successful trials and screening outputs are hashed and reused. Source content, offsets, settings, runner/adapter code, environment and FFmpeg/ffprobe fingerprints bind the cache. Changes require a new output folder. Interrupted trials restart; completed trials remain.

The time budget applies per invocation, including encoding, scoring and reference creation. Source hashing, preflight and process teardown can add wall-clock time. Repeated invocations can continue a budget-limited experiment. Screen timeouts are recorded as failures.

Only one process may use a run or archive folder at a time. A `.lock` file records the process ID. After an abrupt shutdown, remove it only after checking that the recorded process is no longer running.

## Share a report

The HTML report includes results, previews and bundled TanStack Charts. It opens from disk without a server or network requests. Review labels and images before sharing; they may reveal project names or private footage. Raw `results.json` contains local paths. Share the redacted HTML rather than raw results when those paths should remain private.
