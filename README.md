# ArchiveBench

Choose archive presets for completed projects using your own footage and hardware. Compare quality, storage and encoding time, review the changes, then apply exact settings to different folders with verified resumable jobs. Use an agent skill or the same commands directly from a terminal.

<p align="center">
  <a href="pyproject.toml"><img alt="Version: 0.1.0" src="https://img.shields.io/badge/Version-0.1.0-C4A7E7?style=for-the-badge&amp;labelColor=493267"></a>
  <a href="docs/benchmark.md"><img alt="Reports: offline" src="https://img.shields.io/badge/Reports-Offline-A2FFB0?style=for-the-badge&amp;labelColor=246732"></a>
  <a href="pyproject.toml"><img alt="Python: 3.11 or newer" src="https://img.shields.io/badge/Python-3.11%2B-F4C98B?style=for-the-badge&amp;logo=python&amp;labelColor=75512B"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-F4C98B?style=for-the-badge&amp;labelColor=75512B"></a>
</p>

[Install](docs/installation.md) · [Quick start](#start) · [Read the report](#read-the-report) · [Benchmark guide](docs/benchmark.md) · [Settings](docs/configuration.md) · [Archiving](docs/archiving.md) · [Release notes](docs/releases.md) · [Agent prompt](docs/AGENT-PROMPT.md)

## How it works

Choose footage sections and save an experiment. ArchiveBench measures encoder settings, checks finalists on fresh footage, and writes an offline report. Use the report to choose settings, review the exact encoded clips, then export settings for the optional archive runner.

![ArchiveBench user flow: check tools, save an experiment, benchmark, compare and review, export settings, then archive while keeping originals.](docs/diagrams/user-flow.svg)

[Open the user-flow diagram](docs/diagrams/user-flow.html). Cleanup is a separate decision after visual review and verification.

## Start

Follow the [terminal workflow](docs/terminal-workflow.md), or [install the agent skill](docs/installation.md#install-the-optional-agent-skill). Both use the same commands and evidence.

Windows is the tested platform. macOS/Linux and their hardware encoders remain experimental.

Install [uv](https://docs.astral.sh/uv/) and a full FFmpeg build with `libvmaf`. Put `ffmpeg` and `ffprobe` on PATH. uv can provide Python 3.11. Clone the project for use with an agent or to modify it:

```powershell
git clone https://github.com/Today20092/ArchiveBench.git
cd ArchiveBench
uv sync --locked --python 3.11
uv run archivebench doctor
uv run archivebench setup --config local-config.json
uv run archivebench plan local-config.json
uv run archivebench benchmark local-config.json --output runs/first-test
```

Setup asks for footage sections, format variants, quality levels, encode repeats and a time budget. Review its proposed validation samples before you run the benchmark. See [configuration](docs/configuration.md) for the saved fields.

Open `runs/first-test/report.html`. No server, internet connection or Node installation is needed to view it. Follow [the report steps below](#read-the-report) to compare measurements and review the clips.

Want to see a report first? Download the [v0.1.0 synthetic demo](https://github.com/Today20092/ArchiveBench/releases/download/v0.1.0/archivebench-synthetic-demo.zip), extract the whole ZIP and open `report.html`. It shows the released interface, which may differ from this checkout. Its synthetic measurements cannot select settings for your footage and hardware.

Prefer an installed command? See the [standalone installation](docs/installation.md#install-the-command). Python distributions are available from [GitHub Releases](https://github.com/Today20092/ArchiveBench/releases).

Select motion, fine detail and dark/noisy examples. A representative sample is more informative than a large number of similar clips. `setup` lists eligible clips from a folder and asks which to include; it does not infer scene diversity. Proxy and generated archive folders are excluded.

## What is measured

ArchiveBench screens configured H.264, H.265, AV1 and VP9 encoders, including hardware encoders that pass an actual encode test. It tunes promising candidates within your budget and reports failures and unmet targets.

Compare named format variants in one run, including **Match source** for mixed footage. A project candidate uses the same encoder and quality across scenes. It qualifies only when every required sample passes, then the smallest and fastest finalists are checked on fresh sections that were excluded from tuning. Failed and incomplete evidence stays visible.

Compare quality levels in the same experiment. Setup offers VMAF 80, 90, 95 and 97, or a custom list. The runner reuses identical measurements across levels. Each level still needs its own complete passing evidence. A higher target can require more storage or encoding time, and some targets may remain unmet within your budget.

Choose how many encode repeats to measure per setting. The default is one. More repeats measure timing variability; they do not improve picture quality. Tuning tries different compression settings, so one repeat can still involve many encodes.

![Recommendation flow: measure tuning samples, require all samples to pass, freeze finalists, check fresh validation samples, then distinguish validated from provisional, failed or incomplete evidence.](docs/diagrams/recommendation-flow.svg)

[Open the recommendation diagram](docs/diagrams/recommendation-flow.html). A budget-limited search does not prove that the best possible settings were found.

VMAF is a model score, not a percentage of original quality. Measurements cover video only. Projections exclude audio, and scores do not capture all chroma loss or prove editing quality. Read the [method and limits](docs/benchmark.md) before choosing settings.

## Read the report

1. Start with the whole collection. Use the size/time and quality/size charts to find measured settings that fit your priorities. The shaded areas show the preferred direction; they do not certify a result.
2. Compare the saved quality levels. The table shows the smallest validated collection choice at each target, its weakest tuning and validation scores, and projected video size and encoding time. Missing or unmet targets stay explicit.
3. Select a setting from a chart or choice card. Use the two setting selectors to compare size, time and VMAF differences for the same sample coverage. Open the sortable measurements table for details.
4. Inspect the evidence and footage. Review matched native-size stills at saved low-scoring moments with crop and zoom controls. Use paired playback to inspect motion, then open the exact measured MKV in a native player. Browser review previews use H.264 8-bit 4:2:0 and cannot prove source-format fidelity.
5. Use the selected-settings handoff to copy an agent prompt or export archive settings and a decision summary. The summary records your active constraints and stated visual-review status. Review marks do not authorize cleanup.

The report starts with the selected sources' combined duration. Changing duration scales that source mix to estimate video size and encoding time. Target and duration controls use saved measurements; they do not run new tests or change the saved experiment conclusion. Older results without full source durations show a labeled sample-duration estimate.

Read [the benchmark guide](docs/benchmark.md) for scoring, validation, playback limits and restart behavior. Keep `review/` beside `report.html` for native stills and companion playback.

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

Install the [portable skill](docs/installation.md#install-the-optional-agent-skill) into your client's discovery directory. It guides bounded comparisons, preset reuse, visual decisions and jobs using the same CLI as [terminal users](docs/terminal-workflow.md). A capable agent without the skill can also invoke those tools: the skill supplies procedure, while measurements and verification live in the shared engine. The [agent prompt](docs/AGENT-PROMPT.md) remains a checkout alternative. [AGENTS.md](AGENTS.md) supplies maintenance rules.

## Why I made it

I wanted to archive my own footage and free up storage. ArchiveBench gives videographers and editors a starting point to measure the tradeoffs on their own computer, choose settings, and use or adapt an archive script for finished projects.

This project was built with AI coding agents. You can ask your agent to install it, explain your results, or modify it for your workflow. Keep the saved experiment and verification checks intact when adapting it.

## Sharing results

Share the HTML report after checking its labels and preview images for private content. Include its `review/` folder for companion playback and native stills; without it, those controls show missing assets. Raw `results.json` contains local paths. Source paths are redacted in the HTML; labels and images are not.

## Development

See [development and checks](docs/development.md) for report builds, tests and synthetic examples. No personal footage is included. ArchiveBench does not redistribute FFmpeg; see the [third-party notices](THIRD_PARTY_NOTICES.md).

Report reproducible bugs through [GitHub Issues](https://github.com/Today20092/ArchiveBench/issues). Review diagnostic data before posting; raw results and configs can contain private paths.
