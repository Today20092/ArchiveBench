# Development and checks

[Back to the README](../README.md) · [Repository instructions](../AGENTS.md)

Windows is the tested platform; macOS/Linux and their hardware encoders remain experimental. The Python package includes bundled report assets, so users do not need Node to run benchmarks or view reports.

## Run checks

From the repository root:

```powershell
uv sync --locked --python 3.11
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
uv run ty check
npm ci
npm run build
npm test
node --test report/playback.test.mjs
uv build
```

For report changes, also generate a synthetic demo and check it in a browser:

```powershell
uv run tests/create_demo.py
node report/browser-check.mjs
node report/stills-check.mjs runs/demo/benchmark/report.html
```

The demo writes under ignored `runs/`. If an existing demo run rejects a changed runner fingerprint, preserve that run and use its saved config with a fresh output folder:

```powershell
uv run archivebench benchmark runs/demo/config.json --output runs/demo/benchmark-new
node report/browser-check.mjs runs/demo/benchmark-new/report.html
```

The browser check uses installed Windows Edge by default. Set `ARCHIVEBENCH_BROWSER` to another Chromium executable when needed. It checks chart rendering, duration/target controls, export, the image divider, responsive layout and zero network requests.

Synthetic examples contain no personal footage. Do not present their performance figures as real camera results. Keep generated media, local configs, logs and private paths out of Git.

## Dependencies and licensing

The [package manifest](../pyproject.toml) records the Python requirement and development tools. Encoder controls live in `archivebench/encoders.py`; changes affect restart fingerprints. Follow the [agent workflow](agent-workflow.md) when operating a benchmark.

ArchiveBench uses the [MIT license](../LICENSE) and does not redistribute FFmpeg. Anyone redistributing FFmpeg must comply with that build's licensing. See the [third-party notices](../THIRD_PARTY_NOTICES.md).
