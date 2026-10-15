# Releases

## Current development

The TUI, revised Windows Send to workflow and quick fixed comparisons are documented in the [unreleased development summary](release-notes.md). That summary describes the current checkout, including local work, rather than the historical download below.

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
