# ArchiveBench

Benchmark archival video encodes on your CPU and GPU using your own footage. Compare quality, storage and encoding time in an offline report, then export the settings you want to use for a batch archive.

<p align="center">
  <a href="pyproject.toml"><img alt="Version: 0.1.0" src="https://img.shields.io/badge/Version-0.1.0-C4A7E7?style=for-the-badge&amp;labelColor=493267"></a>
  <a href="docs/benchmark.md"><img alt="Reports: offline" src="https://img.shields.io/badge/Reports-Offline-A2FFB0?style=for-the-badge&amp;labelColor=246732"></a>
  <a href="pyproject.toml"><img alt="Python: 3.11 or newer" src="https://img.shields.io/badge/Python-3.11%2B-F4C98B?style=for-the-badge&amp;logo=python&amp;labelColor=75512B"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-F4C98B?style=for-the-badge&amp;labelColor=75512B"></a>
</p>

[Install](docs/installation.md) · [Quick start](#start) · [Benchmark guide](docs/benchmark.md) · [Settings](docs/configuration.md) · [Archiving](docs/archiving.md) · [Agent prompt](docs/AGENT-PROMPT.md)

## Start

Windows is the tested platform. macOS/Linux and their hardware encoders remain experimental.

Install [uv](https://docs.astral.sh/uv/) and a full FFmpeg build with `libvmaf`. Put `ffmpeg` and `ffprobe` on PATH. uv can provide Python 3.11. Clone the project for use with an agent or to modify it:

```powershell
git clone https://github.com/Today20092/ArchiveBench.git
cd ArchiveBench
uv sync --locked --python 3.11
uv run archivebench doctor
uv run archivebench setup --config local-config.json
uv run archivebench benchmark local-config.json --output runs/first-test
```

Open `runs/first-test/report.html`. No server, internet connection or Node installation is needed to view it. Compare measured settings, inspect previews and estimate size/time for longer footage. Review the saved clips before accepting a result.

Want to see the report first? Download the [synthetic demo](https://github.com/Today20092/ArchiveBench/releases/download/v0.1.0/archivebench-synthetic-demo.zip), extract the whole ZIP and open `report.html`. Its measurements demonstrate the interface; benchmark your own footage and hardware to choose settings.

Prefer an installed command? See the [standalone installation](docs/installation.md#install-the-command). Python distributions are available from [GitHub Releases](https://github.com/Today20092/ArchiveBench/releases).

Select motion, fine detail and dark/noisy examples. A representative sample is more informative than a large number of similar clips. `setup` lists eligible clips from a folder and asks which to include; it does not infer scene diversity. Proxy and generated archive folders are excluded.

## What is measured

ArchiveBench screens configured H.264, H.265, AV1 and VP9 encoders, including hardware encoders that pass an actual encode test. It tunes promising candidates within your budget and reports failures and unmet targets.

Compare named format variants in one run, including **Match source** for mixed footage. A project candidate uses the same encoder and quality across scenes. It qualifies only when every required sample passes, then the smallest and fastest finalists are checked on fresh sections that were excluded from tuning. Failed and incomplete evidence stays visible.

Use the graphs to choose what matters to you: smaller files, faster encoding, or a higher measured quality target. Full-project storage/time estimates use the selected sources' durations. Report controls filter recorded measurements; new tests require a new experiment.

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

## Why I made it

I wanted to archive my own footage and free up storage. ArchiveBench gives videographers and editors a starting point to measure the tradeoffs on their own computer, choose settings, and use or adapt an archive script for finished projects.

This project was built with AI coding agents. You can ask your agent to install it, explain your results, or modify it for your workflow. Keep the saved experiment and verification checks intact when adapting it.

## Sharing results

Share the HTML report after checking its labels and preview images for private content. Include its `review/` folder for companion playback and native stills; without it, those controls show missing assets. Raw `results.json` contains local paths. Source paths are redacted in the HTML; labels and images are not.

## Development

See [development and checks](docs/development.md) for report builds, tests and synthetic examples. No personal footage is included. ArchiveBench does not redistribute FFmpeg; see the [third-party notices](THIRD_PARTY_NOTICES.md).

Report reproducible bugs through [GitHub Issues](https://github.com/Today20092/ArchiveBench/issues). Review diagnostic data before posting; raw results and configs can contain private paths.
