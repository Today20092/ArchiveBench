# ArchiveBench

ArchiveBench tests short sections of your footage on your computer. Compare picture quality, file size and encoding time, save an archive preset, then reuse it to make smaller, verified copies of future projects. Originals stay intact.

<p align="center">
  <a href="https://github.com/Today20092/ArchiveBench/releases/tag/v0.2.0"><img alt="Version: 0.2.0" src="https://img.shields.io/badge/Version-0.2.0-C4A7E7?style=for-the-badge&amp;labelColor=493267"></a>
  <a href="docs/benchmark.md"><img alt="Reports: offline" src="https://img.shields.io/badge/Reports-Offline-A2FFB0?style=for-the-badge&amp;labelColor=246732"></a>
  <a href="pyproject.toml"><img alt="Python: 3.11 or newer" src="https://img.shields.io/badge/Python-3.11%2B-F4C98B?style=for-the-badge&amp;logo=python&amp;labelColor=75512B"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-F4C98B?style=for-the-badge&amp;labelColor=75512B"></a>
</p>

[Install](docs/installation.md) · [Find your first preset](#start) · [Use a saved preset](#archive-future-projects) · [Terminal UI](docs/terminal-ui.md) · [Release notes](docs/release-notes.md) · [Support](https://github.com/Today20092/ArchiveBench/issues)

## How it works

For first use, compare representative footage and save reusable settings, or choose a built-in starter for immediate archiving. The [starter catalog](docs/archiving.md#built-in-starter-presets) includes three CPU HEVC choices, AVC, NVIDIA HEVC and CPU AV1 alternatives. Labels describe intentions, not measured quality guarantees. No benchmark is required to use a starter.

Your hardware determines which encoders work and how fast they run. Your footage determines the measured quality and file size. You choose which quality tradeoffs to accept, through visual/editor review or explicit acceptance without inspection. ArchiveBench does not select a preset from your GPU name alone.

A codec is a video format, such as HEVC or AV1. An encoder produces that format. CPU HEVC and NVIDIA GPU HEVC are separate encoders and can produce different results.

| Use | What you do | What you get |
| --- | --- | --- |
| **1. Find your presets** | Benchmark representative footage on your computer; compare quality, size and speed; review candidates or explicitly accept the quality tradeoff. | An offline HTML report with charts, measurements and comparison clips, plus your chosen preset JSON files. |
| **2. Archive new projects** | Choose a saved preset and a different footage folder. | Smaller verified copies, actual savings and a job checkpoint you can resume. No new benchmark is required. |

For example, save one higher-quality preset and one smaller preset. Keep both in a permanent folder and choose one for each project. An archive preset stores exact settings and the historical measurement scope. Each archive job stores the project's folders and a snapshot of the selected settings. You can reuse presets without an agent or API key.

![Six steps: check the computer, choose footage, set the comparison, run the benchmark, review and save a preset, then archive future projects while keeping originals.](docs/diagrams/user-flow.svg)

[Open the user-flow diagram](docs/diagrams/user-flow.html). Cleanup follows a finished job, mandatory verification, replacement acceptance and separate approval of the exact deletion preview.

## Start

Start with a **fixed comparison**. It tests two saved compression settings per encoder on five-second footage sections, with one encode per setting. It measures quality without searching for a quality target.

Choose how much time to allow, with 30 minutes offered by default. Five seconds is the footage length, not the benchmark runtime. The time allowance includes preparation, encoding, scoring and report work. The report shows unfinished work when time runs out. Final file writes and process cleanup can cause a small overrun.

The report exports measured starting presets for you to review and reuse. A short comparison does not establish quality for untested footage. See [quick comparison](docs/quick-comparison.md) for queue order, timing and review preparation.

Follow the [terminal workflow](docs/terminal-workflow.md), or [install the agent skill](docs/installation.md#install-the-optional-agent-skill). Both use the same commands and evidence.

This first stage finds settings you like. If you already have a preset, go directly to [archiving a future project](#archive-future-projects).

Windows is the tested platform. macOS/Linux and their hardware encoders remain experimental.

### 1. Check your computer

Install [uv](https://docs.astral.sh/uv/) and a full FFmpeg build with `libvmaf`. Put `ffmpeg` and `ffprobe` on PATH. uv can provide Python 3.11. Then run:

```powershell
uv tool install --python 3.11 https://github.com/Today20092/ArchiveBench/releases/download/v0.2.0/archivebench-0.2.0-py3-none-any.whl
uv tool update-shell
archivebench doctor
```

`doctor` identifies your hardware and tools, queries NVIDIA NVENC, AMD AMF or Apple VideoToolbox where available, then intersects that evidence with installed FFmpeg support. Bundled manufacturer specifications provide a fallback. Known impossible combinations are skipped; unknown formats retain runtime checks. After saving a comparison config, run `archivebench doctor --config local-config.json` to verify its exact settings and output formats with bounded synthetic probes. See [hardware checks and their limits](docs/hardware.md).

If the command is not found after installation, open a new terminal. The commands above install released **v0.2.0**; newer features merged into `main` require the [source-checkout installation](docs/installation.md#install-a-source-checkout). Follow that guide to run checkout commands with `uv run` or install persistent commands from the checkout. See [installation](docs/installation.md) for upgrades.

### 2. Choose short footage sections

Choose examples of the footage you usually archive. Include motion, fine detail and dark or noisy scenes. Setup lists eligible clips and asks which to include. It does not select varied scenes for you. Proxy and generated archive folders are excluded.

### 3. Set the comparison

```powershell
archivebench setup --config local-config.json
archivebench plan local-config.json
```

Setup checks availability for the selected output formats and suggests up to three verified encoders. Explicit encoder selections retain their failure reasons; the tool never silently reduces chroma to make a GPU work. Setup saves your choices. Plan shows what will run before encoding starts.

| Choice | What it means |
| --- | --- |
| Encoders | Select CPU/GPU encoders, or enter `all` for installed encoders with supported adapters. |
| Footage sections | Short sections to measure. Results apply to the tested footage. |
| Output format | **Match source** preserves resolution, chroma, bit depth and frame rate while re-encoding. Choose reductions explicitly. |
| Time allowance | The total time available for preparation, measurements and report work. |

### 4. Run the benchmark

```powershell
archivebench benchmark local-config.json --output runs/first-test
```

The runner checks encoder availability within the allowance, prepares reference material, then tests one setting per encoder on the first scene before testing the second settings. Measured outputs still undergo format validation. Failures stay visible. The runner does not silently change your requested format.

Each successful test measures video quality, file size and encoding time. While time remains, the runner checks promising settings on additional selected scenes. Encodes run one at a time. Avoid other exports or heavy editing work during the benchmark so the speed measurements are useful.

### 5. Review and save an archive preset

Open `runs/first-test/report.html`. No server, internet connection or Node installation is needed to view it. Follow [Read the report](#read-the-report) to compare measurements, inspect the picture and export a reusable preset JSON file.

### 6. Archive future projects

Apply your saved preset through the [terminal UI](#open-the-terminal-ui) or an [archive job](#archive-future-projects). If footage or hardware differs from tested scope, optionally compare a short sample or explicitly accept uncertain suitability; technical incompatibility still blocks execution. Keep originals until separate review and cleanup.

Want to see a report first? Download the [synthetic demo](https://github.com/Today20092/ArchiveBench/releases/download/v0.2.0/archivebench-synthetic-demo.zip), extract the whole ZIP and open `report.html`. Its synthetic measurements demonstrate the report and cannot select settings for your footage and hardware.

## What is measured

ArchiveBench compares configured H.264, H.265, AV1 and VP9 encoders, including hardware encoders that pass an actual encode test. The default fixed comparison measures saved settings within your budget. The target-tuning workflow below searches compression settings and reports failures and unmet targets.

The default fixed comparison gives measured starting points. It does not include fresh validation. More encode repeats measure timing variability. They do not improve picture quality.

VMAF is a model score, not a percentage of original quality. Measurements cover video only. Projections exclude audio, and scores do not capture all chroma loss or prove editing quality. Read the [method and limits](docs/benchmark.md) before choosing settings.

### Optional target tuning

Use `archivebench setup --strategy tune --config refined.json` to search for settings that meet specific VMAF targets. This takes more work than a fixed comparison. A project recommendation requires complete passing measurements on tuning samples and separate fresh validation samples. Visual acceptance remains your decision.

See [target tuning and validation](docs/benchmark.md#screening-and-tuning) for the detailed recommendation diagram. A limited search does not prove that the best possible settings were found. Older saved configurations retain their original tuning behavior.

## Read the report

In the source-checkout workflow, start with the outcome and suggested next action. Completed measurements, failed tests and unfinished work are separate; an empty comparison cannot supply a measured preset. Reopening the report shows saved evidence, not a fresh check of your files. See [quick comparison](docs/quick-comparison.md) for recovery and [archive jobs](docs/archiving.md#reusable-project-jobs) for the next handoff.

1. Compare quality, video size and encoding time. Use the charts to find settings that fit your priorities. The shaded areas show the preferred direction, not an accepted result.
2. Check which footage sections were measured. Failed tests and missing measurements limit the conclusion. Fixed comparisons give starting points. Target-tuning runs separately show whether each quality target passed fresh validation.
3. Select settings to compare. Use the two selectors to compare the same footage sections. Open the measurements table for details.
4. Inspect the picture. Quick comparisons defer browser stills and previews by default. [Prepare review assets](docs/quick-comparison.md) for a selected result, or open its exact files in the native viewer. Browser previews use H.264 8-bit 4:2:0 and cannot prove source-format fidelity.
5. Use **Export reusable preset** to save accepted settings as JSON in your permanent preset folder. Use a clear filename, such as `camera-higher-quality.json` or `camera-smaller.json`. The preset stores settings, measurements, tested scope and saved review references. Review marks do not authorize cleanup.

The report starts with the selected sources' combined duration. Changing duration scales that source mix to estimate video size and encoding time. Target and duration controls use saved measurements; they do not run new tests or change the saved experiment conclusion. Older results without full source durations show a labeled sample-duration estimate.

Read [the benchmark guide](docs/benchmark.md) for scoring, validation, playback limits and restart behavior. Keep `review/` beside `report.html` for native stills and companion playback.

## Configuration and restart

- Keep source bit depth/chroma, or choose 8/10-bit 4:2:0 or 4:2:2.
- Keep resolution, or cap it at 2160p, 1440p, 1080p or 720p. Smaller sources are not enlarged; frame rate stays unchanged.
- Save archive retention choices alongside the benchmark. New configs copy all audio and retain supported subtitles, attachments, metadata and chapters by default.

See the [configuration reference](docs/configuration.md) for every option. HDR, interlaced and variable-frame-rate footage are unsupported.

For a benchmark, rerun the same command to reuse completed measurements. Changed experiment settings, sources or toolchains require a new output folder. See [restart and budget behavior](docs/benchmark.md#restart-and-budgets). Everyday archive jobs have their own [file-level resume](#resume-an-archive-job).

## Archive future projects

For immediate archiving, run `archivebench preset list`, export a listed starter with `archivebench preset export STARTER_PATH --output starter.json`, and use it in the job commands below. See [starter presets and job outcomes](docs/terminal-workflow.md#immediate-use-and-job-outcomes) for unmeasured limits, external destinations, offline summaries, resume and separate deletion approval. This archives selected footage, not the whole editing project.

### Open the terminal UI

Open the terminal UI to choose a saved preset or a built-in starter:

```powershell
archivebench-tui --preset-directory "D:\Archive Presets" "D:\Project"
```

Follow **Setup / compare > Clips > Settings > Review > Progress > Accept / cleanup**. Setup offers an optional comparison; choose a starter or saved preset to archive immediately. Add sources, select clips, choose a preset and output folder, then run preflight before Start. You can stop safely and resume the saved job later. After processing ends, record replacement acceptance, then separately preview and approve any cleanup.

![ArchiveBench Settings showing example CPU and GPU presets, the selected preset, destination folder and audio policy.](docs/images/tui-settings.png)

The TUI captured on 2026-10-16 with synthetic clips and illustrative presets. These presets are not recommendations. See the [TUI guide and screenshots](docs/terminal-ui.md#screenshots) for the full walkthrough, audio, container, timecode and resume options.

### Create an archive job

Once you have approved presets, ArchiveBench is your archival tool. Tomorrow's project might contain five original clips. Apply today's saved smaller preset without running another benchmark:

```powershell
archivebench job create "D:\New Project\archive-job.json" `
  --source "D:\New Project\Originals" `
  --output "D:\New Project\Archived" `
  --preset "D:\Archive Presets\lumix-smaller.json"

archivebench job inspect "D:\New Project\archive-job.json"
archivebench job run "D:\New Project\archive-job.json" --execute
```

Choose your higher-quality preset instead when that is what you want. For another project, create another job pointing to its source/output folders and reuse either preset. The saved presets remain portable; jobs have independent checkpoints. Editing a preset later does not change an existing job's snapshot.

Inspection shows compatibility, scope, available time/size estimates and exceptions; it runs short scratch probes. Execution encodes the selected files, verifies outputs and records actual savings including retained streams. Outputs follow the explicit MKV, MOV or MP4 container policy; presets without a container default to MKV. Timecode preservation requires supported MOV/MP4 output and verification. Preflight blocks incompatible stream/container combinations; originals stay intact. Unsupported preservation cases keep originals, and files without worthwhile savings are retained. Consider a short confirmation comparison when footage or hardware differs materially from your tested scope, rather than repeating a full benchmark for every project.

### Resume an archive job

After interruption, run the **same job command again**:

```powershell
archivebench job run "D:\New Project\archive-job.json" --execute
```

Verified completed files are checked and skipped. Pending files are encoded; an interrupted file restarts from its beginning. This is file-level resume, not continuation halfway through a video bitstream. Changed sources, outputs or job settings are refused rather than silently mixing results. See the [archive guide](docs/archiving.md) for exceptions, checkpoints and stale-lock handling after an abrupt shutdown.

### Windows Send to

Install the current ArchiveBench command on PATH, save your approved presets in a folder, then optionally install the per-user launcher:

```powershell
archivebench-send-to --install --preset-directory "D:\Archive Presets"
```

Select folders, clips or a mixture, then choose **Send to > Archive footage**. Windows 11 may require **Show more options**. Both archive shortcuts now open the TUI; the shortcut named **Archive footage (terminal)** is retained for compatibility. Source selections must share one drive. Choose the destination in Settings, run preflight in Review, then use Start. These shortcuts do not start a benchmark. **Review originals for deletion** opens the separate acceptance-gated cleanup workflow for one archive folder.

The TUI proposes `Archived Footage` beneath the selected project or common source folder, or beside a directly selected `Original Footage` folder. Review the destination, especially when combining projects. New TUI jobs are saved as `archive-job.json` inside the output folder, with `archive-job.json.log` alongside it. Resume with `archivebench-tui --job "D:\Project\Archived Footage\archive-job.json"`. Older adjacent `Archived Footage.job.json` files remain supported; CLI-created job files can use the explicit path shown above. Saved jobs retain their exact settings and selected files; use a different destination for a different preset version. See [installation and removal](docs/windows-send-to.md).

Optionally review replacements and reopen a separate editing-project copy, or explicitly accept the preset's quality tradeoff without inspection. This does not establish editor compatibility or proprietary metadata preservation.

**Cleanup permanently deletes originals.** After processing ends, it requires current identity-bound replacement acceptance and separate approval of the exact preview, with hash, decode, stream and savings checks. Benchmarking does not authorize cleanup.

## Use with Codex or Claude

Use the optional skill when you want help choosing presets or interpreting results. Once you have presets, the CLI and terminal UI can archive future projects without the skill.

For occasional use, generate a prompt without installing the skill:

```powershell
npx skills use Today20092/ArchiveBench@archivebench
```

Paste the generated prompt into your local agent session, then describe your footage and goal. Add `--agent codex` to start Codex directly, or `--agent claude-code` for Claude Code. Node/npm and the selected agent must be installed separately. ArchiveBench and FFmpeg are still required for encoding.

To keep the skill in the current project:

```powershell
npx skills add Today20092/ArchiveBench --skill archivebench
```

Choose your agent when prompted. Add `--global` only if you want the skill available across projects. This revision makes the installed skill explicitly invoked in Codex and Claude Code. Use `$archivebench` in Codex or `/archivebench` in Claude Code when you need it.

See [skill installation and removal](docs/installation.md#install-the-optional-agent-skill) for details. The [agent prompt](docs/AGENT-PROMPT.md) is a checkout alternative. [AGENTS.md](AGENTS.md) supplies maintenance rules.

## Why I made it

I wanted to archive my own footage and free up storage. ArchiveBench gives videographers and editors a starting point to measure the tradeoffs on their own computer, choose settings, and use or adapt an archive script for finished projects.

This project was built with AI coding agents. You can ask your agent to install it, explain your results, or modify it for your workflow. Keep the saved experiment and verification checks intact when adapting it.

## Sharing results

Share the HTML report after checking its labels and preview images for private content. Include its `review/` folder for companion playback and native stills; without it, those controls show missing assets. Raw `results.json` contains local paths. Source paths are redacted in the HTML; labels and images are not.

## Development

See [development and checks](docs/development.md) for report builds, tests and synthetic examples. No personal footage is included. ArchiveBench does not redistribute FFmpeg; see the [third-party notices](THIRD_PARTY_NOTICES.md).

Report reproducible bugs through [GitHub Issues](https://github.com/Today20092/ArchiveBench/issues). Review diagnostic data before posting; raw results and configs can contain private paths.
