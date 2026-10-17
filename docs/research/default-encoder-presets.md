# Default encoder presets

Research date: 2026-10-17. Scope: bundled starters for people without footage measurements; not benchmark adapter retuning or personal measured presets. No new benchmark was run for this note.

## Decision

Keep the existing source-preserving CPU HEVC choices and AVC alternative. Add explicit NVIDIA HEVC and CPU AV1 alternatives, using the existing adapter controls. Hardware/format discovery must determine availability before presenting a choice as usable. Keep all six starters unmeasured and unreviewed, with unknown quality, size and duration estimates.

| Starter | Exact starting controls | Change and rationale |
| --- | --- | --- |
| Quality priority | `libx265 -preset medium -crf 20` | Retain. A lower CRF within the same encoder/control policy requests more quality and typically more bytes. This is a product starting choice, not a guarantee. |
| Balanced | `libx265 -preset medium -crf 24` | Retain as the general CPU choice. x265 describes medium as its default speed/efficiency compromise. CRF 24 is ArchiveBench's existing choice, not an upstream universal recommendation. |
| Space priority | `libx265 -preset medium -crf 28` | Retain as the more lossy HEVC option. CRF 28 is x265's documented default; it is not necessarily suitable for camera originals. |
| Balanced (AVC alternative) | `libx264 -preset medium -crf 23` | Retain as an explicit codec alternative; source-preserved 10-bit/4:2:2 H.264 does not imply broad player/editor compatibility. |
| Faster encoding (NVIDIA HEVC) | `hevc_nvenc -preset p5 -tune hq -rc vbr -b:v 0 -cq 31` | Add a hardware-speed-oriented choice. P5/CQ31 is an existing ArchiveBench policy, not an NVIDIA quality guarantee. Do not automatically enable extra lookahead, AQ or multipass. |
| AV1 alternative (CPU) | `libsvtav1 -preset 6 -crf 30` | Add a compression-oriented alternative with a moderate speed preset. Upstream suggests CRF30 as a 1080p starting point and presets4–6 as a practical personal-use tradeoff. Its suitability for other footage remains unknown. |

All retain `pixel_format: source`, original dimensions/frame rate and copied audio. This intentionally means the AV1 or hardware starter can be unavailable for a source. A 4:2:0 conversion is a separate explicit choice; do not relabel that conversion as preservation. Rename descriptions to identify CPU/hardware and controls without promising measured savings or elapsed speed.

The recommendation combines documented control behavior with product judgment. It does not infer identical quality from CRF/CQ numbers across codecs or hardware. [x265 presets](https://x265.readthedocs.io/en/master/presets.html), [x265 rate control](https://x265.readthedocs.io/en/master/cli.html#quality-rate-control-and-rate-distortion-options), [SVT-AV1 FFmpeg guide](https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/cd6567a1ae441ffea43564dd6d1bd7eebfe0c486/Docs/Ffmpeg.md), [NVIDIA programming guide](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvenc-video-encoder-api-prog-guide/index.html).

## What the sources establish

### CPU HEVC and AVC

x265's slower presets spend more computation seeking compression efficiency; medium is its documented general compromise. That supports retaining medium rather than changing every user's workflow to slow or placebo. CRF controls quality/size separately from speed. Content-specific grain/animation or metric tuning should not be applied globally. The existing CRF20/24/28 ladder expresses different quality priorities within one policy, not three verified quality levels. [x265 presets](https://x265.readthedocs.io/en/master/presets.html), [x265 options](https://x265.readthedocs.io/en/master/cli.html).

FFmpeg exposes x264 and x265 as separate library wrappers. Keep the AVC alternative explicit, and probe the installed library's actual pixel formats rather than infer them from the codec name. No evidence here justifies replacing the existing AVC setting with a different quality number. [FFmpeg encoder documentation](https://ffmpeg.org/ffmpeg-codecs.html#libx264_002c-libx264rgb).

### CPU AV1 and VP9

SVT's guide distinguishes efficiency/time from quality/size, warns that CRF values are not equivalent across encoders, and describes scaling across CPU threads. Preset6 chooses the faster end of its recommended4–6 range. CRF30 is a cautious initial product choice grounded in its 1080p suggestion; do not promise a fixed VMAF, size reduction, or encoding speed on another resolution. Avoid globally enabling synthetic grain: that deliberately replaces original grain and deserves its own acceptance. [SVT-AV1 FFmpeg guide](https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/cd6567a1ae441ffea43564dd6d1bd7eebfe0c486/Docs/Ffmpeg.md).

Keep AOM, rav1e and VP9 available for comparisons rather than add three more first-use defaults. AOM `cpu-used` and rav1e `speed` trade computation for efficiency. Rav1e supports several chroma formats, but that alone does not establish an optimal archival choice. VP9's `good` mode is the documented practical tradeoff; `best` is not an automatic improvement. Google's delivery recommendations include bitrate-capped/two-pass workflows, so they should not be copied wholesale into ArchiveBench's unconstrained archival starter. [FFmpeg libaom/rav1e/libvpx controls](https://ffmpeg.org/ffmpeg-codecs.html), [rav1e capabilities](https://github.com/xiph/rav1e), [Google VP9 bitrate modes](https://developers.google.com/media/vp9/bitrate-modes), [Google VP9 settings](https://developers.google.com/media/vp9/settings).

### Hardware encoders

NVIDIA documents P1–P7 as a performance/quality tradeoff and target quality as distinct from bitrate targets. Capability depends on the GPU, driver, codec, format and features. Multipass operates per frame; its mere availability does not justify enabling it for every archive. The existing adapter's P5/HQ policy is a reasonable starting hypothesis, with no universal speed multiplier or quality claim. [NVIDIA API guide](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvenc-video-encoder-api-prog-guide/index.html), [NVIDIA support matrix](https://developer.nvidia.com/video-encode-decode-support-matrix).

Do not manufacture equivalent Intel/AMD/Linux/macOS presets by copying NVIDIA's number31. QSV's `global_quality` selects ICQ unless additional options change that mode; FFmpeg warns that the runtime may select another mode and recommends verbose inspection. AMF has distinct CQP/QVBR and quality/speed controls. VAAPI modes depend on the driver and require hardware surfaces. Retain these existing benchmark adapters and exact-format probes; adding vendor-specific starters should follow evidence for their actual control policy rather than a numeric translation. VideoToolbox likewise remains a separate adapter with its own quality direction and platform support. [FFmpeg QSV and VAAPI](https://ffmpeg.org/ffmpeg-codecs.html), [AMD AMF settings](https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/AMF-Encoder-Settings-and-Tuning-in-FFmpeg), [FFmpeg VideoToolbox implementation](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/videotoolboxenc.c).

## Implementation and evidence boundaries

- Change bundled JSON and their catalog expectations; regenerate exact encoder options and settings fingerprints through the existing preset model. Do not alter `SPECS` to implement starter choices, because that changes existing measured preset resolution and run fingerprints.
- Preserve existing starter names/paths where possible. Add alternatives at the end so existing guided selection order remains stable.
- The source-mode encoder-options representation uses an 8-bit420 placeholder for fingerprint comparison; runtime must resolve and verify the actual source format. This placeholder must not authorize conversion.
- Availability is not quality validation. Distinguish verified exact-format support, unsupported combinations, probe failures and unknowns. Busy devices/timeouts must not become permanent unsupported claims.
- No universal encoder ranking follows from vendor documentation. Real CPU speed, device generation, library version, content complexity, noise/grain and quality requirement can change the result. Measure representative footage before claiming comparable size/time/quality; human visual/editor acceptance remains pending.

Research used official documentation and upstream repositories. It did not treat forum anecdotes or a vendor's performance marketing as transferable measurements for users' footage.
