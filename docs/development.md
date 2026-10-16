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

For the default fixed-comparison flow, generate `uv run tests/create_fixed_demo.py`, then run `node report/fixed-check.mjs` and `node report/stills-check.mjs runs/fixed-demo/benchmark/report.html`. These checks cover measured starting-preset export, offline charts, native stills and narrow/wide layouts. Preserve prior demo outputs when code identities change and use a fresh output folder.

The demo writes under ignored `runs/`. If an existing demo run rejects a changed runner fingerprint, preserve that run and use its saved config with a fresh output folder:

```powershell
uv run archivebench benchmark runs/demo/config.json --output runs/demo/benchmark-new
node report/browser-check.mjs runs/demo/benchmark-new/report.html
```

The browser check uses installed Windows Edge by default. Set `ARCHIVEBENCH_BROWSER` to another Chromium executable when needed. It checks chart rendering, duration/target controls, export, the image divider, responsive layout and zero network requests.

Synthetic examples contain no personal footage. Do not present their performance figures as real camera results. Keep generated media, local configs, logs and private paths out of Git.

## Pull request documentation review

Before creating or merging a PR:

1. Add a documentation task to the local ticket or PR checklist. For substantial changes to commands, defaults, installation, workflows or safety behavior, assign a documentation subagent to review the final diff and update `README.md` and affected guides. If subagents are unavailable, perform and record this review directly.
2. Keep the README's overview, quick start and navigation aligned with the shipped behavior; put detailed instructions in linked guides. Verify command examples, relative links, job paths, supported formats and limitations. Distinguish features on `main` from published release contents.
3. Include documentation changes in the feature PR. If a separate documentation PR is necessary, link both PRs and merge the documentation before or with the feature. A separate PR is optional.
4. Record the reviewed documents and checks in the PR description. When no documentation changes are needed, record the reason. Repeat the review when the final scope changes; finish only when each user-facing change is covered by the README or an accurate linked guide.

## Dependencies and licensing

GitHub CI runs these checks on Windows with Python 3.11 and a checksum-verified full FFmpeg 8.1.2 build. It creates a fresh synthetic benchmark, checks the offline report and installs the built wheel in isolation. Local hardware results still need their own probes; CI does not certify a GPU or editor workflow.

The [package manifest](../pyproject.toml) records the Python requirement and development tools. Encoder controls live in `archivebench/encoders.py`; changes affect restart fingerprints. Follow the [agent workflow](agent-workflow.md) when operating a benchmark.

ArchiveBench uses the [MIT license](../LICENSE) and does not redistribute FFmpeg. Anyone redistributing FFmpeg must comply with that build's licensing. See the [third-party notices](../THIRD_PARTY_NOTICES.md).
