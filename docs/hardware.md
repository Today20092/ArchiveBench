# Hardware and encoder availability

ArchiveBench separates an encoder included in FFmpeg from an encoder that works on your computer with the requested settings. Hardware discovery helps choose a comparison; it does not choose picture quality from a GPU model name.

```powershell
archivebench doctor
archivebench doctor --config local-config.json
archivebench doctor --config local-config.json --refresh
```

Plain `doctor` reports the CPU, operating system, available GPU identity information, FFmpeg build and configured encoders. NVIDIA inventory uses `nvidia-smi` when available, including driver and VRAM information. Windows display-adapter inventory also identifies other adapters and provides a fallback. Missing inventory information remains unknown; it does not establish that an encoder is unsupported. Probes use the existing FFmpeg adapter's default device selection, so a pass does not certify every GPU in a multi-GPU computer.

Plain `doctor` also reports `format_checks` for 8/10-bit 4:2:0 and 4:2:2: the intersection of recognized manufacturer capabilities and the installed FFmpeg encoder's advertised pixel formats. Known impossible combinations are excluded before synthetic probes or cached probe results are considered. Unknown combinations still use runtime probes. This filtering also applies to fixed comparisons, target tuning, archive-job preflight and archive execution. It never silently reduces chroma or bit depth.

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

Hardware identity and the capability implementation bind benchmark resume checks; changes require a new output folder. Raw inventory and source-dated evidence remain local in `results.json` under `capabilities.hardware`, archive-job plans and archive manifests. Portable HTML reports omit this raw capability inventory.

## Manufacturer evidence and limits

Manufacturer evidence is bundled for offline use; normal runs do not query vendor websites. The table revision is **2026-10-17**. Capability records include the source URLs and revision so a known exclusion can be distinguished from a failed runtime probe.

| Hardware | Manufacturer evidence and limits |
| --- | --- |
| NVIDIA | Reviewed GeForce RTX 20/30/40/50 model names, including recognized laptop suffixes, use the official [GPU Support Matrix](https://developer.nvidia.com/video-encode-decode-support-matrix) and [NVENC Application Note](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvenc-application-note/index.html). Unrecognized names remain unknown. |
| AMD | Reviewed Radeon RX model patterns use AMD's [AMF GPU/APU support table](https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/GPU-and-APU-HW-Features-and-Support). RX 6300/6400/6500 models have no hardware encode; reviewed RX 5300–5700 and RX 6600–6900 models lack AV1 encode; reviewed RX 7500–7900 and RX 9060/9070 models add AV1. These encode paths use 4:2:0, with 8-bit H.264 and 8/10-bit HEVC/AV1 where the codec exists. Generic Radeon/Ryzen names and APUs remain unknown. |
| Apple | Official [M1](https://support.apple.com/en-us/111894), [M2](https://support.apple.com/en-us/111869), [M3](https://support.apple.com/en-us/117736) and [M4](https://support.apple.com/en-us/121555) specifications identify H.264/HEVC media encoders. They do not establish chroma/bit-depth support, so those formats remain unknown and require real probes. There is currently no AV1 VideoToolbox adapter. |
| Intel and other hardware | No bundled manufacturer capability table; FFmpeg support and runtime probes determine eligibility. |

For example, a GeForce RTX 3070 Ti cannot encode AV1 or H.264/HEVC 4:2:2 through NVENC. RTX 40-series adds AV1 encoding, but that does not imply 4:2:2. Blackwell RTX 50-series supports H.264/HEVC 4:2:2; AV1 encoding remains 4:2:0. Codec, chroma and bit depth are separate capabilities.

FFmpeg may advertise equivalent semiplanar layouts (`nv12`, `p010le`, `nv16`, `p210le`); these satisfy the corresponding requested chroma/bit-depth layouts. Listings containing only hardware surfaces remain unknown and require a probe. A manufacturer-supported possibility still needs an actual encode and output-format validation with the selected driver, settings and FFmpeg build. Cached probe evidence is also bound to the manufacturer-table implementation.

With multiple GPUs, manufacturer evidence excludes a combination only when all relevant devices are known to reject it. Mixed compatible/unknown devices still require a probe. `CUDA_VISIBLE_DEVICES` or `NVIDIA_VISIBLE_DEVICES` overrides disable NVIDIA manufacturer-based rejection because device mapping is uncertain. Apple inventory uses `sysctl` and normalized `system_profiler` display names; Windows uses its existing adapter inventory and CPU fallback.

This is not a complete device database or a native vendor capability API query. AMD manufacturer matching currently uses Windows adapter inventory; Linux AMD devices remain unknown. Windows is the tested platform; macOS/Linux and their hardware backends remain experimental. Unknown or incompletely identified hardware retains runtime checks. Hardware capability evidence establishes technical eligibility, not picture quality, storage savings, encoding speed or editing compatibility.
