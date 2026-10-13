# Format comparisons, project recommendations and visual review

Status: approved for implementation

## Problem statement

Users currently need separate runs to compare output formats. Recommendations apply to individual samples, so a setting that works on one scene can fail elsewhere. First-frame previews miss motion artifacts and brief quality drops. Users need one report that compares format choices, recommends settings supported by all selected footage, and distinguishes tuning results from fresh-footage validation.

## Solution

Run named format variants within one saved experiment. Match source is the default and preserves each clip's resolution, chroma, bit depth and frame rate while re-encoding it. Compare shared encoder settings across all tuning samples, validate finalists on reserved fresh sections, and provide honest project estimates and visual review aids. Keep the offline HTML independently usable; larger playback assets live in an optional companion folder.

## User stories

1. As a user, I want named format variants so I can compare specific output choices without manually combining independent runs.
2. As a user, I want Match source to preserve each clip's format so a mixed project keeps 4K/4:2:2 and 1080p/4:2:0 footage in their respective formats.
3. As a user, I want an editable preset list and projected test count before running so I understand the workload.
4. As a user, I want failed compatibility probes associated with their variant and source so unsupported output is visible.
5. As a user, I want the same encoder and quality setting tested on every tuning sample so project recommendations are reproducible.
6. As a user, I want every required sample to meet my target so a strong average cannot hide a weak scene.
7. As a user, I want source-duration-weighted estimates so short and long source files contribute appropriately.
8. As a user, I want to review proposed fresh validation sections before running so I can choose different scenes.
9. As a user, I want validation footage excluded from tuning so it supplies independent evidence.
10. As a user, I want one budget with a visible validation reserve so tuning cannot silently spend all available time.
11. As a user, I want failed and incomplete validation distinguished from success so a provisional candidate is not presented as validated.
12. As a user, I want synchronized playback to compare motion at the same sample-relative time.
13. As a user, I want full-resolution still pairs from low-scoring moments and selectable crops so I can inspect localized artifacts.
14. As a user, I want converted previews clearly identified and access to exact clips so browser compatibility does not misrepresent measured output.
15. As a user, I want a standalone shareable HTML report even when companion media is missing.
16. As a user, I want exports to retain the selected variant and archive retention settings so the archive job applies what I reviewed.
17. As a user, I want completed work reused on resume without mixing variants, stages or changed configurations.

## Implementation decisions

### Experiment and candidate identity

- Extend saved configuration, runner, report and export together. Existing single-format configurations remain interpretable as one variant; old reports remain readable and cannot acquire a validation claim retroactively.
- Offer four editable presets: Match source, original-resolution 10-bit 4:2:0, capped-1080p 10-bit 4:2:0, and capped-1080p 8-bit 4:2:0. Select only Match source by default. Permit additional currently supported format combinations.
- Identify a candidate by format variant, encoder and quality setting. Use one encoder and quality setting across the project. Source-dependent dimensions and pixel formats are resolved by the variant's policy, not by an implicit encoder fallback.
- Retain frame rate. Do not enlarge smaller sources. Preserve current rejection of unsupported source types. Expanding chroma or bit depth does not recover information.
- Distinguish variant, candidate, source/sample and tuning/validation stage in saved results and cache identities. Changed experiments must not reuse incompatible measurements. A displayed test count is an upper bound or estimate when adaptive tuning prevents an exact count; label it accordingly.

### Project qualification and estimates

- A tuning-qualified candidate has successful measurements meeting the target on every required tuning sample. Missing, failed and unsupported samples prevent qualification. Averages never replace this gate.
- Test candidate settings across all required samples rather than combining independently tuned per-sample winners. Show the weakest sample and coverage.
- Rank storage and encoding time using measured tuning-sample rates. Average rates within each source, then multiply by that source's full duration and sum across distinct selected sources. Do not double-count a source selected at multiple offsets.
- Label estimates as selected-source, video-only projections, with validation evidence shown separately. Report transformations explicitly and retain existing scoring caveats about chroma loss.

### Fresh-footage validation and budgets

- Propose one non-overlapping validation section per selected source, ideally from another scene. Let the user review or replace sections before running. Default to twice the tuning-section duration, capped at 60 seconds. Any unavailable coverage must be visible rather than substituted with tuning footage.
- Use one total budget per invocation across all variants and stages, with a default 30% validation reserve. Stop tuning before consuming the reserve. Preserve existing explicit-resume behavior: rerunning can spend another invocation allowance, continuing a frozen validation shortlist rather than tuning from held-out evidence. Disclose session time, preflight/hash overhead and checkpoint partial work.
- Shortlist the smallest and fastest tuning-qualified candidates from each variant; remove duplicate candidates.
- Validate fixed settings on every required validation section. A failed candidate stays failed; do not adjust it using validation evidence. More tuning is a new experiment. Never lower the target automatically.
- Project recommendations require complete, passing tuning and validation evidence. Present tuning-only candidates as provisional, validation failures as failed, and budget-limited coverage as incomplete.
- Keep report display thresholds separate from measured experiment targets and actual coverage. Changing a display threshold cannot fabricate a validation result or new measurements.

### Visual review and export

- After validation, use remaining budget for review assets for each validated finalist/sample. Asset completion is separate from metric validation status.
- Provide synchronized full-sample browser-compatible previews and links to exact encoded clips in an optional companion folder. Synchronize sample-relative playback, seeking and pause behavior. Show missing or unsupported media as an actionable state rather than a broken player.
- Converted previews identify their resolution, pixel format/bit depth and codec conversion. They are visual aids, not exact measured encodes. Browsers cannot certify preservation of 10-bit/4:2:2 detail.
- Preserve enough frame-score evidence to select three separated low-scoring moments. Generate matching original/encoded full-resolution still pairs with timestamps and user-controlled crop/zoom. Pair the same source instant; handle scaling and score subsampling without inventing unmeasured frames. If fewer distinct moments exist, show fewer and explain why.
- Keep the standalone HTML useful without companion media. Preserve source-path redaction, escape labels, use safe relative asset references, and disclose that shared previews can reveal private footage.
- Export the exact chosen encoder/quality, variant policy and existing retention choices with experiment identity and evidence status. Provisional or failed results must never export as validated. Preserve archive verification and separate cleanup safeguards.

## Testing decisions

Approved testing approach: test primarily through saved configurations into real benchmark results, report behavior, exported settings and archive verification, reusing existing synthetic FFmpeg integration tests and report/browser checks.

- Use small synthetic mixed-format sources to prove Match source retention, explicit conversions, resolution caps and shared-candidate qualification.
- Test worst-sample failure, missing coverage, source-duration weighting and duplicate-source sections with controlled result fixtures.
- Test held-out interval rejection, budget boundaries and resume with controlled timing/process behavior where wall-clock tests would be flaky. Confirm fixed validation settings through actual measured outputs.
- Test that failed validation cannot silently tune, fall back to another encoder, lower the target or produce a validated recommendation.
- Test playback synchronization, safe asset paths, missing media, preview disclosure, matching low-score timestamps and crop alignment through the report/browser workflow.
- Verify old configs/results, exports and archive safeguards continue to work. Run pytest, Ruff format/check, ty, report math tests, bundled-JS build and offline browser checks as applicable.

## Out of scope

Automatic per-source encoder switching; HDR/interlaced/VFR support; audio quality benchmarking; guarantees of lossless preservation, editor relinking or grading latitude; exhaustive codec searches; uploading footage; automatic deletion of originals.

## Further notes

The user accepted the fifteen interview recommendations, emphasized Match source for mixed footage, and authorized implementation with implement-spec. Numerical scores and fresh-footage validation still require human visual review before cleanup.
