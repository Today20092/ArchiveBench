# ArchiveBench

Find smaller video encodes that meet your quality target on your footage and hardware. Run short tests, compare size, quality and encoding time in an offline report, then export the settings you want to use.

<p align="center">
  <a href="docs/development.md"><img alt="Status: in development" src="https://img.shields.io/badge/Status-In%20development-C4A7E7?style=for-the-badge&amp;labelColor=493267"></a>
  <a href="docs/benchmark.md"><img alt="Reports: offline" src="https://img.shields.io/badge/Reports-Offline-A2FFB0?style=for-the-badge&amp;labelColor=246732"></a>
  <a href="pyproject.toml"><img alt="Python: 3.11 or newer" src="https://img.shields.io/badge/Python-3.11%2B-F4C98B?style=for-the-badge&amp;logo=python&amp;labelColor=75512B"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-F4C98B?style=for-the-badge&amp;labelColor=75512B"></a>
</p>

[Quick start](#start) · [Benchmark guide](docs/benchmark.md) · [Settings](docs/configuration.md) · [Archiving](docs/archiving.md) · [Agent prompt](docs/AGENT-PROMPT.md)

## Start

Windows is the tested platform. macOS/Linux and their hardware encoders remain experimental.

Install [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer, plus an FFmpeg build with `libvmaf`. Put `ffmpeg` and `ffprobe` on PATH. From this checkout, run:

```powershell
uv sync --locked
uv run archivebench doctor
uv run archivebench setup --config local-config.json
uv run archivebench benchmark local-config.json --output runs/first-test
```

Open `runs/first-test/report.html`. No server, internet connection or Node installation is needed to view it. Compare measured settings, inspect previews and estimate size/time for longer footage. Review the saved clips before accepting a result.

Select motion, fine detail and dark/noisy examples. A representative sample is more informative than a large number of similar clips. `setup` lists eligible clips from a folder and asks which to include; it does not infer scene diversity. Proxy and generated archive folders are excluded.

## What is measured

ArchiveBench screens configured H.264, H.265, AV1 and VP9 encoders, including hardware encoders that pass an actual encode test. It tunes promising candidates within your budget and reports failures and unmet targets.

The report shows the smallest and fastest tested options meeting your selected VMAF target. Charts show quality, storage and time tradeoffs; duration controls project those measurements to longer footage.

VMAF is a model score, not a percentage of original quality. Measurements cover video only. Projections exclude audio, and scores do not capture all chroma loss or prove editing quality. Read the [method and limits](docs/benchmark.md) before choosing settings.

## Configuration and restart

- Keep source bit depth/chroma, or choose 8/10-bit 4:2:0 or 4:2:2.
- Keep resolution, or cap it at 2160p, 1440p, 1080p or 720p. Smaller sources are not enlarged; frame rate stays unchanged.
- Save archive retention choices alongside the benchmark. New configs copy all audio and retain supported subtitles, attachments, metadata and chapters by default.

See the [configuration reference](docs/configuration.md) for every option. HDR, interlaced and variable-frame-rate footage are unsupported.

Rerun the same command to resume. Changed settings, sources or toolchains require a new output folder. See [restart and budget behavior](docs/benchmark.md#restart-and-budgets).

## Optional archive runner

Export settings from the report, review the clips, then follow the [archive and cleanup guide](docs/archiving.md). The runner writes MKV and keeps originals during encoding. Unsupported streams stop the job. Editor relinking and proprietary metadata need a separate compatibility check.

**Cleanup permanently deletes originals.** It is a separate command after visual review, with hash, decode, stream and savings checks. Benchmarking does not authorize cleanup.

## Use with Codex or Claude

Paste [the agent prompt](docs/AGENT-PROMPT.md) into your agent, pointing it to this checkout. The agent uses the same CLI and saved config. It helps select samples, inspect capabilities, choose a budget and interpret results; thresholds and cleanup remain explicit user decisions. [AGENTS.md](AGENTS.md) provides maintenance rules and links to the run procedure.

## Sharing results

Share the HTML report after checking its labels and preview images for private content. Raw `results.json` contains local paths. Source paths are redacted in the HTML; labels and images are not.

## Development

See [development and checks](docs/development.md) for report builds, tests and synthetic examples. No personal footage is included. ArchiveBench does not redistribute FFmpeg; see the [third-party notices](THIRD_PARTY_NOTICES.md).
