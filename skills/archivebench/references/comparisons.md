# Compare quality, space and time

Use `archivebench setup --config CONFIG` to create a saved experiment. Inspect and edit the file before `archivebench benchmark CONFIG --output RUN`. Paths are local project data. Choose fresh non-overlapping validation sections; a clip used entirely for tuning cannot also be its holdout.

Run `archivebench plan CONFIG` before encoding. It reports sources, settings, full-measurement bounds, separate screen/pilot work, preservation changes, scratch allowance and estimate gaps without encoding. Run `archivebench status RUN` with the output directory for completed trials and evidence state; an adaptive upper bound is not an exact remaining count.

Start with a representative clip and short equal sections when the user has no preference. Select useful CPU/GPU alternatives using doctor results. Codec and encoder are distinct; preserve dimensions, frame rate, bit depth, chroma and all audio by default. Name requested conversions separately, especially 4:2:2 to 4:2:0. Unsupported hardware never silently changes the policy.

Disclose `encode_repeats: 1`, the number of targets and sections, adaptive workload, budget and scratch needs. Different compression settings, compatibility screens and pilots are separate from timing repeats. For quality exploration, targets such as `target_vmafs: [80, 90, 95, 97]` share identical measurements but can add work. VMAF is a model score, not a percentage of retained quality. Let the user judge footage and savings rather than requiring an upfront score.

Honor an agreed time allowance. Overnight means patience for more efficient encoding unless the user gives a deadline. Estimates include uncertainty and excluded work; a budget is not an ETA. Hashing, reference creation, compatibility screening, tuning and fresh validation all take time. Expand only to resolve an unanswered choice.

Read `results.json`, `summary.md` and `report.html`. Compare only matching sections and identify validation status for each setting. Recommend settings only with complete required tuning and fixed-setting fresh validation. Report failures, below-target scenes and budget exhaustion. Video-only projections exclude retained audio and other streams; actual archive totals may differ. Codec, quality and speed tradeoffs cannot be broken into invented additive savings percentages.

Use exact candidate clips for visual judgment; converted browser previews and stills are aids and cannot certify 10-bit color or chroma fidelity. A visual decision is a user attestation distinct from a metric pass. Export the accepted archive settings from the report, with explanation, scope and evidence. Regenerate presentation from saved results using `archivebench report RESULTS`; changing source/settings/toolchain requires a new benchmark output folder. Resuming adds another invocation allowance, so honor the user's resume policy.

Completion: measured settings, uncertain estimates, missing evidence, visible quality differences and the user's choice are explicit. A report generated from partial results does not complete missing measurements.

Use `archivebench review inspect --results RUN/results.json` to identify trial IDs. `review launch --results RUN/results.json --trial ID` opens exact aligned files in optional video-compare. After the user actually reviews them, `review record --results RUN/results.json --trial ID --decision accept --reviewer NAME --method native` saves an attestation. Rejections can add `--objections "0.5,1.2" --note TEXT`. Launching alone is not acceptance. Browser conversions do not prove original chroma/bit-depth fidelity; native display conversion and monitor fidelity also require care. The native viewer is silent.
