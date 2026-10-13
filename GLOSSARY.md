# ArchiveBench

Terms for comparing archival encodes and deciding which settings to use.

## Language

**Format variant**:
A named combination of output chroma, bit depth and resolution choices within an experiment.
_Avoid_: Codec, quality profile

**Tuning sample**:
A selected footage section used to search for encoder settings that meet the quality target.

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
