# ArchiveBench

Measure archival video settings on your footage and hardware. Compare size, speed and quality in a single offline HTML report, then export a tested configuration for the optional archive runner.

Windows is the tested platform. The CLI uses portable Python and FFmpeg; macOS/Linux and their hardware encoders are experimental until tested. No personal footage is included. Reports use bundled TanStack Charts and make no network requests.

## Start

Install Python 3.11+ through [uv](https://docs.astral.sh/uv/) and an FFmpeg build that includes `libvmaf`. FFmpeg/ffprobe must be on PATH. Users do not need Node: the chart bundle is included.

```powershell
uv sync --locked
uv run archivebench doctor
uv run archivebench setup --config local-config.json
uv run archivebench benchmark local-config.json --output E:\ArchiveBenchRuns\first-test
```

Open `report.html` in the output folder. It contains the results and preview images, and works directly from disk without a server or internet. JSON, CSV and Markdown outputs are saved alongside it. Preview labels may reveal project names; review before sharing. Raw `results.json` contains local paths; share the redacted HTML instead.

Select motion, fine detail and dark/noisy examples. A representative sample is more informative than a large number of similar clips. `setup` lists eligible clips from a folder and asks which to include; it does not infer scene diversity. Proxy and generated archive folders are excluded.

## What is measured

- Available configured H.264, H.265, AV1 and VP9 encoders get a one-second compatibility/quality screen. A listed hardware encoder must actually encode the chosen pixel format. Unconfigured or failing implementations are explicitly reported.
- Quick mode selects up to four finalists, runs up to two quality attempts per finalist and one timed encode per attempt. Thorough mode selects up to eight, runs up to four attempts and reports the median of three timed encodes. Screens favor near-target quality, then size/time; this heuristic can miss useful encoders. All raw screen results are retained.
- Compact starts at VMAF 93 and Editing at 96. These are configurable model-score targets, not guarantees of viewing quality or grading latitude. The tool seeks smaller candidates meeting the selected target; it does not certify archival safety.
- Native resolution/frame rate are retained. Choose one output format per experiment: 8-bit 4:2:0, 10-bit 4:2:0 or 10-bit 4:2:2. Use separate configurations/output folders to compare format groups. HDR, interlaced and variable-frame-rate inputs are rejected in this release.
- Scores use native-resolution VMAF (`vmaf_4k_v0.6.1` at width 3840+, otherwise `vmaf_v0.6.1`) and SSIM. Quick VMAF samples every second frame; thorough scores every frame. Frame counts are checked and timestamps aligned by frame index. Reference chroma is converted to the requested output format, so scores do not measure all loss of original 4:2:2 chroma detail.
- Benchmark encodes are video only. Timings include decode, encode and disk I/O, excluding scores, hashing, previews and archival verification. Duration projections are linear estimates. They exclude audio and vary by source and machine load.

## Configuration and restart

The setup wizard creates editable JSON. [Configuration reference](docs/configuration.md) describes fields and supported encoders. An empty `encoders` list screens all configured implementations present in the FFmpeg build. Quality values across encoders are not interchangeable. The adapter definitions are the authoritative source for exact commands.

Re-run the same benchmark command to resume. Successful trials and screening outputs are hashed and reused. Source content, offsets, settings, adapter/runner source and FFmpeg/ffprobe fingerprints bind the cache. Changes require a new output folder. Interrupted trials restart; completed trials remain. The time budget applies per invocation, including encoding/scoring/reference creation, but source hashing and preflight can add time. Repeated invocations can continue a budget-limited experiment.

One process may use a run/archive folder at a time. A `.lock` file records the PID. After an abrupt machine shutdown, remove that file only after checking that the recorded process is no longer running. Encoder screen timeouts are recorded as failures rather than hiding them.

The experiment specification is repeatable. Output bytes and timings may differ across hardware, driver versions or encoder builds. Trials run in stable order with warm-up probes; timing repetitions do not eliminate system-load or thermal bias.

## Optional archive runner

In the report, select a measured configuration and click **Export archive settings**. Review its native-resolution clips first. The starter runner writes MKV, preserves resolution/frame rate/color metadata, compresses retained audio as AAC at 192 kbps per channel and omits audio tracks 3/4. It does not guarantee application-specific metadata or editor relinking. Subtitle/attachment preservation requires customization.

```powershell
# Review eligible files first; no encoding by default.
uv run archivebench archive --source D:\Project\Originals --output E:\Project\Archived --settings archive-settings.json
# Explicitly encode after reviewing the list. Originals stay intact.
uv run archivebench archive --source D:\Project\Originals --output E:\Project\Archived --settings archive-settings.json --execute
# Review separate cleanup list. No deletion by default.
uv run archivebench cleanup --output E:\Project\Archived
# Only after human review of the encoded clips:
uv run archivebench cleanup --output E:\Project\Archived --execute --reviewed
```

Cleanup permanently deletes the listed verified originals. It requires matching source/output hashes, at least 10% actual savings, audio/video validation and full decode checks. The runner never deletes originals while encoding. Encodes saving less than 10% are discarded; originals stay in place. A batch failure stops the archive run and leaves its checkpoint for inspection/restart.

## Use with Codex or Claude

Paste [the agent prompt](docs/AGENT-PROMPT.md) into your agent, pointing it to this checkout. The agent uses the same CLI and saved config. It helps select samples, inspect capabilities, choose a budget and interpret results; thresholds and cleanup remain explicit user decisions. [AGENTS.md](AGENTS.md) provides maintenance rules and links to the run procedure.

## Development

```powershell
uv sync --locked
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
uv run ty check
npm ci
npm run build
npm test
uv run tests/create_demo.py
node report/browser-check.mjs
```

The browser check uses installed Windows Edge by default. Set `ARCHIVEBENCH_BROWSER` to another Chromium executable when needed. It verifies chart rendering, duration/target controls, export, image divider, responsive layout and zero network requests. The synthetic demo is generated locally under ignored `runs/`; none of its performance figures should be presented as real camera results.

This is an initial release. FFmpeg redistributors must comply with their build's licensing; ArchiveBench does not redistribute FFmpeg. See [third-party notices](THIRD_PARTY_NOTICES.md).
