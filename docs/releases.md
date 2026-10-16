# Releases

## 0.2.0

Released 2026-10-16. [Download v0.2.0](https://github.com/Today20092/ArchiveBench/releases/tag/v0.2.0) or follow [installation](installation.md).

- Use the terminal UI to select clips, choose a preset, review preflight, encode, stop and resume an archive job.
- Open the same UI from Windows Send to with selected folders or clips.
- Compare fixed CPU/GPU encoder settings within a time allowance, then export measured starting presets. Target tuning remains optional.
- Choose MKV, MOV or MP4, audio copy/AAC/removal, and supported timecode policies with compatibility checks.
- Install the optional agent skill, invoke it explicitly, or use it once through `npx skills use`.

Release assets include a Python wheel, source distribution, synthetic offline-report demo and SHA-256 checksums. FFmpeg is installed separately. Originals remain intact; cleanup requires separate review and authorization. See [full release notes](release-notes.md) for scope and limitations.

## 0.1.0

ArchiveBench's first public release benchmarks archival video encodes on your own footage and hardware. It compares measured quality, encoding time and projected storage in an offline report.

- Compare named format variants, including Match source for mixed resolutions, bit depths and chroma formats.
- Test shared encoder settings across all selected scenes, then validate frozen finalists on fresh footage.
- Inspect low-scoring moments with native-size crops and synchronized companion previews.
- Export measured settings to the optional batch archive runner, which preserves originals during encoding.
- Install with uv from the release wheel, or clone the repository for use with a coding agent.
- Download the synthetic demo ZIP, extract it and open `report.html` to explore the report with its companion assets.

Windows is the tested platform. Hardware availability depends on the installed FFmpeg build, device and driver. macOS/Linux hardware support is experimental. HDR, interlaced and variable-frame-rate footage are unsupported. VMAF does not prove editing or color fidelity; inspect exact clips before archiving. Editor relinking and application-specific metadata require workflow testing.

See [installation](installation.md), [benchmarking](benchmark.md) and [archiving](archiving.md). FFmpeg is installed separately and is not included in the distributions. This project was built with AI coding agents.
