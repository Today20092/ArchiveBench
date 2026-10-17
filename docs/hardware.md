# Hardware and encoder availability

ArchiveBench separates an encoder included in FFmpeg from an encoder that works on your computer with the requested settings. Hardware discovery helps choose a comparison; it does not choose picture quality from a GPU model name.

```powershell
archivebench doctor
archivebench doctor --config local-config.json
archivebench doctor --config local-config.json --refresh
```

Plain `doctor` reports the CPU, operating system, available GPU identity information, FFmpeg build and configured encoders. NVIDIA inventory uses `nvidia-smi` when available, including driver and VRAM information. Windows display-adapter inventory also identifies other adapters and provides a fallback. Missing inventory information remains unknown; it does not establish that an encoder is unsupported. Probes use the existing FFmpeg adapter's default device selection, so a pass does not certify every GPU in a multi-GPU computer.

`doctor --config` checks the saved encoder controls and resolved pixel format, resolution and frame rate. It reads source metadata and uses generated synthetic frames, not footage encodes. Each probe encodes at most three frames with a ten-second limit; the availability check has a thirty-second total allowance including inventory and source metadata. Output inspection verifies codec, pixel format, dimensions and frame rate. An encoder that silently converts a requested format does not pass. Final writes and process cleanup can slightly overrun the allowance.

| Result | Meaning |
| --- | --- |
| Verified | The exact tested combination encoded successfully and its output format matched. |
| Unsupported | The encoder or requested combination is unavailable according to definitive evidence. |
| Probe failed | The check encountered an error without establishing incompatibility. |
| Unknown | There is not enough evidence, including checks not reached within the allowance. |

A timeout, busy device or temporary resource failure is not proof of unsupported hardware. A successful three-frame probe does not establish sustained throughput, maximum device capabilities, stability on long clips, picture quality or editor compatibility. Decode and encode capabilities are separate: this discovery path uses software decoding and does not certify hardware decoding.

## Choosing encoders

Setup and terminal comparison review use the same availability checks. Leave encoder selection blank to use at most three verified defaults. Explicit names remain visible with their failures or missing evidence, so an incomplete probe does not silently rewrite your request. The terminal UI reports hardware inventory at startup; archive-job preflight includes that inventory alongside its existing footage checks.

Both fixed comparisons and target tuning record availability evidence in `results.json` under `capabilities`. Target-tuning checks cover the starting controls, not every quality value it might later try. The benchmark skips definitively unsupported combinations; failed or unknown checks do not rule out a measured attempt. Measured encodes still validate their actual outputs.

For example, a GPU may support HEVC 10-bit 4:2:0 but reject HEVC 10-bit 4:2:2. With **Match source** and 4:2:2 footage, ArchiveBench must preserve 4:2:2 or report failure. Choose a compatible CPU encoder to preserve it, or explicitly choose a 4:2:0 variant and review the color reduction. Supporting a codec alone is insufficient evidence for every chroma format, bit depth, resolution and control combination.

## Cached evidence and reproducibility

Availability evidence is cached locally for up to 24 hours and bound to hardware, driver, probe implementation, executable paths/hashes/build versions and exact settings. The cache is under `%LOCALAPPDATA%/ArchiveBench/capabilities` on Windows, or `~/.cache/ArchiveBench/capabilities` when that environment variable is absent. Nondefinitive failures are not cached as unsupported; hardware results without usable device inventory are not reused across invocations. Use `--refresh` to bypass cached evidence after resolving a device problem. A benchmark rechecks availability within its own time allowance and records the evidence alongside the run; preparation and checks are overhead, not measured encoding time.

This first implementation uses operating-system inventory and FFmpeg runtime probes. It does not enumerate every capability through native vendor SDKs or certify every installed GPU. Windows is the tested platform; other operating systems and hardware backends require their own successful runtime checks.
