# ArchiveBench

Terms for comparing archival encodes and deciding which settings to use.

**Archive preset**:
Portable encoder settings with their explanation, historical measurement scope and references to reviewed sections. A preset does not validate a new project.

**Archive job**:
A project-specific snapshot of a preset, source/output folders and per-file exceptions. Execution records verification and actual savings without changing the portable preset.

**Historical scope**:
The tested footage characteristics, hardware, toolchain and sample coverage supporting a preset. Applying the same settings outside this scope needs a confirmation sample check.

**Visual attestation**:
A person's accepted or rejected decision for specific, hash-bound footage sections. It is separate from measured quality and does not accept unreviewed sections.

**Replacement acceptance**:
A current, identity-bound decision accepting verified archive outputs: either genuine visual and editor reopening attestations, or explicit acceptance of the quality tradeoff without inspection. Automated verification alone does not authorize cleanup.

**Quality-tradeoff acceptance**:
An explicit person's decision to accept the preset's quality loss without claiming visual inspection, grading or editor reopening. It cannot waive integrity checks or unmet preservation requirements and does not authorize deletion.

## Language

**Fixed comparison**:
A bounded experiment that encodes explicit settings without searching for a quality target. It measures quality, space and encoding time on short selected sections.

**Measured starting point**:
An exportable preset supported by the listed short measurements. It does not imply fresh validation, visual acceptance or suitability for untested footage.

**Wall-clock allowance**:
The user-selected time available for a fixed comparison, including preparation, measurements and report/review work. Unfinished work remains explicit; final writes and process cleanup may cause a small recorded overrun.

**Quality levels**:
A saved list of VMAF targets for comparing measured storage, quality and encoding time. Targets share identical measurements; each target's recommendation must meet its own threshold on all tuning and fresh validation sections. Scores are not percentages of original quality.

**Format variant**:
A named combination of output chroma, bit depth and resolution choices within an experiment.
_Avoid_: Codec, quality profile

**Tuning sample**:
A selected footage section used to search for encoder settings that meet the quality target.

**Encode repeat**:
An additional encode of the same section with identical settings to measure timing variability. It does not improve picture quality or try a different compression setting. The configured repeat count includes the first measured encode and defaults to one.

**Match source**:
A format variant that preserves each clip's resolution, chroma, bit depth and frame rate while re-encoding its video. The output codec and bitrate may differ from the source, and mixed sources retain their individual formats.
_Avoid_: Stream copy, lossless

**Validation sample**:
A fresh, non-overlapping footage section reserved for checking shortlisted settings rather than tuning them.
_Avoid_: Tuning sample

**Project recommendation**:
One set of settings that meets the quality target on every required sample. Missing or failed measurements leave the evidence incomplete.
_Avoid_: Average winner

**Review preview**:
A browser-compatible visual aid that may be converted from the measured encode. It is distinct from the exact benchmark clip.
_Avoid_: Exact encode
