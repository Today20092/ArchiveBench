# Running and interpreting a benchmark

[Back to the README](../README.md) · [Configuration](configuration.md) · [Archiving](archiving.md)

## Choose samples

Select short sections with motion, fine detail and dark or noisy footage. Similar clips add less information than varied scenes. Setup lists eligible clips and asks which to include; it does not infer scene diversity. Proxy and generated archive folders are excluded.

Use the saved configuration and canonical `results.json` as the experiment record. JSON, CSV and Markdown results accompany the HTML report. Report controls reinterpret saved measurements; they do not encode new candidates.

## Screening and tuning

Configured H.264, H.265, AV1 and VP9 encoders available in FFmpeg get a one-second compatibility/quality screen. Hardware encoders must actually encode the selected format. Unconfigured or failing implementations are reported.

| Mode | Finalists | Quality attempts per finalist per target | Timed encodes per attempt |
| --- | ---: | ---: | --- |
| Quick | Up to 4 | Up to 2 | `encode_repeats`, default 1 |
| Thorough | Up to 8 | Up to 4 | `encode_repeats`, default 1 |

Setup asks how many measured encodes to run per setting and saves `encode_repeats`. Choose 1 for one timing measurement, or 2, 3 or another positive integer to measure timing variability. The runner prints this count before measurements. It applies to both tuning and validation, and timing uses the median of the recorded values. Repeating an identical setting does not improve its picture quality. Short compatibility screens and pilots still run separately, and scoring takes additional time.

Compression tuning is different from repeating a timing measurement: it tries different compression settings toward the shared VMAF target. This compares size and speed at a chosen measured quality rather than treating unrelated encoder quality numbers as equivalent. One repeat still allows multiple quality attempts; it does not mean one encode for the whole experiment.

Screens favor near-target quality, then size and time. This heuristic can miss useful encoders; raw screen results are retained. A budget-limited run is a partial search, not proof that the best possible settings were found.

Each quality discovered during tuning becomes a shared candidate. Within the budget, the runner measures that exact encoder, quality and format variant across every prepared tuning sample. The report requires successful measurements meeting the target on every planned sample; averages cannot hide a weak scene. It shows the weakest scene and completed/required coverage. These choices remain provisional pending fresh-footage validation.

Setup offers VMAF 80, 90, 95 and 97, or a single/custom list. These are adjustable model-score targets, not guarantees of viewing quality or grading latitude. Identical measurements and references are reused across levels; additional levels can still add distinct quality attempts and validation candidates. The report compares measured size, quality and time at each level, with missing/unmet targets explicit. Quality-control values are not interchangeable between encoders. Recommend only measured settings that meet the target. Exact encoder commands are defined by the adapters described in the [configuration reference](configuration.md).

## Fresh-footage validation and visual review

Setup proposes separate, non-overlapping sections from each selected source for you to review. After tuning, the runner freezes the smallest and fastest qualifying candidates for each target and variant, deduplicates identical choices, and tests those exact settings on the fresh sections. A setting becomes validated at a target only after it meets that target on every required tuning and validation sample. Passing at 80 does not mean passing at 97. Failed, incomplete and provisional candidates stay visible with their evidence status.

Thirty percent of the budget is reserved for validation by default. Resuming an incomplete run continues the frozen shortlist; validation results never tune its settings. Raising the report's target checks the saved validation scores too.

The report includes matched native-size stills from up to three separated low-scoring moments. Use the crop and zoom controls to inspect detail. Companion playback provides shared play, pause and seek controls; synchronization is approximate in a browser. Playback previews are converted to H.264 8-bit 4:2:0 for compatibility. Review the exact encoded files before accepting color, editing or archive fidelity.

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

The HTML report includes results, embedded fallback previews and bundled TanStack Charts. It opens from disk without a server or network requests. Keep the adjacent `review/` folder with it for companion playback and native stills. Review labels and images before sharing; they may reveal project names or private footage. Raw `results.json` contains local paths. Share the redacted HTML and reviewed companion assets rather than raw results when those paths should remain private.
