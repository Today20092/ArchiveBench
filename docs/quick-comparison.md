# Quick comparison and refinement

Quick runs now deliver the measurements report before detailed browser review. The default `review_mode: "deferred"` skips automatic still/preview rendering. Exact native pairs remain available through `review inspect/launch`. To prepare browser visuals for one selected result, run `archivebench review prepare --results RUN/results.json --trial ID --seconds 120`. It preserves measured encodes, generates only that trial's visuals, updates the report and records separate review timing. Original browser previews are hash-checked and shared across candidates from the same sample. Set `review_mode: "full"` before a run to request automatic frontier visuals; the measurements report is still written first. These browser conversions do not establish source color fidelity.

Choose the encoders you want to compare and how long you want to spend. These are independent choices. `archivebench setup --strategy fixed --config quick.json` is the default setup. Setup checks selected formats and suggests up to three verified encoders. Enter selected encoder names, or `all` to save every installed encoder with a supported adapter. Listing an encoder does not prove the hardware or requested format works. [Bounded synthetic probes](hardware.md) check runtime availability; measured footage still needs output validation. H.265 CPU (`libx265`) and GPU (`hevc_nvenc`) are separate choices. AV1 implementations are also separate encoders.

Setup defaults to five seconds from each selected clip, one timing repeat, 30 minutes total, and two fixed quality values per encoder. The saved `fixed_settings` map makes every setting explicit; edit it before launch. Defaults are starting comparisons, not equivalent quality across codecs. For example:

```json
"strategy": "fixed",
"encoders": ["libx265", "libsvtav1", "hevc_nvenc"],
"fixed_settings": {"libx265": [24, 30], "libsvtav1": [35, 41], "hevc_nvenc": [31, 37]},
"budget_minutes": 30,
"encode_repeats": 1
```

Run `archivebench doctor --config quick.json` to inspect availability, then `archivebench plan quick.json` and `archivebench benchmark quick.json --output runs/quick`. The benchmark rechecks availability within its allowance and records the evidence. Synthetic checks do not measure footage quality or encoding speed. There is no target search. On the first scene the measured queue tests one setting per encoder, then the next setting, for each explicit format. Later scenes test settings on the first scene's measured quality/size/time frontier. Missing evidence never becomes a pass.

The wall-clock allowance starts before source inspection and hashes. Preparation, scoring and review assets consume it too. The runner reserves up to 60 seconds (15% for shorter allowances) for review/report work. Unfinished items show measured duration estimates when the encoder/format has prior evidence, otherwise unknown. Estimates are approximate and can change with content; process cleanup and final report writes may slightly overrun. It will not silently start another allowance. Explicitly rerunning the same command grants a new allowance and reuses verified completed measurements. Changed settings, source or toolchain require a new output folder; cross-experiment cache import is not supported.

Pending settings share the remaining scene allowance so a slow encoder cannot consume the whole first comparison. A timed-out attempt remains unfinished and the queue continues to other encoders. Such a timeout is not proof of incompatibility. An explicit resume can retry it; the tool never starts an unlimited retry loop.

Run without competing editing/export work. Measured encodes are sequential to avoid biased timing from concurrent scoring/encodes. Encoder defaults manage CPU parallelism; SVT no longer has an arbitrary three-processor cap. VMAF starts with the available logical processor count and, when cheap enough, times a four-thread alternative within a bounded calibration allowance. It records the choice. This is a practical throughput policy, not a promise of globally optimal scheduling or measured historical CPU utilization.

Open `report.html`. Compare visual differences, measured VMAF, video sizes and encoding time against your original footage. Video-only savings projections exclude retained audio, metadata and verification costs. Select a scene for comparisons with equal coverage. Starting presets are exportable without fresh validation, but remain labeled **measured starting point** and unreviewed until you perform visual review. Export a portable preset and use it with `archive`, `job`, or the [Windows Send to launcher](windows-send-to.md) on another folder. Originals remain intact; cleanup remains a separate action after verification and acceptance.

For refinement, `archivebench setup --strategy tune --config refined.json` retains the exact-VMAF search, multiple targets and fixed fresh validation. That mode is deliberately more expensive. Legacy configs with no `strategy` still tune. Quick comparisons can have incomplete review assets at the deadline; exact hash-bound native comparisons remain available through `review inspect` and `review launch` for successful trials.
